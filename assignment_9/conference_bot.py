import os
from chroma_db import get_chroma_client

# Use CHROMA_PERSIST_DIR env var or default to in-memory client
persist = os.environ.get("CHROMA_PERSIST_DIR")
chroma_client = get_chroma_client(persist_dir=persist)

def main():

    return



if __name__ == "__main__":
    print("Chroma client ready:", type(chroma_client))
