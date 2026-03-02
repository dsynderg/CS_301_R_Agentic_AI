"""
Test script to verify Canvas API tools integration with the chatbot
"""

import asyncio
from basicChatbot import ChatAgent


async def test_canvas_tools():
    """Test Canvas API tools"""
    
    print("=" * 60)
    print("Testing Canvas API Tools Integration")
    print("=" * 60)
    
    # Create a chat agent with no system prompt
    agent = ChatAgent(
        model='gpt-4o-mini',
        prompt='You are a helpful assistant that can access Canvas assignments. Be concise in your responses.',
        show_reasoning=False,
        reasoning_effort=None
    )
    
    # Test 1: Get all courses
    print("\n[Test 1] Getting courses from Canvas...")
    print("-" * 60)
    
    try:
        async for output_type, text in agent.get_response("What canvas courses am I enrolled in?"):
            if output_type == 'output':
                print(text, end='', flush=True)
        print("\n")
    except Exception as e:
        print(f"Error: {e}\n")
    
    # Test 2: Get assignments for next 7 days
    print("\n[Test 2] Getting assignments for next 7 days...")
    print("-" * 60)
    
    try:
        async for output_type, text in agent.get_response("What assignments are due in the next 7 days?"):
            if output_type == 'output':
                print(text, end='', flush=True)
        print("\n")
    except Exception as e:
        print(f"Error: {e}\n")
    
    # Test 3: Get assignments for next 30 days
    print("\n[Test 3] Getting assignments for next 30 days...")
    print("-" * 60)
    
    try:
        async for output_type, text in agent.get_response("Show me assignments due in the next 30 days, can you summarize them?"):
            if output_type == 'output':
                print(text, end='', flush=True)
        print("\n")
    except Exception as e:
        print(f"Error: {e}\n")
    
    print("=" * 60)
    print("Tests completed!")
    print("=" * 60)


if __name__ == '__main__':
    asyncio.run(test_canvas_tools())
