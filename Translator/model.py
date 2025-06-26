import torch
import torch.nn.functional as F
from torch import nn
import random
import math

class BahdanauAttention(nn.Module):
    def __init__(self, enc_hid_dim, dec_hid_dim, attn_dim):
        super().__init__()
        self.W_enc = nn.Linear(enc_hid_dim, attn_dim)
        self.W_dec = nn.Linear(dec_hid_dim, attn_dim)
        self.v = nn.Linear(attn_dim, 1)
        
    def forward(self, decoder_hidden, encoder_outputs, mask):
        """Forward pass with proper mask handling"""
        # decoder_hidden: [batch_size, dec_hid_dim]
        # encoder_outputs: [batch_size, src_len, enc_hid_dim]
        # mask: [batch_size, src_len] (boolean mask)
        
        src_len = encoder_outputs.size(1)
        decoder_hidden = decoder_hidden.unsqueeze(1).repeat(1, src_len, 1)
        
        energy = torch.tanh(
            self.W_enc(encoder_outputs) + 
            self.W_dec(decoder_hidden)
        )
        scores = self.v(energy).squeeze(2)  # [batch_size, src_len]
        
        # Apply mask before softmax
        scores = scores.masked_fill(~mask, -1e10)  # Invert mask and fill
        
        attn_weights = F.softmax(scores, dim=1)
        context = torch.bmm(attn_weights.unsqueeze(1), encoder_outputs).squeeze(1)
        
        return context, attn_weights

class Encoder(nn.Module):
    def __init__(self, input_dim, emb_dim, hid_dim, n_layers, device):
        super().__init__()
        self.hid_dim = hid_dim
        self.n_layers = n_layers
        self.device = device
        self.embedding = nn.Embedding(input_dim, emb_dim, padding_idx=0)
        self.rnn = nn.LSTM(
            emb_dim, hid_dim, n_layers,
            batch_first=True,
            bidirectional=True
        )
        self.dropout = nn.Dropout(0.5)
        self.fc_hidden = nn.Linear(hid_dim * 2, hid_dim)
        self.fc_cell = nn.Linear(hid_dim * 2, hid_dim)

    def forward(self, src, src_lengths):
        embedded = self.embedding(src)
        
        embedded = self.dropout(self.embedding(src))
        packed_embedded = nn.utils.rnn.pack_padded_sequence(
            embedded, src_lengths.cpu(), batch_first=True, enforce_sorted=False
        )
                
        packed_outputs, (hidden, cell) = self.rnn(packed_embedded)

        outputs, _ = nn.utils.rnn.pad_packed_sequence(
                    packed_outputs, batch_first=True
        )
        
        # Process final states
        hidden_forward = hidden[0:2*self.n_layers:2, :, :]
        hidden_backward = hidden[1:2*self.n_layers:2, :, :]
        hidden_concat = torch.cat((hidden_forward, hidden_backward), dim=2)
        
        cell_forward = cell[0:2*self.n_layers:2, :, :]
        cell_backward = cell[1:2*self.n_layers:2, :, :]
        cell_concat = torch.cat((cell_forward, cell_backward), dim=2)

        hidden_init = torch.tanh(self.fc_hidden(hidden_concat))
        cell_init = torch.tanh(self.fc_cell(cell_concat))
        
        # outputs: [batch_size, src_len, hid_dim*2] (full sequence)
        return outputs, hidden_init, cell_init

