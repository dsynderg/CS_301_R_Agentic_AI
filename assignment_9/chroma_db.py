from __future__ import annotations

from typing import Optional
import os

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction


def get_chroma_client(persist_dir: Optional[str] = None) -> chromadb.Client:
    """Return a configured Chroma client.

    - If `persist_dir` is provided or `CHROMA_PERSIST_DIR` env var is set,
      a `PersistentClient` is returned (disk-backed).
    - Otherwise an in-memory `Client` is returned.
    """
    path = persist_dir or os.environ.get("CHROMA_PERSIST_DIR")
    if path:
        return chromadb.PersistentClient(path=path)
    return chromadb.Client()


def get_openai_embedding_function(model_name: str = "text-embedding-3-small") -> OpenAIEmbeddingFunction:
    """Helper to create an OpenAI embedding function (uses OPENAI_API_KEY).
    """
    return OpenAIEmbeddingFunction(model_name=model_name)


def get_or_create_collection(client: chromadb.Client, name: str, embedding_function: Optional[OpenAIEmbeddingFunction] = None):
    """Get or create a Chroma collection with a default OpenAI embedding function.
    """
    if embedding_function is None:
        embedding_function = get_openai_embedding_function()
    return client.get_or_create_collection(name=name, embedding_function=embedding_function)
