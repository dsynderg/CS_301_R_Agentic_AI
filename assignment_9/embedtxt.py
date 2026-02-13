#!/usr/bin/env python3
"""Embed paragraphs from text files using OpenAI embeddings.

Takes text files separated by paragraphs (empty lines) and stores
each paragraph's embedding in a persistent Chroma database.
"""

import os
from pathlib import Path
from typing import Dict
import csv

from chroma_db import get_openai_embedding_function, get_chroma_client, get_or_create_collection
collection_name = "par"

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
        
        # Use embed_paragraphs_from_file to get list of (embedding, paragraph) tuples
        embedding_paragraph_pairs = embed_paragraphs_from_file(str(txt_file))
        
        if not embedding_paragraph_pairs:
            print(f"  No paragraphs found")
            continue
        
        # Prepare data for Chroma
        ids = []
        docs = []
        embeddings = []
        metadatas = []
        
        for i, (embedding_list, paragraph) in enumerate(embedding_paragraph_pairs):
            para_id = f"{txt_file.stem}::{i}"
            ids.append(para_id)
            docs.append(paragraph)
            embeddings.append(embedding_list)  # Already a list of Python floats
            metadatas.append({
                "filename": txt_file.name,
                "paragraph_index": i,
                "source": str(txt_file.relative_to(folder))
            })
        
        collection.add(ids=ids, documents=docs, embeddings=embeddings, metadatas=metadatas)
        total_paragraphs += len(embedding_paragraph_pairs)
        print(f"  Added {len(embedding_paragraph_pairs)} paragraphs")
    
    print(f"\n✓ Successfully stored {total_paragraphs} paragraphs in '{collection_name}' (persisted at '{persist_dir}')")

def embed_paragraphs_from_file(file_path: str, max_chars_per_batch: int = 600000) -> list[tuple[list[float], str]]:
    """Read a text or CSV file, extract paragraphs/rows, embed in batches, and return list of (embedding, text) tuples.
    
    Args:
        file_path: Path to the text or CSV file to embed
        max_chars_per_batch: Maximum characters to embed at once to avoid token limits (default: 600k)
        
    Returns:
        List of tuples: (embedding_vector, text) where embedding_vector is a list of floats
    """
    path = Path(file_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")
    
    paragraphs = []
    
    # Read based on file type
    if path.suffix.lower() == '.csv':
        # Read CSV file
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                # Combine all columns in row into a paragraph
                if row:  # Skip empty rows
                    text = ' '.join(str(cell).strip() for cell in row if cell.strip())
                    if len(text) > 20:  # Skip very short rows
                        paragraphs.append(text)
    else:
        # Read text file and split by paragraphs (empty lines)
        text = path.read_text(encoding="utf-8")
        paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
    
    # Filter out empty paragraphs and ones that are too long
    paragraphs = [
        p for p in paragraphs
        if p and isinstance(p, str) and len(p.strip()) > 20 and len(p) < 8000
    ]
    
    if not paragraphs:
        print(f"No valid paragraphs found in {file_path}")
        return []
    
    # Get embedding function
    embedding_fn = get_openai_embedding_function(model_name="text-embedding-3-small")
    
    # Batch paragraphs by character count to avoid exceeding token limits
    batches = []
    current_batch = []
    current_char_count = 0
    
    for paragraph in paragraphs:
        para_chars = len(paragraph)
        
        # If adding this paragraph exceeds limit, start a new batch
        if current_char_count + para_chars > max_chars_per_batch and current_batch:
            batches.append(current_batch)
            current_batch = [paragraph]
            current_char_count = para_chars
        else:
            current_batch.append(paragraph)
            current_char_count += para_chars
    
    # Add final batch
    if current_batch:
        batches.append(current_batch)
    
    print(f"  Embedding {len(paragraphs)} paragraphs in {len(batches)} batch(es)...")
    
    # Embed each batch and collect results
    result = []
    for batch_idx, batch in enumerate(batches, 1):
        if len(batches) > 1:
            print(f"    Batch {batch_idx}/{len(batches)}: {len(batch)} paragraphs...", end=" ", flush=True)
        
        embeddings = embedding_fn(batch)  # Returns list of embedding vectors
        
        # Convert embeddings to proper format and pair with paragraphs
        for embedding, paragraph in zip(embeddings, batch):
            # Convert to list of Python floats
            if hasattr(embedding, 'tolist'):
                embedding_list = embedding.tolist()
            else:
                embedding_list = [float(x) for x in embedding]
            result.append((embedding_list, paragraph))
        
        if len(batches) > 1:
            print(f"✓")
    
    print(f"  Successfully embedded {len(result)} paragraphs")
    return result


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python embedtxt.py <file>                  # Embed single .txt or .csv file")
        print("  python embedtxt.py <folder>               # Embed all .txt and .csv in folder (stores to Chroma)")
        print("  python embedtxt.py <folder> <db_dir>      # Specify custom Chroma database directory")
        sys.exit(1)
    
    path = sys.argv[1]
    path_obj = Path(path).expanduser().resolve()
    
    if path_obj.is_file() and path_obj.suffix.lower() in [".txt", ".csv"]:
        # Single file mode
        print(f"Reading single file: {path_obj}")
        embedding_pairs = embed_paragraphs_from_file(path)
        
        if embedding_pairs:
            print(f"\nTotal paragraphs extracted: {len(embedding_pairs)}")
            for i, (embedding, paragraph) in enumerate(embedding_pairs[:3], 1):
                print(f"\n[Paragraph {i} preview]")
                print(paragraph[:100] + "...\n")
    
    elif path_obj.is_dir():
        # Folder mode - embed all and store to Chroma
        persist_dir = sys.argv[2] if len(sys.argv) > 2 else "./chroma_data"
        print(f"Reading folder: {path_obj}")
        embed_folder_of_txtfiles(path, persist_dir=persist_dir,collection_name=collection_name)
    
    else:
        print(f"Error: {path} is not a valid file (.txt or .csv) or folder")
        sys.exit(1)
