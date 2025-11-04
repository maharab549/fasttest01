import spacy

# Load English tokenizer, tagger, parser, NER and word vectors
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Downloading spacy model \'en_core_web_sm\'...")
    spacy.cli.download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

def get_semantic_search_query(query: str) -> str:
    """Extracts key entities or concepts from a search query for semantic search.
    For a real AI integration, this would involve embedding models or more advanced NLP.
    """
    doc = nlp(query)
    # For simplicity, extract nouns and proper nouns as potential semantic keywords
    keywords = [token.text for token in doc if token.pos_ in ("NOUN", "PROPN", "ADJ")]
    if keywords:
        return " ".join(keywords)
    return query # Fallback to original query if no keywords found

