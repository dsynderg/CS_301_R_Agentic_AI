import argparse
import asyncio
import base64
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

import yaml
from openai import AsyncOpenAI

from run_agent import run_agent, as_tool, Agent, conclude, current_agent
from tools import ToolBox
from usage import print_usage

LOG_FORMAT = '%(filename)-10.10s %(levelname)-4.4s %(asctime)s %(message)s'

toolbox = ToolBox()
toolbox.tool(conclude)


@toolbox.tool
def talk_to_user(message: str):
    """
    Use this function to communicate with the user.
    All communication to and from the user **MUST**
    be through this tool.
    :param message: The message to send to the user.
    :return: The user's response.
    """
    _agent = current_agent.get()
    name = _agent['name'] if _agent else 'Agent'
    print(f'{name}: {message}')
    return input('User: ')


@toolbox.tool
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
            "status": "blocked",
            "written_files": [],
            "notes": ["file_name must not contain directory separators."],
        })

    base_dir = Path.cwd().resolve()
    target_dir = Path(file_path).expanduser()
    if not target_dir.is_absolute():
        target_dir = (base_dir / target_dir).resolve()
    else:
        target_dir = target_dir.resolve()

    target_file = (target_dir / file_name).resolve()
    try:
        target_file.relative_to(base_dir)
    except ValueError:
        return json.dumps({
            "status": "blocked",
            "written_files": [],
            "notes": [f"Target path is outside workspace: {target_file}"],
        })

    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text(file_text, encoding='utf-8')
    relative_path = str(target_file.relative_to(base_dir))
    return json.dumps({
        "status": "written",
        "written_files": [relative_path],
        "notes": [f"Wrote {relative_path}"],
    })


@toolbox.tool
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
        return json.dumps({"status": "blocked", "written_files": [], "notes": [f"Invalid JSON: {exc}"]})

    file_specs = payload.get('files') if isinstance(payload, dict) else payload
    if not isinstance(file_specs, list):
        return json.dumps({"status": "blocked", "written_files": [], "notes": ["Payload must be a list or an object containing a 'files' list."]})

    written_files: list[str] = []
    notes: list[str] = []

    for entry in file_specs:
        if not isinstance(entry, dict):
            notes.append("Skipped a non-object file entry.")
            continue

        rel_path = entry.get('path')
        content = entry.get('content')
        if not isinstance(rel_path, str) or not isinstance(content, str):
            notes.append("Skipped an entry missing string path/content fields.")
            continue

        target_path = (base_dir / rel_path).resolve()
        try:
            target_path.relative_to(base_dir)
        except ValueError:
            notes.append(f"Skipped path outside workspace: {rel_path}")
            continue

        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content, encoding='utf-8')
        written_files.append(rel_path)

    status = 'written' if written_files else 'blocked'
    if not notes:
        notes.append('Files written successfully.')

    return json.dumps({"status": status, "written_files": written_files, "notes": notes})


@toolbox.tool
def write_files_with_terminal(files_json: str) -> str:
    """
    Write one or more files by invoking a terminal command.
    :param files_json: JSON array of {"path": ..., "content": ...} objects, or an object containing a "files" array.
    :return: JSON status describing written files.
    """
    base_dir = Path.cwd().resolve()

    try:
        payload = json.loads(files_json)
    except json.JSONDecodeError as exc:
        return json.dumps({"status": "blocked", "written_files": [], "notes": [f"Invalid JSON: {exc}"]})

    encoded_payload = base64.b64encode(json.dumps(payload).encode('utf-8')).decode('ascii')
    helper_script = """
import base64
import json
import sys
from pathlib import Path

base_dir = Path(sys.argv[1]).resolve()
payload = json.loads(base64.b64decode(sys.argv[2]).decode('utf-8'))
file_specs = payload.get('files') if isinstance(payload, dict) else payload

if not isinstance(file_specs, list):
    print(json.dumps({
        'status': 'blocked',
        'written_files': [],
        'notes': ["Payload must be a list or an object containing a 'files' list."]
    }))
    raise SystemExit(0)

written_files = []
notes = []

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
    try:
        target_path.relative_to(base_dir)
    except ValueError:
        notes.append(f'Skipped path outside workspace: {rel_path}')
        continue

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(content, encoding='utf-8')
    written_files.append(rel_path)

status = 'written' if written_files else 'blocked'
if not notes:
    notes.append('Files written successfully through terminal command execution.')

print(json.dumps({
    'status': status,
    'written_files': written_files,
    'notes': notes,
}))
""".strip()

    command = subprocess.list2cmdline([
        sys.executable,
        '-c',
        helper_script,
        str(base_dir),
        encoded_payload,
    ])
    completed = subprocess.run(command, shell=True, capture_output=True, text=True)
    terminal_chunks: list[str] = []
    if completed.stdout:
        terminal_chunks.append(completed.stdout.strip())
    if completed.stderr:
        terminal_chunks.append(completed.stderr.strip())
    terminal_chunks.append(f'exit_code={completed.returncode}')
    terminal_output = '\n'.join(chunk for chunk in terminal_chunks if chunk)
    output_lines = [line for line in terminal_output.splitlines() if line.strip()]

    if output_lines and output_lines[-1].startswith('exit_code='):
        exit_code_line = output_lines.pop()
        if exit_code_line != 'exit_code=0':
            message = '\n'.join(output_lines) if output_lines else exit_code_line
            return json.dumps({"status": "blocked", "written_files": [], "notes": [f"Terminal write command failed: {message}"]})

    if not output_lines:
        return json.dumps({"status": "blocked", "written_files": [], "notes": ["Terminal write command produced no JSON output."]})

    try:
        return json.dumps(json.loads(output_lines[-1]))
    except json.JSONDecodeError:
        return json.dumps({"status": "blocked", "written_files": [], "notes": [f"Terminal write command returned unexpected output: {' | '.join(output_lines)}"]})


async def main(agent_config: Path, message: str):
    client = AsyncOpenAI()
    usages = []

    def add_to_toolbox(_agent):
        toolbox.tool(as_tool(client, toolbox, _agent, usage=usages))

    agents: list[Agent] = list(yaml.safe_load_all(agent_config.read_text()))

    for agent in agents:
        if agent['name'] == 'main':
            continue
        add_to_toolbox(agent)

    main_agent = next(agent for agent in agents if agent['name'] == 'main')

    try:
        response = await run_agent(
            client, toolbox, main_agent,
            message, usage=usages
        )

        if response:
            print(response)
            print()
    finally:
        print_usage(usages)


def _configure_logging(debug: bool) -> None:
    local_level = logging.DEBUG if debug else logging.INFO
    use_dark_gray = (
            sys.stderr.isatty()
            and os.getenv('NO_COLOR') is None
            and os.getenv('TERM', '').lower() != 'dumb'
    )
    format_string = f'\x1b[90m{LOG_FORMAT}\x1b[0m' if use_dark_gray else LOG_FORMAT
    logging.basicConfig(
        level=logging.WARNING,
        format=format_string,
        datefmt='%H:%M:%S',
        force=True,
    )
    for logger_name in ('__main__', 'agents', 'run_agent', 'tools', 'usage'):
        logging.getLogger(logger_name).setLevel(local_level)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('agent_config', type=Path, nargs='?', default=Path('quotes.yaml'))
    parser.add_argument('message', nargs='?', default=None)
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()
    _configure_logging(args.debug)
    try:
        asyncio.run(main(args.agent_config, args.message))
    except KeyboardInterrupt:
        pass
