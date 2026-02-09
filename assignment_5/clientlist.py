from openai import OpenAI

def main():
    client = OpenAI()
    
    # Get all available models
    models = client.models.list()
    
    # Extract model IDs
    model_list = [model.id for model in models.data]
    
    # Write to text file
    with open("available_models.txt", "w") as f:
        for model in model_list:
            f.write(f"{model}\n")
    
    print(f"Found {len(model_list)} models. List saved to available_models.txt")

if __name__ == "__main__":
    main()
