import asyncio
import os
import re
from datetime import datetime
from pathlib import Path

import yaml
from openai import AsyncOpenAI

from run_agent import run_agent
from tools import ToolBox, create_clickup_task, get_assignments_for_next_days, get_courses
from usage import print_usage


DEFAULT_CANVAS_REQUEST = (
    "Get assignments due in the next 7 days and format each as four lines: "
    "'<Class> <Assignment>:', 'Due: MM/DD/YYYY at HH:MM', 'URL: <link>', "
    "and 'Time estimant: <value>'. Use the actual Canvas due date and time."
)


def load_agent_config(agent_yaml_path: Path) -> dict:
    agent = yaml.safe_load(agent_yaml_path.read_text())
    if not isinstance(agent, dict):
        raise ValueError(f"{agent_yaml_path} must parse into a mapping/object")
    return agent


def build_canvas_toolbox() -> ToolBox:
    toolbox = ToolBox()
    toolbox.tool(get_assignments_for_next_days)
    toolbox.tool(get_courses)
    return toolbox


def build_clickup_toolbox() -> ToolBox:
    toolbox = ToolBox()
    toolbox.tool(create_clickup_task)
    return toolbox


def parse_assignment_blocks(canvas_output: str) -> list[dict]:
    """
    Parse Canvas output into individual assignment blocks.
    Splits on double newlines to separate assignments.
    
    Expected format per assignment:
    [Class name] [assignment name]:
    Due: MM/DD/YYYY at HH:MM
    URL: <url>
    Time estimant: X hours.
    """
    blocks = canvas_output.split('\n\n')
    assignments = []
    
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        
        lines = block.split('\n')
        if len(lines) < 4:
            continue
        
        # Parse assignment name (first line)
        assignment_name = lines[0].strip().rstrip(':')
        
        # Parse due date (second line, format: "Due: MM/DD/YYYY at HH:MM")
        due_date_line = lines[1].strip()
        due_date_match = re.search(
            r'(?:Due|Due date):\s*(\d{1,2})/(\d{1,2})/(\d{4})\s+at\s+(\d{1,2}):(\d{2})',
            due_date_line,
            flags=re.IGNORECASE,
        )
        due_date_iso_match = re.search(
            r'(?:Due|Due date):\s*(\d{4})-(\d{2})-(\d{2})\s+(\d{1,2}):(\d{2})',
            due_date_line,
            flags=re.IGNORECASE,
        )
        
        # Parse URL (third line, format: "URL: <url>")
        url_line = lines[2].strip()
        url = url_line.replace('URL:', '').strip() if 'URL:' in url_line else ''
        
        # Parse time estimate (fourth line, format: "Time estimant: X hours." or "Time estimant: X hour.")
        time_est_line = lines[3].strip() if len(lines) > 3 else ''
        time_hours_match = re.search(r'Time estimant:\s*(\d+(?:\.\d+)?)\s*hours?', time_est_line)
        time_minutes_match = re.search(r'Time estimant:\s*(\d+(?:\.\d+)?)\s*minutes?', time_est_line)
        
        if due_date_match:
            month, day, year, hour, minute = due_date_match.groups()
            # Convert to Unix timestamp in milliseconds
            due_datetime = datetime(int(year), int(month), int(day), int(hour), int(minute))
            due_date_ms = int(due_datetime.timestamp() * 1000)
        elif due_date_iso_match:
            year, month, day, hour, minute = due_date_iso_match.groups()
            due_datetime = datetime(int(year), int(month), int(day), int(hour), int(minute))
            due_date_ms = int(due_datetime.timestamp() * 1000)
        else:
            due_date_ms = None
        
        if time_hours_match:
            hours = float(time_hours_match.group(1))
            time_estimate_ms = int(hours * 3600 * 1000)
        elif time_minutes_match:
            minutes = float(time_minutes_match.group(1))
            time_estimate_ms = int(minutes * 60 * 1000)
        else:
            time_estimate_ms = None
        
        assignments.append({
            'name': assignment_name,
            'due_date': due_date_ms,
            'url': url,
            'time_estimate': time_estimate_ms,
        })
    
    return assignments


