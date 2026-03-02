# Before running this script:
# pip install gradio openai

import argparse
import asyncio
from pathlib import Path

import gradio as gr
from openai import AsyncOpenAI

from usage import print_usage, format_usage_markdown
from tools import ToolBox, get_assignments_for_next_days, get_courses


class ChatAgent:
    def __init__(self, model: str, prompt: str, show_reasoning: bool, reasoning_effort: str | None):
        self._ai = AsyncOpenAI()
        self.model = model
        self.show_reasoning = show_reasoning
        self.reasoning = {}
        if show_reasoning:
            self.reasoning['summary'] = 'auto'
        if 'gpt-5' in self.model and reasoning_effort:
            self.reasoning['effort'] = reasoning_effort

        self.usage = []
        self.usage_markdown = format_usage_markdown(self.model, [])

        self._history = []
        self._prompt = prompt
        if prompt:
            self._history.append({'role': 'system', 'content': prompt})
        
        # Initialize tools
        self.toolbox = ToolBox()
        self.toolbox.tool(get_assignments_for_next_days)
        self.toolbox.tool(get_courses)

    async def get_response(self, user_message: str):
        self._history.append({'role': 'user', 'content': user_message})

        # Keep requesting until we get a final response (no more tool calls)
        iteration = 0
        max_iterations = 10  # Prevent infinite loops
        
        while iteration < max_iterations:
            iteration += 1
            
            # Use Chat Completions API with tools instead of Responses API
            response = await self._ai.chat.completions.create(
                model=self.model,
                messages=self._history,
                tools=self.toolbox.tools,
                stream=False
            )
            
            # Normalize usage data for compatibility
            usage_obj = response.usage
            # Create a normalized usage object with expected attributes
            cached_tokens = 0
            if hasattr(usage_obj, 'prompt_tokens_details') and usage_obj.prompt_tokens_details:
                cached_tokens = getattr(usage_obj.prompt_tokens_details, 'cached_tokens', 0)
            
            normalized_usage = type('Usage', (), {
                'input_tokens': usage_obj.prompt_tokens,
                'output_tokens': usage_obj.completion_tokens,
                'input_tokens_details': type('Details', (), {
                    'cached_tokens': cached_tokens
                })(),
                'output_tokens_details': type('Details', (), {
                    'reasoning_tokens': 0
                })()
            })()
            
            self.usage.append(normalized_usage)
            self.usage_markdown = format_usage_markdown(self.model, self.usage)
            
            # Process response
            assistant_message = response.choices[0].message
            has_tool_use = False
            
            # Yield the text content if available
            if assistant_message.content:
                yield 'output', assistant_message.content
            
            # Check for tool calls
            if assistant_message.tool_calls:
                has_tool_use = True
                
                # Add assistant message to history
                self._history.append({
                    'role': 'assistant',
                    'content': assistant_message.content or '',
                    'tool_calls': [
                        {
                            'id': tool_call.id,
                            'type': 'function',
                            'function': {
                                'name': tool_call.function.name,
                                'arguments': tool_call.function.arguments
                            }
                        }
                        for tool_call in assistant_message.tool_calls
                    ]
                })
                
                # Process each tool call
                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_input = tool_call.function.arguments
                    
                    # Parse arguments if they're a JSON string
                    import json
                    if isinstance(tool_input, str):
                        try:
                            tool_input = json.loads(tool_input)
                        except json.JSONDecodeError:
                            tool_input = {}
                    
                    # Get the tool function
                    tool_func = self.toolbox.get_tool_function(tool_name)
                    if tool_func:
                        try:
                            # Call the tool
                            if isinstance(tool_input, dict):
                                tool_result = tool_func(**tool_input)
                            else:
                                tool_result = tool_func(tool_input)
                            
                            # Yield the tool use information
                            yield 'output', f"\n[Using tool: {tool_name}]\n"
                            
                            # Add tool result to history
                            self._history.append({
                                'role': 'tool',
                                'tool_call_id': tool_call.id,
                                'content': str(tool_result)
                            })
                        except Exception as e:
                            yield 'output', f"\n[Error executing tool {tool_name}: {e}]\n"
                            self._history.append({
                                'role': 'tool',
                                'tool_call_id': tool_call.id,
                                'content': f'Error: {str(e)}'
                            })
                    else:
                        yield 'output', f"\n[Tool not found: {tool_name}]\n"
            
            # If no tool use, we're done
            if not has_tool_use:
                break

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print_usage(self.model, self.usage)


async def _main_console(agent_args):
    with ChatAgent(**agent_args) as agent:
        while True:
            message = input('User: ')
            if not message:
                break

            reasoning_complete = True
            if agent.show_reasoning:
                print(' Reasoning '.center(30, '-'))
                reasoning_complete = False

            async for text_type, text in agent.get_response(message):
                if text_type == 'output' and not reasoning_complete:
                    print()
                    print('-' * 30)
                    print()
                    print('Agent: ')
                    reasoning_complete = True

                print(text, end='', flush=True)
            print()
            print()


def _main_gradio(agent_args):
    # Constrain width with CSS and center
    css = """
    /* limit overall Gradio app width and center it */
    .gradio-container, .gradio-app, .gradio-root {
      width: 120ch;
      max-width: 120ch !important;
      margin-left: auto !important;
      margin-right: auto !important;
      box-sizing: border-box !important;
    }
    
    #reasoning-md {
        max-height: 300px;
        overflow-y: auto;
    }
    """

    reasoning_view = gr.Markdown('', elem_id='reasoning-md')
    usage_view = gr.Markdown('')

    with gr.Blocks(css=css, theme=gr.themes.Monochrome()) as demo:
        agent = gr.State()

        async def get_response(message, chat_view_history, agent):
            output = ""
            reasoning = ""

            async for text_type, text in agent.get_response(message):
                if text_type == 'reasoning':
                    reasoning += text
                elif text_type == 'output':
                    output += text
                else:
                    raise NotImplementedError(text_type)

                yield output, reasoning, agent.usage_markdown, agent

            yield output, reasoning, agent.usage_markdown, agent

        with gr.Row():
            with gr.Column(scale=5):
                bot = gr.Chatbot(
                    label=' ',
                    height=600,
                    resizable=True,
                )
                chat = gr.ChatInterface(
                    chatbot=bot,
                    fn=get_response,
                    additional_inputs=[agent],
                    additional_outputs=[reasoning_view, usage_view, agent]
                )

            with gr.Column(scale=1):
                reasoning_view.render()
                usage_view.render()

        demo.load(fn=lambda: ChatAgent(**agent_args), outputs=[agent])

    demo.launch()


def main(prompt_path: Path, model: str, show_reasoning, reasoning_effort: str | None, use_web: bool):
    agent_args = dict(
        model=model,
        prompt=prompt_path.read_text() if prompt_path else '',
        show_reasoning=show_reasoning,
        reasoning_effort=reasoning_effort

    )

    if use_web:
        _main_gradio(agent_args)
    else:
        asyncio.run(_main_console(agent_args))


# Launch app
if __name__ == "__main__":
    parser = argparse.ArgumentParser('ChatBot')
    parser.add_argument('prompt_file', nargs='?', type=Path, default=None)
    parser.add_argument('--web', action='store_true')
    parser.add_argument('--model', default='gpt-5-nano')
    parser.add_argument('--show-reasoning', action='store_true', default=True)
    parser.add_argument('--reasoning-effort', default='low')
    args = parser.parse_args()
    main(args.prompt_file, args.model, args.show_reasoning, args.reasoning_effort, args.web)
