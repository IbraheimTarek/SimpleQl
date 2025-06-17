from sentence_transformers import SentenceTransformer
import spacy

_embedding_model = None
_spacy_model = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer('models/embedding_model')
    return _embedding_model

def get_spacy_model():
    global _spacy_model
    if _spacy_model is None:
        _spacy_model = spacy.load("models/fuzzy_model") 
    return _spacy_model
