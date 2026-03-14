from sentence_transformers import SentenceTransformer
import numpy as np

_model = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model

def generate_embedding(text: str) -> np.ndarray:
    model = get_model()
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding

def batch_embed(texts: list[str]) -> list[np.ndarray]:
    model = get_model()
    embeddings = model.encode(texts, convert_to_numpy=True)
    return [embeddings[i] for i in range(len(embeddings))]
