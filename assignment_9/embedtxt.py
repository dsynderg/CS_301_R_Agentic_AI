#!/usr/bin/env python3
"""Embed paragraphs from a text file using OpenAI embeddings.

Takes a text file separated by paragraphs (empty lines) and stores
each paragraph's embedding (as tuple key) and text in a dictionary.
"""

from pathlib import Path
from typing import Dict
from chroma_db import get_openai_embedding_function


def embed_paragraphs_from_file(txt_file: str) -> Dict[tuple, str]:
    """Read a text file, split by paragraphs, embed each, and return dict.
    
    Args:
        txt_file: Path to the text file to embed
        
    Returns:
        Dictionary where key is embedding (as tuple) and value is paragraph text
    """
    path = Path(txt_file).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")
    
    # Read and split by paragraphs (empty lines)
    text = path.read_text(encoding="utf-8")
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    
    if not paragraphs:
        print(f"No paragraphs found in {txt_file}")
        return {}
    
    # Get embedding function
    embedding_fn = get_openai_embedding_function(model_name="text-embedding-3-small")
    
    # Embed all paragraphs at once
    print(f"Embedding {len(paragraphs)} paragraphs...")
    embeddings = embedding_fn(paragraphs)
    
    # Build dictionary with embedding (as tuple) as key, paragraph as value
    result = {}
    for embedding, paragraph in zip(embeddings, paragraphs):
        # Convert list to tuple so it can be used as dictionary key
        embedding_tuple = tuple(embedding)
        result[embedding_tuple] = paragraph
    
    print(f"Successfully embedded {len(result)} paragraphs")
    return result


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python embedtxt.py <txt_file>")
        sys.exit(1)
    
    txt_file = sys.argv[1]
    embedded_dict = embed_paragraphs_from_file(txt_file)
    
    # Show sample
    if embedded_dict:
        # Show first embedding and paragraph
        first_key = list(embedded_dict.keys())[0]
        print(f"\nFirst embedding (sample): {first_key[:5]}... (truncated)")
        print(f"First paragraph: {embedded_dict[first_key][:100]}...\n")
        print(f"Total paragraphs: {len(embedded_dict)}")
