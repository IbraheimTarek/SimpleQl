import torch
from torch import nn
import random

class Encoder(nn.Module):
    def __init__(self, input_dim, emb_dim, hid_dim, n_layers, device):
        super().__init__()
        self.hid_dim = hid_dim
        self.n_layers = n_layers
        self.device = device
        self.embedding = nn.Embedding(input_dim, emb_dim, padding_idx=0)
        self.rnn = nn.LSTM(
            emb_dim, hid_dim, n_layers,
            dropout=0.5 if n_layers > 1 else 0,
            batch_first=True,
            bidirectional=True
        )
        self.dropout = nn.Dropout(0.5)
        self.fc_hidden = nn.Linear(hid_dim * 2, hid_dim)
        self.fc_cell = nn.Linear(hid_dim * 2, hid_dim)

    def forward(self, src, src_lengths):

        embedded = self.dropout(self.embedding(src))
        # Pack padded sequences
        packed_embedded = nn.utils.rnn.pack_padded_sequence(
            embedded, src_lengths.cpu(), batch_first=True, enforce_sorted=False
        )

        _, (hidden, cell) = self.rnn(packed_embedded)  # PyTorch auto-inits zero states

        # Process ALL layers (not just last)
        hidden_forward = hidden[0:2*self.n_layers:2, :, :]
        hidden_backward = hidden[1:2*self.n_layers:2, :, :]
        hidden_concat = torch.cat((hidden_forward, hidden_backward), dim=2)
                


        cell_forward = cell[0:2*self.n_layers:2, :, :]
        cell_backward = cell[1:2*self.n_layers:2, :, :]
        cell_concat = torch.cat((cell_forward, cell_backward), dim=2)

        hidden_init = self.fc_hidden(hidden_concat)
        cell_init = self.fc_cell(cell_concat)
        
        return hidden_init, cell_init

class Decoder(nn.Module):
    def __init__(self, output_dim, emb_dim, hid_dim, n_layers):
        super().__init__()

        self.output_dim = output_dim
        self.hid_dim = hid_dim
        self.n_layers = n_layers

        self.embedding = nn.Embedding(output_dim, emb_dim, padding_idx = 0)
        self.rnn       = nn.LSTM(emb_dim, hid_dim, n_layers, dropout=0.5 if n_layers>1 else 0, batch_first=True)
        self.fc_out    = nn.Linear(hid_dim, output_dim)
        self.dropout   = nn.Dropout(0.5)
        
    def forward(self, input, hidden, cell):
        input = input.unsqueeze(1)

        embedded = self.dropout(self.embedding(input))

        output, (hidden, cell) = self.rnn(embedded, (hidden, cell))

        prediction = self.fc_out(output.squeeze(1))

        return prediction, hidden, cell
    
class Seq2Seq(nn.Module):
    def __init__(self, encoder_arabic, encoder_postag, decoder, device):
        super().__init__()
        self.encoder_arabic = encoder_arabic
        self.encoder_postag = encoder_postag
        self.enc2dec = nn.Linear(2*encoder_arabic.hid_dim, encoder_arabic.hid_dim)
        self.decoder = decoder
        self.device = device

        assert (encoder_arabic.hid_dim == encoder_postag.hid_dim), "Hidden dimensions of encoders must match!"
        assert (encoder_arabic.n_layers == encoder_postag.n_layers), "Encoder and decoder must have the same number of layers!"
        
        assert (encoder_arabic.hid_dim == decoder.hid_dim), "Hidden dimensions of encoder and decoder must match!"
        assert (encoder_arabic.n_layers == decoder.n_layers), "Encoder and decoder must have the same number of layers!"

    def forward(self, src, trg, src_length , postags, teacher_forcing_ratio=0.5):

        batch_size = src.shape[0]
        
        trg_len = trg.shape[1]
        trg_vocab_size = self.decoder.output_dim

        outputs = torch.zeros(batch_size, trg_len, trg_vocab_size).to(self.device)
            
        hidden_arabic, cell_arabic = self.encoder_arabic(src,src_length)
        hidden_postag, cell_postag = self.encoder_postag(postags,src_length)

        hidden = self.enc2dec(torch.cat((hidden_arabic, hidden_postag), dim=2))
        cell = self.enc2dec(torch.cat((cell_arabic, cell_postag), dim=2))

        input = trg[:, 0] # Passing the starting token (SOS)

        for t in range(1, trg_len):

            output, hidden, cell = self.decoder(input, hidden, cell)
            outputs[:, t, :] = output # Predictions upto target length
            teacher_force = random.random() < teacher_forcing_ratio
            top1 = output.argmax(1)
            input = trg[:, t] if teacher_force else top1
        
        return outputs