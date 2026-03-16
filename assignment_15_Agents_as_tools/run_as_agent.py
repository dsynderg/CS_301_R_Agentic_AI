from __future__ import annotations

import argparse
import asyncio
import json
import logging
import subprocess
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Callable, Iterable
import yaml
from openai import AsyncOpenAI

from class_stuff.run_agent import Agent, as_tool, conclude, current_agent, run_agent
from class_stuff.tools import ToolBox
from usage import print_usage


current_toolbox: ContextVar[ToolBox | None] = ContextVar('current_toolbox', default=None)


def _normalize_tools(tools: Iterable[Callable] | dict[str, Callable] | None) -> dict[str, Callable]:
    if tools is None:
        return {}
    if isinstance(tools, dict):
        return tools
    return {fn.__name__: fn for fn in tools}


def _build_agent(
    *,
    name: str,
    description: str = "",
    model: str = "gpt-5-nano",
    prompt: str = "",
    tools: list[str] | None = None,
    kwargs: dict[str, Any] | None = None,
    kwarks: dict[str, Any] | None = None,  # alias supported on purpose
) -> Agent:
    final_kwargs = kwargs if kwargs is not None else (kwarks or {})
    return {
        "name": name,
        "description": description,
        "model": model,
        "prompt": prompt,
        "tools": tools or [],
        "kwargs": final_kwargs,
    }


async def run_pluggable_agent(
    *,
    message: str,
    # Direct agent fields (used when yaml_path is None)
    name: str = "main",
    description: str = "",
    model: str = "gpt-5-mini",
    prompt: str = "",
    tools: list[str] | None = None,
    kwargs: dict[str, Any] | None = None,
    kwarks: dict[str, Any] | None = None,
    # YAML mode
    yaml_path: str | Path | None = None,
    main_agent_name: str = "main",
    # Runtime tools
    tool_functions: Iterable[Callable] | dict[str, Callable] | None = None,
    # Optional dependency injection
    client: AsyncOpenAI | None = None,
    # Shared usage accumulator across multiple runs
    usage: list[tuple[str, Any]] | None = None,
) -> str | None:
    """
    Plug-and-play agent runner:
    - If yaml_path is provided: load agents from YAML (single or multi-doc).
    - If yaml_path is None: build one agent from passed fields.
    - Registers provided Python callables as tools.
    - Supports kwargs and kwarks (alias).
    - If a usage list is passed, usage is appended to it in place.
    """
    local_client = client or AsyncOpenAI()
    usage = usage if usage is not None else []

    toolbox = ToolBox()
    toolbox.tool(conclude)

    provided_tools = _normalize_tools(tool_functions)
    for fn in provided_tools.values():
        toolbox.tool(fn)

    if yaml_path:
        raw = Path(yaml_path).read_text(encoding="utf-8")
        docs = [doc for doc in yaml.safe_load_all(raw) if doc]
        if not docs:
            raise ValueError("YAML file has no agent definitions.")

        agents: list[Agent] = docs

        # Add non-main agents as callable tools
        for ag in agents:
            if ag.get("name") != main_agent_name:
                toolbox.tool(as_tool(local_client, toolbox, ag, usage=usage))

        try:
            main_agent = next(a for a in agents if a.get("name") == main_agent_name)
        except StopIteration as e:
            raise ValueError(f"No main agent named '{main_agent_name}' found in YAML.") from e
    else:
        main_agent = _build_agent(
            name=name,
            description=description,
            model=model,
            prompt=prompt,
            tools=tools,
            kwargs=kwargs,
            kwarks=kwarks,
        )

    token = current_toolbox.set(toolbox)
    try:
        response = await run_agent(
            local_client,
            toolbox,
            main_agent,
            user_message=message,
            usage=usage,
        )
    finally:
        current_toolbox.reset(token)
    return response


def talk_to_user(message: str) -> str:
    """
    Use this function to communicate with the user.
    All communication to and from the user **MUST**
    be through this tool.
    :param message: The message to send to the user.
    :return: The user's response.
    """
    _agent = current_agent.get(None)
    name = _agent['name'] if _agent else 'Agent'
    print(f'{name}: {message}')
    return input('User: ')


def run_terminal(command: str) -> str:
    """
    Execute a terminal command and return stdout/stderr + exit code.
    :param command: Command to run in the shell.
    :return: Combined command output.
    """
    completed = subprocess.run(command, shell=True, capture_output=True, text=True)
    output: list[str] = []
    if completed.stdout:
        output.append(completed.stdout.strip())
    if completed.stderr:
        output.append(completed.stderr.strip())
    output.append(f'exit_code={completed.returncode}')
    return '\n'.join(part for part in output if part)