def get_clickup_list_id_from_env() -> int:
    """Read and validate ClickUp list ID from environment."""
    raw_value = os.getenv("CLICKUP_LIST_ID")
    if not raw_value:
        raise ValueError("CLICKUP_LIST_ID not found in environment. Add it to your .env file.")

    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError("CLICKUP_LIST_ID must be a valid integer.") from exc


async def sync_canvas_assignments_to_clickup(
    user_message: str,
    canvas_yaml_path: Path = Path("canvas.yaml"),
    clickup_yaml_path: Path = Path("clickup.yaml"),
    client=None,
    canvas_toolbox: ToolBox | None = None,
    canvas_agent: dict | None = None,
) -> dict:
    """
    Run Canvas agent to fetch assignments, parse output, then create ClickUp task for each.
    """
    if client is None:
        client = AsyncOpenAI()

    if canvas_toolbox is None:
        canvas_toolbox = build_canvas_toolbox()

    if canvas_agent is None:
        canvas_agent = load_agent_config(canvas_yaml_path)

    canvas_usage = []
    canvas_history = []

    # Step 1: Get assignments from Canvas
    canvas_result = await run_agent(
        client=client,
        toolbox=canvas_toolbox,
        agent=canvas_agent,
        user_message=user_message,
        history=canvas_history,
        usage=canvas_usage,
    )

    # Step 2: Parse Canvas output into structured assignment data
    assignments = parse_assignment_blocks(canvas_result)
    clickup_list_id = get_clickup_list_id_from_env()

    # Step 3: Create ClickUp task for each assignment
    created_tasks = []
    for assignment in assignments:
        try:
            result = create_clickup_task(
                list_id=clickup_list_id,
                name=assignment['name'],
                description=f"URL: {assignment['url']}" if assignment['url'] else None,
                due_date=assignment['due_date'],
                due_date_time=True,
                time_estimate=assignment['time_estimate'],
                status='to do',
            )
            created_tasks.append({
                'assignment_name': assignment['name'],
                'result': result,
            })
        except Exception as e:
            created_tasks.append({
                'assignment_name': assignment['name'],
                'error': str(e),
            })

    return {
        "canvas_output": canvas_result,
        "parsed_assignments": assignments,
        "created_tasks": created_tasks,
        "canvas_usage": canvas_usage,
    }


async def main(
    user_message: str,
    canvas_yaml_path: Path = Path("canvas.yaml"),
    clickup_yaml_path: Path = Path("clickup.yaml"),
):
    result = await sync_canvas_assignments_to_clickup(
        user_message=user_message,
        canvas_yaml_path=canvas_yaml_path,
        clickup_yaml_path=clickup_yaml_path,
    )

    print("Canvas Agent Output:")
    print(result["canvas_output"])
    print()
    print("Parsed Assignments:")
    for i, assignment in enumerate(result['parsed_assignments'], 1):
        print(f"{i}. {assignment['name']}")
        print(f"   Due: {assignment['due_date']} (ms)")
        print(f"   URL: {assignment['url']}")
        print(f"   Time estimate: {assignment['time_estimate']} (ms)")
    print()
    print("ClickUp Task Creation Results:")
    for task_result in result['created_tasks']:
        if 'error' in task_result:
            print(f"  [FAIL] {task_result['assignment_name']}: {task_result['error']}")
        else:
            print(f"  [OK] {task_result['assignment_name']}")
    print()

    canvas_model = load_agent_config(canvas_yaml_path).get("model", "gpt-5-mini")
    print_usage(canvas_model, result["canvas_usage"])


if __name__ == "__main__":
    import sys

    message = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CANVAS_REQUEST
    canvas_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("canvas.yaml")
    clickup_path = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("clickup.yaml")

    asyncio.run(main(message, canvas_path, clickup_path))