import os
import sys
from openai import OpenAI
from chroma_db import get_chroma_client

# Default system prompt - can be overridden via command line or environment variable
DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful assistant answering questions about General Conference talks. "
    "Use the provided excerpts to answer the user's question accurately and thoroughly. "
    "If the excerpts don't contain enough information, say so."
)


def main():
    """Query vector database and answer a single question using GPT-4o."""
    
    # Initialize Chroma client
    persist_dir = os.environ.get("CHROMA_PERSIST_DIR", "./chroma_data")
    chroma_client = get_chroma_client(persist_dir=persist_dir)
    
    # Get the collection
    try:
        collection = chroma_client.get_collection(name="conference_talks")
    except Exception as e:
        print(f"Error: Could not find 'conference_talks' collection. Make sure to run embed_conference_talks.py first.")
        print(f"Details: {e}")
        return
    
    # Get user question
    print("\n" + "="*60)
    print("Conference Talks Q&A Bot")
    print("="*60)
    question = input("\nAsk a question about the conference talks: ").strip()
    
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
    context = "Here are relevant excerpts from General Conference talks:\n\n"
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
    
    # Get system prompt (from command line, environment variable, or default)
    if len(sys.argv) > 1:
        system_prompt = " ".join(sys.argv[1:])
    else:
        system_prompt = os.environ.get("CHATBOT_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT)
    
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