def terminal_writer(command: str) -> str:
    """
    Alias tool for writing/executing terminal commands.
    Useful for YAMLs that reference terminal_writer directly as a tool.
    """
    return run_terminal(command)

async def run_parallel_tools(calls_json: str) -> str:
    """
    Run multiple tool calls concurrently.
    Input JSON format:
      [{"tool": "tool_name", "args": {"k": "v"}}, ...]
    Returns JSON with one result object per call.
    """
    toolbox = current_toolbox.get(None)
    if toolbox is None:
        return json.dumps({"error": "No active toolbox in context."})

    try:
        calls = json.loads(calls_json)
    except json.JSONDecodeError as exc:
        return json.dumps({"error": f"Invalid JSON: {exc}"})

    if not isinstance(calls, list):
        return json.dumps({"error": "calls_json must decode to a list."})

    async def _execute(call: dict[str, Any]) -> dict[str, Any]:
        tool_name = call.get('tool')
        args = call.get('args', {})
        if not isinstance(tool_name, str):
            return {"tool": tool_name, "ok": False, "error": "Missing or invalid 'tool' name."}
        if tool_name == 'run_parallel_tools':
            return {"tool": tool_name, "ok": False, "error": "Nested run_parallel_tools is not allowed."}
        if not isinstance(args, dict):
            return {"tool": tool_name, "ok": False, "error": "'args' must be an object."}
        try:
            result = await toolbox.run_tool(tool_name, **args)
            return {"tool": tool_name, "ok": True, "result": str(result)}
        except Exception as exc:
            return {"tool": tool_name, "ok": False, "error": str(exc)}

    results = await asyncio.gather(*(_execute(call) for call in calls))
    return json.dumps({"results": results})


def _load_yaml_docs(yaml_path: Path) -> list[dict[str, Any]]:
    return [doc for doc in yaml.safe_load_all(yaml_path.read_text(encoding='utf-8')) if doc]


def _yaml_uses_tool_docs(docs: list[dict[str, Any]], tool_name: str) -> bool:
    for agent in docs:
        tools = agent.get('tools', []) or []
        if tool_name in tools:
            return True
    return False


def _yaml_has_agent_name_docs(docs: list[dict[str, Any]], agent_name: str) -> bool:
    return any(agent.get('name') == agent_name for agent in docs)


class _AgentFilter(logging.Filter):
    """Injects the current agent name and only passes tool-call and agent lines."""
    def filter(self, record):
        agent = current_agent.get(None)
        record.agent = agent['name'] if agent else '-'
        msg = record.getMessage()
        # Show: AGENT <name> lines and TOOL <name>(<args>) lines (not result lines)
        return msg.startswith('AGENT ') or (
            msg.startswith('TOOL ') and ' -> ' not in msg
        )


def _configure_debug_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('[%(agent)s] %(message)s'))
    handler.addFilter(_AgentFilter())
    for name in ('class_stuff.tools', 'class_stuff.run_agent'):
        log = logging.getLogger(name)
        log.setLevel(logging.DEBUG)
        log.addHandler(handler)
        log.propagate = False


async def main(yaml_path: Path, message: str | None, debug: bool = False) -> None:
    if debug:
        _configure_debug_logging()
    usages = []
    docs = _load_yaml_docs(yaml_path)

    runtime_tools: list[Callable] = [talk_to_user]
    if _yaml_uses_tool_docs(docs, 'run_terminal'):
        runtime_tools.append(run_terminal)
    if _yaml_uses_tool_docs(docs, 'run_parallel_tools'):
        runtime_tools.append(run_parallel_tools)
    if (
        _yaml_uses_tool_docs(docs, 'terminal_writer')
        and not _yaml_has_agent_name_docs(docs, 'terminal_writer')
    ):
        runtime_tools.append(terminal_writer)

    try:
        response = await run_pluggable_agent(
            yaml_path=yaml_path,
            message=message or '',
            tool_functions=runtime_tools,
            usage=usages,
        )
        if response:
            print(response)
            print()
    finally:
        print_usage(usages)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run an agent from a YAML file.')
    parser.add_argument('yaml_path', type=Path, help='Path to the agent YAML file.')
    parser.add_argument('message', nargs='?', default=None, help='Initial message to the agent.')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging.')
    args = parser.parse_args()
    try:
        asyncio.run(main(args.yaml_path, args.message, args.debug))
    except KeyboardInterrupt:
        pass