class Decoder(nn.Module):
    def __init__(self, output_dim, emb_dim, hid_dim, n_layers, enc_hid_dim, attn_dim):
        super().__init__()
        self.output_dim = output_dim
        self.hid_dim = hid_dim
        self.n_layers = n_layers
        self.embedding = nn.Embedding(output_dim, emb_dim, padding_idx=0)
        self.attention = BahdanauAttention(enc_hid_dim, hid_dim, attn_dim)
        self.rnn = nn.LSTM(
            emb_dim + enc_hid_dim,  # Input size changed for context vector
            hid_dim, 
            n_layers, 
            dropout=0.5 if n_layers>1 else 0, 
            batch_first=True
        )
        self.fc_out = nn.Linear(hid_dim + enc_hid_dim + emb_dim, output_dim)
        self.dropout = nn.Dropout(0.5)

    def forward(self, input, hidden, cell, encoder_outputs, mask):
        input = input.unsqueeze(1)  # [batch_size, 1]
        
        embedded = self.embedding(input)  # [batch_size, 1, emb_dim]
        
        # Get top layer hidden state for attention
        hidden_top = hidden[-1]  # [batch_size, hid_dim]
        
        # Calculate attention context vector
        context, attn_weights = self.attention(hidden_top, encoder_outputs, mask)
        context = context.unsqueeze(1)  # [batch_size, 1, enc_hid_dim]
        
        # Combine embedded input with context
        rnn_input = torch.cat((embedded, context), dim=2)  # [batch_size, 1, emb_dim + enc_hid_dim]
        
        # Pass to RNN
        output, (hidden, cell) = self.rnn(rnn_input, (hidden, cell))
        
        # Prepare for prediction
        output = output.squeeze(1)  # [batch_size, hid_dim]
        context = context.squeeze(1)  # [batch_size, enc_hid_dim]
        embedded = embedded.squeeze(1)  # [batch_size, emb_dim]
        
        # Combine RNN output, context, and embedded input
        prediction_input = torch.cat((output, context, embedded), dim=1)
        prediction = self.fc_out(prediction_input)
        
        return prediction, hidden, cell, attn_weights

class Seq2Seq(nn.Module):
    def __init__(self, encoder_arabic, encoder_postag, decoder, device):
        super().__init__()
        self.encoder_arabic = encoder_arabic
        self.encoder_postag = encoder_postag
        self.enc2dec = nn.Linear(2 * encoder_arabic.hid_dim, encoder_arabic.hid_dim)
        self.decoder = decoder
        self.device = device

        assert encoder_arabic.hid_dim == encoder_postag.hid_dim
        assert encoder_arabic.n_layers == encoder_postag.n_layers
        assert encoder_arabic.hid_dim == decoder.hid_dim
        assert encoder_arabic.n_layers == decoder.n_layers

    def create_mask(self, src_lengths, max_len):
        return torch.arange(max_len, device=self.device)[None, :] < src_lengths[:, None]

    def forward(self, src, trg, src_length, postags, teacher_forcing_ratio=0.5,return_attentions=False):
        # Run encoders
        enc_outs_arabic, hidden_arabic, cell_arabic = self.encoder_arabic(src, src_length)
        enc_outs_postag, hidden_postag, cell_postag = self.encoder_postag(postags, src_length)
        
        # Combine encoder outputs
        combined_enc_outs = torch.cat((enc_outs_arabic, enc_outs_postag), dim=2)
        max_src_len = combined_enc_outs.size(1)  # Get actual max length
        
        # Create mask from source lengths
        mask = self.create_mask(src_length, max_src_len)  # [batch_size, max_src_len]
        
        # Combine and project hidden states
        hidden = self.enc2dec(torch.cat((hidden_arabic, hidden_postag), dim=2))
        cell = self.enc2dec(torch.cat((cell_arabic, cell_postag), dim=2))
        
        # Initialize decoder
        batch_size = src.size(0)
        trg_len = trg.size(1)
        outputs = torch.zeros(batch_size, trg_len, self.decoder.output_dim).to(self.device)
        input = trg[:, 0]

        # Initialize attention storage
        all_attentions = [] if return_attentions else None

        for t in range(1, trg_len):
            output, hidden, cell, attn_weights = self.decoder(
                input, hidden, cell, combined_enc_outs, mask
            )
            outputs[:, t] = output
            teacher_force = random.random() < teacher_forcing_ratio
            top1 = output.argmax(1)
            input = trg[:, t] if teacher_force else top1

            if return_attentions:
                all_attentions.append(attn_weights.detach().cpu())
        
        return outputs, all_attentions