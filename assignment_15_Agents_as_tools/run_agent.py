from __future__ import annotations

import argparse
import asyncio
import json
import logging
import subprocess
import sys
import time
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Callable, Iterable, TypedDict

import yaml
from openai import AsyncOpenAI

from tools import ToolBox
from usage import print_usage

logger = logging.getLogger(__name__)
current_agent = ContextVar('current_agent')
current_toolbox: ContextVar[ToolBox | None] = ContextVar('current_toolbox', default=None)


class Agent(TypedDict):
    name: str
    description: str
    model: str
    prompt: str
    tools: list[str]
    kwargs: dict


def conclude():
    """Conclude the conversation."""


async def run_agent(
    client,
    toolbox,
    agent: Agent,
    user_message: str | None = None,
    history: list[dict[str, Any]] | None = None,
    usage: list[tuple[str, Any]] | None = None,
) -> str | None:
    current_agent.set(agent)

    history = history if history is not None else []
    usage = usage if usage is not None else []

    if user_message:
        history.append({'role': 'user', 'content': user_message})

    while True:
        history_for_response = history
        if prompt := agent.get('prompt'):
            history_for_response = history_for_response + [{'role': 'system', 'content': prompt}]

        start = time.time()
        logger.debug('AGENT %s', agent['name'])
        response = await client.responses.create(
            input=history_for_response,
            model=agent.get('model', 'gpt-5-mini'),
            tools=toolbox.get_tools(agent.get('tools', [])),
            **agent.get('kwargs', {}),
        )
        logger.debug('RESPONSE from %s in %.2f seconds', agent['name'], time.time() - start)

        usage.append((agent.get('model', response.model), response.usage))
        history.extend(response.output)

        outputs = [item for item in response.output if item.type == 'message']
        if outputs:
            return '\n'.join(
                chunk.text
                for item in outputs
                for chunk in item.content
            )

        tool_calls = {
            item.call_id: toolbox.run_tool(item.name, **json.loads(item.arguments))
            for item in response.output
            if item.type == 'function_call'
        }

        results = await asyncio.gather(*(asyncio.create_task(call) for call in tool_calls.values()))

        for call_id, result in zip(tool_calls.keys(), results):
            history.append({
                'type': 'function_call_output',
                'call_id': call_id,
                'output': str(result),
            })

        if any(
            item.type == 'function_call' and item.name == conclude.__name__
            for item in response.output
        ):
            return None


def as_tool(client, toolbox, agent, history=None, usage=None):
    async def function(input: str) -> str:
        return await run_agent(
            client,
            toolbox,
            agent,
            user_message=input,
            history=history,
            usage=usage,
        )

    function.__name__ = agent['name']
    function.__doc__ = agent.get('description', '')
    return function


def _normalize_tools(tools: Iterable[Callable] | dict[str, Callable] | None) -> dict[str, Callable]:
    if tools is None:
        return {}
    if isinstance(tools, dict):
        return tools
    return {fn.__name__: fn for fn in tools}


def _build_agent(
    *,
    name: str,
    description: str = '',
    model: str = 'gpt-5-nano',
    prompt: str = '',
    tools: list[str] | None = None,
    kwargs: dict[str, Any] | None = None,
    kwarks: dict[str, Any] | None = None,
) -> Agent:
    final_kwargs = kwargs if kwargs is not None else (kwarks or {})
    return {
        'name': name,
        'description': description,
        'model': model,
        'prompt': prompt,
        'tools': tools or [],
        'kwargs': final_kwargs,
    }


