#!/usr/bin/env python3
"""Embed paragraphs from text files using OpenAI embeddings.

Takes text files separated by paragraphs (empty lines) and stores
each paragraph's embedding in a persistent Chroma database.
"""

import os
from pathlib import Path
from typing import Dict

from chroma_db import get_openai_embedding_function, get_chroma_client, get_or_create_collection


def embed_folder_of_txtfiles(
    folder_path: str,
    persist_dir: str = "./chroma_data",
    collection_name: str = "paragraphs"
) -> None:
    """Embed all txt files in a folder and store in persistent Chroma DB.
    
    Args:
        folder_path: Path to folder containing .txt files
        persist_dir: Directory to store Chroma database (default: ./chroma_data)
        collection_name: Name of collection in Chroma DB (default: paragraphs)
    """
    folder = Path(folder_path).expanduser().resolve()
    if not folder.is_dir():
        raise NotADirectoryError(f"Not a directory: {folder}")
    
    # Find all txt files
    txt_files = sorted(folder.glob("*.txt"))
    if not txt_files:
        print(f"No .txt files found in {folder}")
        return
    
    print(f"Found {len(txt_files)} txt files")
    
    # Set up persistent Chroma client and collection
    client = get_chroma_client(persist_dir=persist_dir)
    embedding_fn = get_openai_embedding_function(model_name="text-embedding-3-small")
    collection = get_or_create_collection(client, collection_name, embedding_fn)
    
    total_paragraphs = 0
    
    # Process each txt file
    for txt_file in txt_files:
        print(f"\nProcessing {txt_file.name}...")
        
        # Use embed_paragraphs_from_file to get embedded paragraphs
        embedded_dict = embed_paragraphs_from_file(str(txt_file))
        
        if not embedded_dict:
            print(f"  No paragraphs found")
            continue
        
        # Prepare data for Chroma
        ids = []
        docs = []
        embeddings = []
        metadatas = []
        
        for i, (embedding, paragraph) in enumerate(embedded_dict.items()):
            # Create unique ID: filename::paragraph_index
            para_id = f"{txt_file.stem}::{i}"
            ids.append(para_id)
            docs.append(paragraph)
            embeddings.append(list(embedding))  # Convert tuple back to list
            metadatas.append({
                "filename": txt_file.name,
                "paragraph_index": i,
                "source": str(txt_file.relative_to(folder))
            })
        
        # Add to collection with embeddings
        collection.add(ids=ids, documents=docs, embeddings=embeddings, metadatas=metadatas)
        total_paragraphs += len(embedded_dict)
        print(f"  Added {len(embedded_dict)} paragraphs")
    
    print(f"\n✓ Successfully stored {total_paragraphs} paragraphs in '{collection_name}' (persisted at '{persist_dir}')")

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
        print("Usage:")
        print("  python embedtxt.py <txt_file>              # Embed single file (returns dict)")
        print("  python embedtxt.py <folder>               # Embed all .txt in folder (stores to Chroma)")
        print("  python embedtxt.py <folder> <db_dir>      # Specify custom Chroma database directory")
        sys.exit(1)
    
    path = sys.argv[1]
    path_obj = Path(path).expanduser().resolve()
    
    if path_obj.is_file() and path_obj.suffix == ".txt":
        # Single file mode - return dictionary
        print(f"Reading single file: {path_obj}")
        embedded_dict = embed_paragraphs_from_file(path)
        
        if embedded_dict:
            first_key = list(embedded_dict.keys())[0]
            print(f"\nFirst embedding (sample): {first_key[:5]}... (truncated)")
            print(f"First paragraph: {embedded_dict[first_key][:100]}...\n")
            print(f"Total paragraphs: {len(embedded_dict)}")
    
    elif path_obj.is_dir():
        # Folder mode - embed all and store to Chroma
        persist_dir = sys.argv[2] if len(sys.argv) > 2 else "./chroma_data"
        print(f"Reading folder: {path_obj}")
        embed_folder_of_txtfiles(path, persist_dir=persist_dir)
    
    else:
        print(f"Error: {path} is not a valid file or folder")
        sys.exit(1)
