import asyncio
from pathlib import Path

import yaml
from openai import AsyncOpenAI

from run_agent import run_agent
from tools import ToolBox, get_assignments_for_next_days, get_courses, create_clickup_task
from usage import print_usage


def load_canvas_lookup_agent(canvas_yaml_path: Path) -> dict:
	agent = yaml.safe_load(canvas_yaml_path.read_text())
	if not isinstance(agent, dict):
		raise ValueError("canvas.yaml must parse into a mapping/object")

	prompt = agent.get("prompt", "")
	reference = canvas_yaml_path.read_text()
	agent["prompt"] = (
		f"{prompt}\n\n"
		"Reference configuration (canvas.yaml):\n"
		"```yaml\n"
		f"{reference}\n"
		"```"
	)
	return agent


def build_toolbox() -> ToolBox:
	toolbox = ToolBox()
	toolbox.tool(get_assignments_for_next_days)
	toolbox.tool(get_courses)
	toolbox.tool(create_clickup_task)
	return toolbox


async def ask_canvas(message: str, canvas_yaml_path: Path = Path("canvas.yaml")) -> str:
	client = AsyncOpenAI()
	toolbox = build_toolbox()
	agent = load_canvas_lookup_agent(canvas_yaml_path)
	usage = []
	history = []

	response = await run_agent(client, toolbox, agent, message, history, usage)
	print_usage(agent.get("model", "gpt-5-mini"), usage)
	return response


if __name__ == "__main__":
	import sys

	if len(sys.argv) < 2:
		raise SystemExit("Usage: python run_agent_practice.py \"<question>\" [canvas_yaml_path]")

	user_message = sys.argv[1]
	config_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("canvas.yaml")
	print(asyncio.run(ask_canvas(user_message, config_path)))
