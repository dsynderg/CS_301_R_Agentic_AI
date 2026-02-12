#!/usr/bin/env python3
"""Embed conference talks from 2006_talks folder to Chroma database."""

import sys
from pathlib import Path

# Add parent directory to path so we can import embedtxt
sys.path.insert(0, str(Path(__file__).parent.parent))

from embedtxt import embed_folder_of_txtfiles


def main():
    """Embed all txt files from 2006_talks folder to persistent Chroma database."""
    # Get the 2006_talks folder (relative to script location)
    script_dir = Path(__file__).parent
    talks_folder = script_dir / "../mathtextbook"
    
    # Define where to store the Chroma database
    chroma_persist_dir = script_dir / "textbook_chroma"
    
    print(f"Embedding conference talks from: {talks_folder}")
    print(f"Chroma database will be stored at: {chroma_persist_dir}")
    
    # Embed all txt files in the folder
    embed_folder_of_txtfiles(
        folder_path=str(talks_folder),
        persist_dir=str(chroma_persist_dir),
        collection_name="textbook"
    )


if __name__ == "__main__":
    main()
