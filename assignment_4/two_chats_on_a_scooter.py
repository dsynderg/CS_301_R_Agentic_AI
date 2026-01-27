from openai import Client
from usage import print_usage
from time import time
import pandas as pd
import os  # Import os module
import sys

def add_context(contextlist, role, message):
    contextlist.append({"role": role, "content": message})
    return contextlist

def main(system_prompt, context):
    contextList = [system_prompt, context]
    for i in range(150):
        contextList.append(system_prompt)
    usages = []
    client = Client()
    model = "gpt-4o"
    user_msg = input("start the chats talking:")

    for _ in range(20):
        
        if user_msg.lower() in ["exit", "quit"]:
            
            print_usage(model, usages)
            print("Exiting chatbot.")
            return 0
        add_context(contextList, "user", user_msg)
        response = client.responses.create(
            model=model,
            input=contextList
            # reasoning={'effort': 'low'}
        )
        print(f"Bot: {response.output_text}")
        add_context(contextList, "assistant", response.output_text)
        usages.append(response.usage)
        user_msg = response.output_text
    
    
    print_usage(model, usages)
    print("Exiting chatbot.")
    return 0

if __name__ == "__main__":
    # the argv[1] should be the system prompt file, 
    # the second should be the context
    system_prompt = sys.argv[1] if len(sys.argv) > 1 else ""
    context = sys.argv[2] if len(sys.argv) > 2 else "context1.txt"
    if system_prompt != "":
        with open(system_prompt, "r") as f:
            system_prompt = f.read()
        system_injection = {"role": "system", "content": system_prompt}
    else:
        system_injection = {"role": "system", "content": "You are a helpful assistant."}
    if context != "":
        with open(context, "r") as f:
            context = f.read()
        context_injection = {"role": "system", "content": context}
    else:
        context_injection = {"role": "system", "content": ""}
   
    exit_code = main(system_prompt=system_injection, context=context_injection)
    sys.exit(exit_code)
