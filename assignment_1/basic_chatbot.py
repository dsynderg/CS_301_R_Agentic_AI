from openai import Client
from usage import print_usage
from time import time

def main():
    client = Client()
    model = "gpt-5-nano"
    
    # Read context from text file with validation
    context = ""
    while True:
        try:
            context_file = input("Enter context file path (press enter for context1.txt or type 'no' to skip): ")
            if context_file.lower() == "no":
                break
            if not context_file:
                context_file = "context1.txt"
            with open(context_file, "r") as f:
                context = f.read()
            break
        except FileNotFoundError:
            print("File not found. Please enter a valid file path.")
        except Exception as e:
            print(f"Error reading file: {e}. Please try again.")
    
    # Get user input
    user_input = input("You: ")
    
    # Send to OpenAI API
    if context:
        full_input = f"{context}\n{user_input}"
    else:
        full_input = user_input
    
    # Start timer
    start_time = time()
    response = client.responses.create(
        model=model,
        input=full_input
        # reasoning={'effort': 'low'}
    )
    # Stop timer
    end_time = time()
    elapsed_time = end_time - start_time
    
    # Display response
    print(f"\nAssistant: \n {response.output_text}")
    print(f"Response time: {elapsed_time:.2f} seconds")
    print_usage(model, response.usage)

if __name__ == "__main__":
    main()