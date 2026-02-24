# Before running this script:
# pip install gradio openai

import argparse
import asyncio
import sys
from pathlib import Path

import gradio as gr
from openai import AsyncOpenAI

from usage import print_usage, format_usage_markdown


class ChatAgent:
    def __init__(self, model: str, prompt: str, show_thinking: bool = True):
        self._ai = AsyncOpenAI()
        self.usage = []
        self.tool_log = []
        self.model = model
        self.show_thinking = show_thinking
        self.reasoning = None
        if 'gpt-5' in self.model:
            self.reasoning = {'effort': 'low'}
        self._prompt = prompt
        self._history = []
        if prompt:
            self._history.append({'role': 'system', 'content': prompt})
        if self.show_thinking:
            self._history.append({
                'role': 'system',
                'content': (
                    'When you respond, include a section labeled "Thinking summary:" '
                    'with 2-4 brief bullet points that describe high-level reasoning. '
                    'Keep it abstract and do not reveal hidden chain-of-thought.'
                )
            })

    def _split_thinking(self, text: str):
        marker = 'Thinking summary:'
        if marker in text:
            answer, thinking = text.split(marker, 1)
            return answer.strip(), thinking.strip()
        return text.strip(), ''

    def _format_tool_log(self):
        if not self.tool_log:
            return '_No tool calls yet._'
        return '\n'.join(f'- {entry}' for entry in self.tool_log)

    async def get_response(self, user_message: str):
        self._history.append({'role': 'user', 'content': user_message})

        while True:
            response = await self._ai.responses.create(
                input=self._history,
                model=self.model,
                # tools=[
                #     {"type": "web_search"},
                # ],
                reasoning=self.reasoning
            )
            self.usage.append(response.usage)
            
            # Check if model wants to use a tool
            if response.output and hasattr(response.output[0], 'type') and response.output[0].type == 'tool_use':
                tool_use = response.output[0]
                print(f"\nAgent wants to use tool: {tool_use.name}")
                print(f"Parameters: {tool_use.input}")
                
                # Ask human for confirmation
                confirm = input("Allow this tool call? (yes/no): ").strip().lower()
                
                if confirm in ['yes', 'y']:
                    self.tool_log.append(
                        f"{tool_use.name} allowed with params: {tool_use.input}"
                    )
                    # Execute the tool call
                    print(f"Executing {tool_use.name}...")
                    # For now, assume web_search succeeds
                    tool_result = f"Tool {tool_use.name} executed successfully with result: [search results would go here]"
                    
                    # Add assistant response and tool result to history
                    self._history.extend(response.output)
                    self._history.append({
                        'role': 'user',
                        'content': [
                            {
                                'type': 'tool_result',
                                'tool_use_id': tool_use.id,
                                'content': tool_result
                            }
                        ]
                    })
                else:
                    self.tool_log.append(
                        f"{tool_use.name} rejected with params: {tool_use.input}"
                    )
                    # User rejected tool call
                    print("Tool call rejected by user.")
                    self._history.extend(response.output)
                    # Ask model to continue without the tool
                    self._history.append({
                        'role': 'user',
                        'content': 'The user has declined this tool use. Please provide your response without using tools.'
                    })
            else:
                # No tool use, return final response
                self._history.extend(response.output)
                answer, thinking = self._split_thinking(response.output_text or '')
                return answer, thinking

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print_usage(self.model, self.usage)


async def _main_console(agent):
    while True:
        message = input('User: ')
        if not message:
            break
        response, thinking = await agent.get_response(message)
        print('Agent:', response)
        if thinking:
            print('\nThinking summary:')
            print(thinking)


def _main_gradio(agent):
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
    """

    usage_view = gr.Markdown(format_usage_markdown(agent.model, []))
    thinking_view = gr.Markdown('')
    tool_calls_view = gr.Markdown(agent._format_tool_log())

    with gr.Blocks(css=css, theme=gr.themes.Monochrome()) as demo:
        async def get_response(message, chat_view_history):
            response, thinking = await agent.get_response(message)
            usage_content = format_usage_markdown(agent.model, agent.usage)
            tool_calls_content = agent._format_tool_log()
            return response, usage_content, thinking, tool_calls_content

        with gr.Row():
            with gr.Column(scale=5):
                bot = gr.Chatbot(
                    label=' ',
                    # type='messages',
                    height=600,
                    resizable=True,
                )
                chat = gr.ChatInterface(
                    # type=bot.type,
                    chatbot=bot,
                    fn=get_response,
                    additional_outputs=[usage_view, thinking_view, tool_calls_view]
                )

            with gr.Column(scale=1):
                usage_view.render()
                thinking_view.render()
                tool_calls_view.render()

    demo.launch(share = True)


def main(prompt_path: Path, model: str, use_web: bool):
    with ChatAgent(model, prompt_path.read_text() if prompt_path else '') as agent:
        if use_web:
            _main_gradio(agent)
        else:
            asyncio.run(_main_console(agent))


# Launch app
if __name__ == "__main__":
    parser = argparse.ArgumentParser('ChatBot')
    parser.add_argument('prompt_file', nargs='?', type=Path, default=None)
    parser.add_argument('--web', action='store_true')
    parser.add_argument('--model', default='gpt-5-nano')
    args = parser.parse_args()
    main(args.prompt_file, args.model, args.web)