# Before running this script:
# pip install gradio openai requests beautifulsoup4

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import gradio as gr
from openai import AsyncOpenAI

from tools import ToolBox
from usage import print_usage, format_usage_markdown

WEB_TOOLS_PATH = Path(__file__).resolve().parent / "web_tools"
if str(WEB_TOOLS_PATH) not in sys.path:
    sys.path.insert(0, str(WEB_TOOLS_PATH))

from url_retriver import scrape_webpage
from conference_url_finder import generate_conference_speaker_url


url_tools = ToolBox()


@url_tools.tool
def retrieve_url(url: str) -> str:
    """Normalize a URL and confirm it can be retrieved."""
    normalized_url = url.strip()
    if not normalized_url:
        return "Error: URL is empty."

    if not normalized_url.startswith(("http://", "https://")):
        normalized_url = f"https://{normalized_url}"

    content = scrape_webpage(normalized_url)
    if content is None:
        return f"Error: Failed to retrieve content from {normalized_url}"

    return normalized_url


@url_tools.tool
def find_conference_url(speaker_name: str) -> str:
    """Return the LDS General Conference speaker page URL for a name. It must be their full name as listed on the conference program, including middle initial if they have one."""
    normalized_name = speaker_name.strip()
    if not normalized_name:
        return "Error: Speaker name is empty."
    return generate_conference_speaker_url(normalized_name)


class ChatAgent:
    def __init__(self, model: str, prompt: str, show_reasoning: bool, reasoning_effort: str | None):
        self._ai = AsyncOpenAI()
        self.model = model
        self.show_reasoning = show_reasoning
        self.reasoning = {}
        if show_reasoning:
            self.reasoning["summary"] = "auto"
        if "gpt-5" in self.model and reasoning_effort:
            self.reasoning["effort"] = reasoning_effort

        self.usage = []
        self.usage_markdown = format_usage_markdown(self.model, [])

        self._history = []
        self._prompt = prompt
        if prompt:
            self._history.append({"role": "system", "content": prompt})

    async def get_response(self, user_message: str):
        self._history.append({"role": "user", "content": user_message})

        while True:
            response = await self._ai.responses.create(
                input=self._history,
                model=self.model,
                reasoning=self.reasoning,
                tools=url_tools.tools,
            )

            self.usage.append(response.usage)
            self.usage_markdown = format_usage_markdown(self.model, self.usage)
            self._history.extend(response.output)

            for item in response.output:
                if item.type == "reasoning":
                    for chunk in item.summary:
                        yield "reasoning", chunk.text

                elif item.type == "function_call":
                    yield "reasoning", f"{item.name}({item.arguments})"

                    func = url_tools.get_tool_function(item.name)
                    args = json.loads(item.arguments)
                    result = func(**args)
                    self._history.append(
                        {
                            "type": "function_call_output",
                            "call_id": item.call_id,
                            "output": str(result),
                        }
                    )
                    yield "reasoning", str(result)

                elif item.type == "message":
                    for chunk in item.content:
                        yield "output", chunk.text
                    return

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print_usage(self.model, self.usage)


async def _main_console(agent_args):
    with ChatAgent(**agent_args) as agent:
        while True:
            message = input("User: ")
            if not message:
                break

            reasoning_complete = True
            if agent.show_reasoning:
                print(" Reasoning ".center(30, "-"))
                reasoning_complete = False

            async for text_type, text in agent.get_response(message):
                if text_type == "output" and not reasoning_complete:
                    print()
                    print("-" * 30)
                    print()
                    print("Agent: ")
                    reasoning_complete = True

                print(text, end="", flush=True)
            print()
            print()


def _main_gradio(agent_args):
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

    reasoning_view = gr.Markdown("", elem_id="reasoning-md")
    usage_view = gr.Markdown("")

    with gr.Blocks(css=css, theme=gr.themes.Monochrome()) as demo:
        agent = gr.State()

        async def get_response(message, chat_view_history, agent):
            output = ""
            reasoning = ""

            async for text_type, text in agent.get_response(message):
                if text_type == "reasoning":
                    reasoning += text
                elif text_type == "output":
                    output += text
                else:
                    raise NotImplementedError(text_type)

                yield output, reasoning, agent.usage_markdown, agent

            yield output, reasoning, agent.usage_markdown, agent

        with gr.Row():
            with gr.Column(scale=5):
                bot = gr.Chatbot(
                    label=" ",
                    height=600,
                    resizable=True,
                )
                gr.ChatInterface(
                    chatbot=bot,
                    fn=get_response,
                    additional_inputs=[agent],
                    additional_outputs=[reasoning_view, usage_view, agent],
                )

            with gr.Column(scale=1):
                reasoning_view.render()
                usage_view.render()

        demo.load(fn=lambda: ChatAgent(**agent_args), outputs=[agent])

    demo.launch()


def main(prompt_path: Path, model: str, show_reasoning, reasoning_effort: str | None, use_web: bool):
    agent_args = dict(
        model=model,
        prompt=prompt_path.read_text() if prompt_path else """When you call the conference url, make sure to include the speaker's full name as listed on the conference program, including middle initial if they have one. 
        for example if the user says Elder Holland, you should call the conference url tool with "Jeffrey R Holland"
        another example is Elder Cook, you should call the conference url tool with "Quentin L Cook"
        if the name has punctuation, remove it before calling the tool""",
        
        show_reasoning=show_reasoning,
        reasoning_effort=reasoning_effort,
    )

    if use_web:
        _main_gradio(agent_args)
    else:
        asyncio.run(_main_console(agent_args))


if __name__ == "__main__":
    parser = argparse.ArgumentParser("URL ToolBot")
    parser.add_argument("prompt_file", nargs="?", type=Path, default=None)
    parser.add_argument("--web", action="store_true")
    parser.add_argument("--model", default="gpt-5-nano")
    parser.add_argument("--show-reasoning", action="store_true")
    parser.add_argument("--reasoning-effort", default="low")
    args = parser.parse_args()
    main(args.prompt_file, args.model, args.show_reasoning, args.reasoning_effort, args.web)
