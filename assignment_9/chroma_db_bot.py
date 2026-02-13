import os
import sys
from openai import OpenAI
from chroma_db import get_chroma_client

# Default system prompt - can be overridden via command line or environment variable
DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful assistant answering questions about the provided documents. "
    "Use the provided excerpts to answer the user's question accurately and thoroughly. "
    "If the excerpts don't contain enough information, say so."
)


def main():
    """Query vector database and answer a single question using GPT-4o."""
    
    # Parse command-line arguments
    if len(sys.argv) < 2 or sys.argv[1] in ["-h", "--help"]:
        print("Usage:")
        print("  python conference_bot.py <chroma_db_dir> [collection_name] [system_prompt]")
        print("\nExamples:")
        print("  python conference_bot.py ./chroma_data conference_talks")
        print("  python conference_bot.py ./textbook_chroma textbook_paragraphs")
        print("  python conference_bot.py ./my_chroma my_collection \"You are a physics tutor...\"")
        sys.exit(0)
    
    # Get arguments
    chroma_dir = sys.argv[1]
    collection_name = sys.argv[2] if len(sys.argv) > 2 else "paragraphs"
    system_prompt = sys.argv[3] if len(sys.argv) > 3 else os.environ.get("CHATBOT_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT)
    
    # Validate Chroma directory exists
    if not os.path.isdir(chroma_dir):
        print(f"Error: Chroma directory not found: {chroma_dir}")
        print(f"Please specify a valid directory or run the embedding script first.")
        sys.exit(1)
    
    # Initialize Chroma client
    print(f"Connecting to Chroma database: {chroma_dir}")
    chroma_client = get_chroma_client(persist_dir=chroma_dir)
    
    # Get the collection
    try:
        collection = chroma_client.get_collection(name=collection_name)
    except Exception as e:
        print(f"Error: Could not find '{collection_name}' collection in {chroma_dir}.")
        print(f"Details: {e}")
        sys.exit(1)
    
    # Get user question
    print("\n" + "="*60)
    print(f"Q&A Bot - Collection: {collection_name}")
    print("="*60)
    question = input("\nAsk a question: ").strip()
    
    if not question:
        print("No question provided. Exiting.")
        return
    
    print("\nSearching vector database for relevant paragraphs...")
    
    # Query the vector database for relevant paragraphs
    results = collection.query(
        query_texts=[question],
        n_results=5,  # Get top 5 relevant paragraphs
        include=["documents", "metadatas"]
    )
    
    # Extract relevant paragraphs
    relevant_paragraphs = results["documents"][0] if results["documents"] else []
    
    if not relevant_paragraphs:
        print("No relevant paragraphs found in the database.")
        return
    
    # Build context
    context = "Here are relevant excerpts from the documents:\n\n"
    for i, para in enumerate(relevant_paragraphs, 1):
        context += f"[Excerpt {i}]\n{para}\n\n"
    
    print(f"Found {len(relevant_paragraphs)} relevant excerpts.\n")
    
    # Print the relevant excerpts
    print("="*60)
    print("Relevant Excerpts:")
    print("="*60)
    for i, para in enumerate(relevant_paragraphs, 1):
        print(f"\n[Excerpt {i}]")
        print(para)
    print("\n" + "="*60 + "\n")
    
    
    # Initialize OpenAI client
    openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    
    print(f"\nUsing system prompt:\n{system_prompt}\n")
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"{context}\n\nQuestion: {question}"}
    ]
    
    print("Generating answer with GPT-4o...\n")
    
    # Get response from ChatGPT 4o
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.7
    )
    
    # Print the answer
    print("="*60)
    print("Answer:")
    print("="*60)
    print(response.choices[0].message.content)
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
