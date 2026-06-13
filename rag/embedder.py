from langchain_openai import OpenAIEmbeddings
from rag.config import OPENAI_API_KEY, EMBEDDING_MODEL

_embedder = None

def get_embedder() -> OpenAIEmbeddings:
    global _embedder
    if _embedder is None:
        _embedder = OpenAIEmbeddings(
            model=EMBEDDING_MODEL,
            openai_api_key=OPENAI_API_KEY
        )
    return _embedder
