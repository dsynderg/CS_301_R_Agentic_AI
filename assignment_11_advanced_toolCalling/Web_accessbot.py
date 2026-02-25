# Before running this script:
# pip install gradio openai

import argparse
import asyncio
from pathlib import Path

import gradio as gr
from openai import AsyncOpenAI

from usage import print_usage, format_usage_markdown


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

    async def get_response(self, user_message: str):
        self._history.append({'role': 'user', 'content': user_message})

        stream = self._ai.responses.stream(
            input=self._history,
            model=self.model,
            reasoning=self.reasoning,
            tools=[
                {"type": "web_search"},
            ],
        )
        async with stream as stream:
            async for event in stream:
                # Debug: only print specific event types
                allowed_events = [
                    "response.web_search_call.in_progress",
                    "response.web_search_call.searching",
                    "response.web_search_call.completed",
                    "response.output_item.done",
                    "response.output_item.added"
                ]
                
                if event.type in allowed_events:
                    print(f"DEBUG: Event type: {event.type}", flush=True)
                
                if event.type == "response.output_text.delta":
                    yield 'output', event.delta

                if event.type == "response.reasoning_summary_text.delta":
                    yield 'reasoning', event.delta
                
                # Try multiple event types for tool detection
                if event.type == "response.output_item.added":
                    if hasattr(event, 'item') and hasattr(event.item, 'type'):
                        print(f"DEBUG: Item added - type: {event.item.type}", flush=True)
                        if event.item.type == 'tool_use':
                            tool_name = event.item.name
                            tool_input = getattr(event.item, 'input', {})
                            print(f"DEBUG: Tool use detected - {tool_name}: {tool_input}", flush=True)
                            yield 'reasoning', f"\n\n________WEB SEARCH______\n\n**🔍 Web Search Tool Call:**\n- Tool: `{tool_name}`\n- Input: `{tool_input}`\n"
                        if event.item.type == 'web_search_call':
                            yield 'reasoning', f"\n\n________WEB SEARCH______\n\n"
                
                if event.type == "response.output_item.done":
                    if hasattr(event, 'item') and hasattr(event.item, 'type'):
                        if event.item.type == 'tool_use':
                            tool_name = event.item.name
                            tool_input = getattr(event.item, 'input', {})
                            print(f"DEBUG: Tool use completed - {tool_name}: {tool_input}", flush=True)
                            yield 'reasoning', f"\n\n________WEB SEARCH______\n\n**🔍 Web Search Tool Call:**\n- Tool: `{tool_name}`\n- Input: `{tool_input}`\n"

            response = await stream.get_final_response()
            self.usage.append(response.usage)
            self.usage_markdown = format_usage_markdown(self.model, self.usage)
            self._history.extend(
                response.output
            )

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
