from spacy.lang.en.stop_words import STOP_WORDS as SPACY_STOPWORDS

def dependency_keywords(question: str, spacy_model): 
    tokens = spacy_model(question)
    # Remove stop words
    keep_words = {"name", "amount", "show", "mine", "side", "keep", "full", "see", "various", "former", "bottom", "call", "next"}  
    custom_stopwords = SPACY_STOPWORDS.difference(keep_words)
    tokens = [token for token in tokens if token.text.lower() not in custom_stopwords and not token.is_punct]
    keywords = set()

    for token in tokens:
        # Look for a noun with modifiers
        if token.pos_ in {"NOUN", "PROPN"}:
            modifiers = [
                child for child in token.lefts
                if child.dep_ in {"amod", "compound"} 
            ]
            if modifiers:
                phrase = " ".join([t.text for t in [*modifiers, token]])
                keywords.add(phrase)
        keywords.add(token.text)
    return list(keywords)

def keybert_keywords(question, candidates, bert_model, top_n=5):
    candidates = [phrase.lower() for phrase in candidates]
    keywords = bert_model.extract_keywords(
        question,
        stop_words="english",
        candidates=candidates,
        keyphrase_ngram_range=(1, 3),
        top_n=top_n                 # Number of keywords to return
    )
    return [keyword[0] for keyword in keywords]

def extract_keywords(question, bert_model, spacy_model, top_n=5):
    candidates = dependency_keywords(question, spacy_model)
    keywords = keybert_keywords(question, candidates, bert_model, top_n=top_n)
    return keywords

