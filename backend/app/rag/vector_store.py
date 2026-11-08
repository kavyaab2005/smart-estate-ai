import chromadb
from sentence_transformers import SentenceTransformer

CHROMA_PATH = "chroma_db"
COLLECTION_NAME = "properties"

_model = SentenceTransformer("all-MiniLM-L6-v2")
_client = chromadb.PersistentClient(path=CHROMA_PATH)
_collection = _client.get_or_create_collection(name=COLLECTION_NAME)


def embed_text(text: str):
    return _model.encode(text).tolist()


def upsert_property(property_id: str, text: str, metadata: dict):
    _collection.upsert(
        ids=[property_id],
        embeddings=[embed_text(text)],
        documents=[text],
        metadatas=[metadata],
    )


def search_properties(query: str, top_k: int = 5):
    query_embedding = embed_text(query)
    results = _collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
    )
    return results


def collection_count():
    return _collection.count()


def reset_collection():
    global _collection
    _client.delete_collection(name=COLLECTION_NAME)
    _collection = _client.get_or_create_collection(name=COLLECTION_NAME)