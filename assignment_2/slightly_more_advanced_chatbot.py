from openai import Client
from usage import print_usage
from time import time
import pandas as pd

def main():
    client = Client()
    model = "gpt-4o-nano"
    
    # Read context from text file with validation
    context = ""
    try:
        context_file = input("Enter context file path (press enter for context1.txt or type 'no' to skip): ")
        if context_file.lower() != "no":
            if not context_file:
                context_file = "context1.txt"
            with open(context_file, "r") as f:
                context = f.read()
            print(f"Loaded context: {context_file}")
    except FileNotFoundError:
        print("File not found. Skipping context.")
    except Exception as e:
        print(f"Error reading file: {e}. Skipping context.")
    
    # Read CSV file with validation
    dataframe = None
    try:
        csv_file = input("Enter CSV file path (press enter to skip): ")
        if csv_file:
            dataframe = pd.read_csv(csv_file)
            print(f"Loaded CSV: {csv_file}")
    except FileNotFoundError:
        print("CSV file not found. Skipping CSV.")
    except Exception as e:
        print(f"Error reading CSV file: {e}. Skipping CSV.")
    
    # Get user input
    user_input = input("You: ")
    
    # Send to OpenAI API
    if context:
        full_input = f"{context}\n{user_input}"
    elif dataframe is not None:
        full_input = f"{dataframe.to_string()}\n{user_input}"
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