import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from collections import Counter

# Define the CBOW Dataset
class CBOWDataset(Dataset):
    def __init__(self, sentences, word_to_idx, window_size):
        self.max_C = 2 * window_size  # Maximum context size
        self.data = []
        for sentence in sentences:
            sentence_idx = [word_to_idx.get(word, word_to_idx["<UNK>"]) for word in sentence]  
            for i in range(len(sentence_idx)):
                context = []
                for j in range(-window_size, window_size + 1):
                    if j != 0 and 0 <= i + j < len(sentence_idx):
                        context.append(sentence_idx[i + j])
                actual_C = len(context)
                # Pad context to max_C with 0 (<pad>)
                context += [0] * (self.max_C - actual_C)
                self.data.append((context, actual_C, sentence_idx[i]))
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        context, actual_C, target = self.data[idx]
        return torch.tensor(context), torch.tensor(actual_C), torch.tensor(target)

# Define the CBOW Model
class CBOW(nn.Module):
    def __init__(self, vocab_size, embedding_dim):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embedding_dim, padding_idx=0)
        self.linear = nn.Linear(embedding_dim, vocab_size)
    
    def forward(self, context_indices, actual_C):
        embeddings = self.embedding(context_indices)  # (batch_size, max_C, embedding_dim)
        sum_embeddings = embeddings.sum(dim=1)  # (batch_size, embedding_dim)
        average_embedding = sum_embeddings / actual_C.unsqueeze(1).float()
        scores = self.linear(average_embedding)  # (batch_size, vocab_size)
        return scores

def build_vocab(tokens_file):
        tokens  = list(pd.read_json(tokens_file)[0])
        tokens  = {word : i + 1  for i, word in enumerate(tokens)}
        tokens.update({"<PAD>":0,"<UNK>":len(tokens) + 1})
        return tokens

# Function to train the CBOW model
def train_cbow(sentences, tokens_file,
               window_size=2, embedding_dim=100, batch_size=64, num_epochs=10, learning_rate=0.001):
    # Build vocabulary
    word_to_idx = build_vocab(tokens_file)
    vocab_size = len(word_to_idx)
    
    # Create dataset and dataloader
    dataset = CBOWDataset(sentences, word_to_idx, window_size)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    # Initialize model, loss, and optimizer
    model = CBOW(vocab_size, embedding_dim)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    
    # Training loop
    for epoch in tqdm(range(num_epochs),desc="Epochs"):
        total_loss = 0
        for context_indices, actual_C, target in dataloader:
            optimizer.zero_grad()
            scores = model(context_indices, actual_C)
            loss = criterion(scores, target)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        print(f"Epoch {epoch + 1}, Loss: {total_loss / len(dataloader):.4f}")
    
    return model, word_to_idx

