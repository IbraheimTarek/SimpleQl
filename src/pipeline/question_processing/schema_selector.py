from fuzzywuzzy import fuzz
from sentence_transformers import  util
from spacy.lang.en.stop_words import STOP_WORDS as SPACY_STOPWORDS

def clean_tokens(text, spacy_model):
    """Remove stop words and punctuation."""
    keep_words = {"name", "amount", "show", "mine", "side", "keep", "full", "see", "various", "former", "bottom", "call", "next"}  
    custom_stopwords = SPACY_STOPWORDS.difference(keep_words)
    doc = spacy_model(text)
    return [token.text for token in doc if token.text.lower() not in custom_stopwords and not token.is_punct]

def fuzzy_match_phrases(question, schema, spacy_model, threshold=70):
    """Fuzzy match question's token phrases to column names."""
    tokens = clean_tokens(question, spacy_model)
    matches = set()
    for token in tokens:
        for table in schema:
            for column in schema[table]:
                if column in matches:
                    continue
                score = fuzz.partial_ratio(token.lower(), column.lower())
                if score >= threshold:
                    matches.add((table, column))
    return matches

def semantic_similarity(question, schema, embeddings, bert_model, threshold=0.4):
    """Compute semantic similarity between keywords and column descriptions."""
    question_vec = bert_model.encode(question, convert_to_tensor=True)
    similarities = set()
    for table in schema:
        for col in schema[table]:
            desc = schema[table][col]
            score = 0
            if desc != "":
                desc_vec = embeddings[table][col]
                score = util.cos_sim(question_vec, desc_vec).item()
            else:
                col_vec = bert_model.encode(col, convert_to_tensor=True)
                score = util.cos_sim(question_vec, col_vec).item()
            if score >= threshold:
                similarities.add((table, col))

    return similarities

def select_schema(question, schema : dict[str, dict[str,str]], embeddings, spacy_model, bert_model, fuzz_threshold=80, similarity_threshold=0.4):
    """Selects the part of schema that is related to the given question"""
    fuzzy = fuzzy_match_phrases(question, schema, spacy_model, threshold=fuzz_threshold)
    semantic = semantic_similarity(question, schema, embeddings, bert_model, threshold=similarity_threshold)
    related_schema = fuzzy.union(semantic)
    selected_schema = {}
    # Remove unrelated columns
    for table in schema:
        for col in schema[table]:
            if (table, col) in related_schema:
                if table not in selected_schema:
                    selected_schema[table] = {}
                selected_schema[table][col] = schema[table][col]
    return selected_schema