async def run_pluggable_agent(
    *,
    message: str,
    name: str = 'main',
    description: str = '',
    model: str = 'gpt-5-mini',
    prompt: str = '',
    tools: list[str] | None = None,
    kwargs: dict[str, Any] | None = None,
    kwarks: dict[str, Any] | None = None,
    yaml_path: str | Path | None = None,
    main_agent_name: str = 'main',
    tool_functions: Iterable[Callable] | dict[str, Callable] | None = None,
    client: AsyncOpenAI | None = None,
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

    for fn in _normalize_tools(tool_functions).values():
        toolbox.tool(fn)

    if yaml_path:
        raw = Path(yaml_path).read_text(encoding='utf-8')
        docs = [doc for doc in yaml.safe_load_all(raw) if doc]
        if not docs:
            raise ValueError('YAML file has no agent definitions.')

        agents: list[Agent] = docs
        for ag in agents:
            if ag.get('name') != main_agent_name:
                toolbox.tool(as_tool(local_client, toolbox, ag, usage=usage))

        try:
            main_agent = next(a for a in agents if a.get('name') == main_agent_name)
        except StopIteration as exc:
            raise ValueError(f"No main agent named '{main_agent_name}' found in YAML.") from exc
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


def _resolve_within_workspace(path: Path) -> Path | None:
    base_dir = Path.cwd().resolve()
    try:
        return path.resolve().relative_to(base_dir)
    except ValueError:
        return None


def run_terminal(file_text: str, file_name: str, file_path: str) -> str:
    """
    Write a document to disk.
    :param file_text: Text content to write.
    :param file_name: Name of the file (for example, notes.txt).
    :param file_path: Directory path where the file should be written.
    :return: JSON status describing the write result.
    """
    if Path(file_name).name != file_name:
        return json.dumps({
            'status': 'blocked',
            'written_files': [],
            'notes': ['file_name must not contain directory separators.'],
        })

    base_dir = Path.cwd().resolve()
    target_dir = Path(file_path).expanduser()
    if not target_dir.is_absolute():
        target_dir = (base_dir / target_dir).resolve()
    else:
        target_dir = target_dir.resolve()

    target_file = (target_dir / file_name).resolve()
    if _resolve_within_workspace(target_file) is None:
        return json.dumps({
            'status': 'blocked',
            'written_files': [],
            'notes': [f'Target path is outside workspace: {target_file}'],
        })

    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text(file_text, encoding='utf-8')
    relative_path = str(target_file.relative_to(base_dir))
    return json.dumps({
        'status': 'written',
        'written_files': [relative_path],
        'notes': [f'Wrote {relative_path}'],
    })


def write_files(files_json: str) -> str:
    """
    Write one or more files from a JSON payload.
    :param files_json: JSON array of {"path": ..., "content": ...} objects, or an object containing a "files" array.
    :return: JSON status describing written files.
    """
    base_dir = Path.cwd().resolve()

    try:
        payload = json.loads(files_json)
    except json.JSONDecodeError as exc:
        return json.dumps({'status': 'blocked', 'written_files': [], 'notes': [f'Invalid JSON: {exc}']})

    file_specs = payload.get('files') if isinstance(payload, dict) else payload
    if not isinstance(file_specs, list):
        return json.dumps({
            'status': 'blocked',
            'written_files': [],
            'notes': ["Payload must be a list or an object containing a 'files' list."],
        })

    written_files: list[str] = []
    notes: list[str] = []

    for entry in file_specs:
        if not isinstance(entry, dict):
            notes.append('Skipped a non-object file entry.')
            continue

        rel_path = entry.get('path')
        content = entry.get('content')
        if not isinstance(rel_path, str) or not isinstance(content, str):
            notes.append('Skipped an entry missing string path/content fields.')
            continue

        target_path = (base_dir / rel_path).resolve()
        if _resolve_within_workspace(target_path) is None:
            notes.append(f'Skipped path outside workspace: {rel_path}')
            continue

        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content, encoding='utf-8')
        written_files.append(rel_path)

    status = 'written' if written_files else 'blocked'
    if not notes:
        notes.append('Files written successfully.')

    return json.dumps({'status': status, 'written_files': written_files, 'notes': notes})


def python(code: str) -> str:
    """
    Execute Python code with the current interpreter and return stdout/stderr + exit code.
    :param code: Python code to execute.
    :return: Combined command output.
    """
    completed = subprocess.run(
        [sys.executable, '-c', code],
        capture_output=True,
        text=True,
    )
    output: list[str] = []
    if completed.stdout:
        output.append(completed.stdout.strip())
    if completed.stderr:
        output.append(completed.stderr.strip())
    output.append(f'exit_code={completed.returncode}')
    return '\n'.join(part for part in output if part)


def terminal_writer(file_text: str, file_name: str, file_path: str) -> str:
    """Alias tool for writing a document to disk."""
    return run_terminal(file_text, file_name, file_path)


