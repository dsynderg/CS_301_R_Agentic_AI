#!/usr/bin/env python3
"""Embed conference talks from 2006_talks folder to Chroma database."""

from pathlib import Path
from embedtxt import embed_folder_of_txtfiles


def main():
    """Embed all txt files from 2006_talks folder to persistent Chroma database."""
    # Get the 2006_talks folder (relative to script location)
    script_dir = Path(__file__).parent
    talks_folder = script_dir / "2006_talks"
    
    # Define where to store the Chroma database
    chroma_persist_dir = script_dir / "chroma_data"
    
    print(f"Embedding conference talks from: {talks_folder}")
    print(f"Chroma database will be stored at: {chroma_persist_dir}")
    
    # Embed all txt files in the folder
    embed_folder_of_txtfiles(
        folder_path=str(talks_folder),
        persist_dir=str(chroma_persist_dir),
        collection_name="conference_talks"
    )


if __name__ == "__main__":
    main()
