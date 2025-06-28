# Load DataSet
import torch
import pandas as pd

from torch.utils.data import Dataset

class Parallel_Data(Dataset):
    def __init__(self, pickle_file, arabic_tokens_file, english_tokens_file):
        self.data               = pd.read_pickle(pickle_file)
        self.max_length_arabic  = self.data.map(len).max()["arabic"]
        self.max_length_english = self.data.map(len).max()["english"]

        self.data["arabic_text_len"]  =  self.data["arabic"].map(len)
        self.data["english_text_len"] = self.data["english"].map(len)
        self.__build_vocab(arabic_tokens_file, english_tokens_file)

        self.data["padded_arabic"]  = self.data["arabic"].apply(lambda x  : self.pad_to_max(x,self.max_length_arabic))
        self.data["padded_postags"] = self.data["pos_tag"].apply(lambda x : self.pad_to_max(x,self.max_length_arabic))
        self.data["padded_english"] = self.data["english"].apply(lambda x : self.pad_to_max(x,self.max_length_english))
    
        self.data["padded_arabic"]  = self.data["padded_arabic"].apply(lambda x: self.__token2id(x,self.arabic_tokens))
        self.data["padded_english"] = self.data["padded_english"].apply(lambda x: self.__token2id(x,self.english_tokens))
        self.data["padded_postags"] = self.data["padded_postags"].apply(lambda x: self.__token2id(x,self.postags))


    def __build_vocab(self, arabic_tokens_file, english_tokens_file):
        self.arabic_tokens  = list(pd.read_json(arabic_tokens_file)[0])
        self.arabic_tokens  = {word : i + 1  for i, word in enumerate(self.arabic_tokens)}
        self.arabic_tokens.update({"<PAD>":0,"<UNK>":len(self.arabic_tokens) + 1})

        self.english_tokens = list(pd.read_json(english_tokens_file)[0])
        self.english_tokens  = {word : i + 1  for i, word in enumerate(self.english_tokens)}
        self.english_tokens.update({"<PAD>":0,"<UNK>":len(self.english_tokens) + 1})
        
        self.postags = set()
        all_en_sequences = list(self.data["pos_tag"].map(set))
        for sequence in all_en_sequences:
                self.postags.update(sequence)
        self.postags = {tag: i+1 for i, tag in enumerate(self.postags)}
        self.postags.update({"<PAD>":0,"<UNK>":len(self.postags)+1})

    def __token2id(self, tokens, vocab):
        return [vocab.get(token, vocab["<UNK>"]) for token in tokens]   
    
    def pad_to_max(self, lst, max_len, pad_token="<PAD>"):
        return lst + [pad_token] * (max_len - len(lst))

    def __len__(self):
        return self.data.shape[0]
    
    def __getitem__(self, idx):
        # load and return sample number idx
        item = self.data.iloc[idx]
        source = torch.tensor(item["padded_arabic"]       , dtype = torch.long)
        target = torch.tensor(item["padded_english"]      , dtype = torch.long)
        len_source = torch.tensor(item["arabic_text_len"] , dtype = torch.long)
        src_pos_tags = torch.tensor(item["padded_postags"]       , dtype = torch.long)

        return source, target, len_source, src_pos_tags