async def run_parallel_tools(calls_json: str) -> str:
    """
    Run multiple tool calls concurrently.
    Input JSON format:
      [{"tool": "tool_name", "args": {"k": "v"}}, ...]
    Returns JSON with one result object per call.
    """
    toolbox = current_toolbox.get(None)
    if toolbox is None:
        return json.dumps({'error': 'No active toolbox in context.'})

    try:
        calls = json.loads(calls_json)
    except json.JSONDecodeError as exc:
        return json.dumps({'error': f'Invalid JSON: {exc}'})

    if not isinstance(calls, list):
        return json.dumps({'error': 'calls_json must decode to a list.'})

    async def _execute(call: dict[str, Any]) -> dict[str, Any]:
        tool_name = call.get('tool')
        args = call.get('args', {})
        if not isinstance(tool_name, str):
            return {'tool': tool_name, 'ok': False, 'error': "Missing or invalid 'tool' name."}
        if tool_name == 'run_parallel_tools':
            return {'tool': tool_name, 'ok': False, 'error': 'Nested run_parallel_tools is not allowed.'}
        if not isinstance(args, dict):
            return {'tool': tool_name, 'ok': False, 'error': "'args' must be an object."}
        try:
            result = await toolbox.run_tool(tool_name, **args)
            return {'tool': tool_name, 'ok': True, 'result': str(result)}
        except Exception as exc:
            return {'tool': tool_name, 'ok': False, 'error': str(exc)}

    results = await asyncio.gather(*(_execute(call) for call in calls))
    return json.dumps({'results': results})


def _load_yaml_docs(yaml_path: Path) -> list[dict[str, Any]]:
    return [doc for doc in yaml.safe_load_all(yaml_path.read_text(encoding='utf-8')) if doc]


def _yaml_uses_tool(docs: list[dict[str, Any]], tool_name: str) -> bool:
    return any(tool_name in (agent.get('tools', []) or []) for agent in docs)


def _yaml_has_agent_name(docs: list[dict[str, Any]], agent_name: str) -> bool:
    return any(agent.get('name') == agent_name for agent in docs)


class _AgentFilter(logging.Filter):
    """Injects the current agent name and only passes tool-call and agent lines."""

    def filter(self, record):
        agent = current_agent.get(None)
        record.agent = agent['name'] if agent else '-'
        msg = record.getMessage()
        return msg.startswith('AGENT ') or (msg.startswith('TOOL ') and ' -> ' not in msg)


def _configure_debug_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('[%(agent)s] %(message)s'))
    handler.addFilter(_AgentFilter())
    for name in ('tools', 'run_agent'):
        log = logging.getLogger(name)
        log.setLevel(logging.DEBUG)
        log.addHandler(handler)
        log.propagate = False


def _select_runtime_tools(docs: list[dict[str, Any]]) -> list[Callable]:
    runtime_tools: list[Callable] = [talk_to_user]
    if _yaml_uses_tool(docs, 'python'):
        runtime_tools.append(python)
    if _yaml_uses_tool(docs, 'run_terminal'):
        runtime_tools.append(run_terminal)
    if _yaml_uses_tool(docs, 'write_files'):
        runtime_tools.append(write_files)
    if _yaml_uses_tool(docs, 'run_parallel_tools'):
        runtime_tools.append(run_parallel_tools)
    if _yaml_uses_tool(docs, 'terminal_writer') and not _yaml_has_agent_name(docs, 'terminal_writer'):
        runtime_tools.append(terminal_writer)
    return runtime_tools


async def main(yaml_path: Path, message: str | None, debug: bool = False) -> None:
    if debug:
        _configure_debug_logging()
    usages: list[tuple[str, Any]] = []
    docs = _load_yaml_docs(yaml_path)

    try:
        response = await run_pluggable_agent(
            yaml_path=yaml_path,
            message=message or '',
            tool_functions=_select_runtime_tools(docs),
            usage=usages,
        )
        if response:
            print(response)
            print()
    finally:
        print_usage(usages)


def cli() -> None:
    parser = argparse.ArgumentParser(description='Run an agent from a YAML file.')
    parser.add_argument('yaml_path', type=Path, help='Path to the agent YAML file.')
    parser.add_argument('message', nargs='?', default=None, help='Initial message to the agent.')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging.')
    args = parser.parse_args()
    try:
        asyncio.run(main(args.yaml_path, args.message, args.debug))
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    cli()
