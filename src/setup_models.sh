#!/bin/bash

# Download SentenceTransformer model
python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='sentence-transformers/all-MiniLM-L6-v2', local_dir='models/embedding_model')"

# Download and save spaCy model
python -m spacy download en_core_web_sm
python -c "
import spacy
nlp = spacy.load('en_core_web_sm')
nlp.to_disk('models/fuzzy_model')
"
