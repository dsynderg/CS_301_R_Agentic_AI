import inspect
import json
import os
from datetime import datetime, timedelta
from types import UnionType
from typing import Any, Callable, get_type_hints, Literal, get_origin, get_args, Union

import requests
from dotenv import load_dotenv
from openai.types.responses import FunctionToolParam

# Load environment variables
load_dotenv()

_tools: dict[str, Callable] = {}


def _is_optional(annotation) -> bool:
    origin = get_origin(annotation)
    args = get_args(annotation)
    return (origin is UnionType or origin is Union) and type(None) in args


def _get_strict_json_schema_type(annotation) -> dict:
    origin = get_origin(annotation)
    args = get_args(annotation)

    if _is_optional(annotation):
        non_none_args = [arg for arg in args if arg is not type(None)]
        if len(non_none_args) == 1:
            return _get_strict_json_schema_type(non_none_args[0])
        raise TypeError(f"Unsupported Union with multiple non-None values: {annotation}")

    type_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
    }

    if annotation in type_map:
        return {"type": type_map[annotation]}

    if origin in type_map:
        return {"type": type_map[origin]}

    if origin is Literal:
        values = args
        if all(isinstance(v, (str, int, bool)) for v in values):
            return {"type": "string" if all(isinstance(v, str) for v in values) else "number", "enum": list(values)}
        raise TypeError("Unsupported Literal values in annotation")

    raise TypeError(f"Unsupported parameter type: {annotation}")


def generate_function_schema(func: Callable[..., Any]) -> FunctionToolParam:
    sig = inspect.signature(func)
    type_hints = get_type_hints(func)

    params = {}
    required = []

    for name, param in sig.parameters.items():
        if name in {"self", "ctx"}:
            continue

        ann = type_hints.get(name, param.annotation)
        if ann is inspect._empty:
            raise TypeError(f"Missing type annotation for parameter: {name}")

        schema_entry = _get_strict_json_schema_type(ann)

        is_required = (
            param.default is inspect._empty
            and not _is_optional(ann)
        )
        if is_required:
            required.append(name)
        params[name] = schema_entry

    # Format for Chat Completions API
    return {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": func.__doc__ or "",
            "parameters": {
                "type": "object",
                "properties": params,
                "required": required,
                "additionalProperties": False
            }
        }
    }


class ToolBox:
    tools: list[FunctionToolParam]

    def __init__(self):
        self._funcs = {}
        self.tools = []

    def tool(self, func):
        self._funcs[func.__name__] = func
        self.tools.append(generate_function_schema(func))
        return func

    def get_tool_function(self, tool_name: str) -> Callable | None:
        return self._funcs.get(tool_name)

    def get_tools(self, tool_names: list[str]) -> list[FunctionToolParam]:
        if not tool_names:
            return []
        allowed = set(tool_names)
        return [
            tool for tool in self.tools
            if tool.get('function', {}).get('name') in allowed
        ]


# Canvas API Integration
def _get_canvas_headers() -> dict:
    """Get authorization headers for Canvas API"""
    token = os.getenv('CANVAS_API_TOKEN')
    if not token:
        raise ValueError("CANVAS_API_TOKEN not found in environment")
    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }


def _get_canvas_url() -> str:
    """Get Canvas API base URL"""
    url = os.getenv('CANVAS_API_URL')
    if not url:
        raise ValueError("CANVAS_API_URL not found in environment")
    return url.rstrip('/')


def _get_clickup_headers() -> dict:
    """Get authorization headers for ClickUp API"""
    token = os.getenv('CLICKUP_API_TOKEN')
    if not token:
        raise ValueError("CLICKUP_API_TOKEN not found in environment")
    return {
        'Authorization': token,
        'Content-Type': 'application/json'
    }


def _get_clickup_url() -> str:
    """Get ClickUp API base URL normalized to /api/v2"""
    raw_url = os.getenv('CLICKUP_API_URL', 'https://api.clickup.com/api/v2').strip()
    url = raw_url.rstrip('/')

    # Fix common config where app host is used instead of api host.
    if 'app.clickup.com' in url:
        url = url.replace('app.clickup.com', 'api.clickup.com')

    if url.endswith('/api'):
        return f"{url}/v2"
    if '/api/v2' in url:
        return url
    if '/api/' in url:
        return f"{url}/v2"
    return f"{url}/api/v2"


# Canvas API Tools
def get_assignments_for_next_days(days: int) -> str:
    """
    Fetch all assignments due in the next x days from Canvas
    
    Args:
        days: Number of days to look ahead (e.g. 7 for next week)
    
    Returns:
        A formatted string containing all upcoming assignments
    """
    try:
        api_url = _get_canvas_url()
        headers = _get_canvas_headers()
        
        # Get current time and end time
        now = datetime.now()
        end_date = now + timedelta(days=days)
        
        # Fetch all courses
        courses_url = f"{api_url}/courses?enrollment_state=active&per_page=100"
        courses_response = requests.get(courses_url, headers=headers, timeout=10)
        courses_response.raise_for_status()
        courses = courses_response.json()
        
        all_assignments = []
        
        # For each course, fetch assignments
        for course in courses:
            course_id = course['id']
            course_name = course.get('name', 'Unknown Course')
            
            # Fetch assignments for this course
            assignments_url = f"{api_url}/courses/{course_id}/assignments?per_page=100"
            assignments_response = requests.get(assignments_url, headers=headers, timeout=10)
            assignments_response.raise_for_status()
            assignments = assignments_response.json()
            
            # Filter assignments due within the time window
            for assignment in assignments:
                due_at = assignment.get('due_at')
                if due_at:
                    due_date = datetime.fromisoformat(due_at.replace('Z', '+00:00'))
                    due_date_local = due_date.replace(tzinfo=None)
                    
                    if now <= due_date_local <= end_date:
                        all_assignments.append({
                            'course': course_name,
                            'assignment': assignment.get('name', 'Unnamed Assignment'),
                            'due_date': due_date_local.strftime('%Y-%m-%d %H:%M'),
                            'url': assignment.get('html_url', 'N/A'),
                            'points_possible': assignment.get('points_possible', 'N/A')
                        })
        
        if not all_assignments:
            return f"No assignments due in the next {days} days."
        
        # Format the response
        result = f"Assignments due in the next {days} days:\n\n"
        for i, assignment in enumerate(all_assignments, 1):
            result += f"{i}. [{assignment['assignment']}]\n"
            result += f"   Course: {assignment['course']}\n"
            result += f"   Due: {assignment['due_date']}\n"
            result += f"   Points: {assignment['points_possible']}\n"
            result += f"   URL: {assignment['url']}\n\n"
        
        return result
        
    except requests.exceptions.RequestException as e:
        return f"Error fetching assignments from Canvas API: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


def get_courses() -> str:
    """
    Get list of all enrolled courses from Canvas
    
    Returns:
        A formatted string with course information
    """
    try:
        api_url = _get_canvas_url()
        headers = _get_canvas_headers()
        
        courses_url = f"{api_url}/courses?enrollment_state=active&per_page=100"
        response = requests.get(courses_url, headers=headers, timeout=10)
        response.raise_for_status()
        courses = response.json()
        
        if not courses:
            return "No enrolled courses found."
        
        result = "Your enrolled courses:\n\n"
        for i, course in enumerate(courses, 1):
            result += f"{i}. {course.get('name', 'Unknown')} (ID: {course['id']})\n"
        
        return result
        
    except requests.exceptions.RequestException as e:
        return f"Error fetching courses from Canvas API: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


def create_clickup_task(
        list_id: int,
        name: str,
        description: str | None = None,
        status: str | None = None,
        priority: int | None = None,
        due_date: int | None = None,
        due_date_time: bool | None = None,
        start_date: int | None = None,
        start_date_time: bool | None = None,
        time_estimate: int | None = None,
        notify_all: bool | None = None,
        parent: str | None = None,
        links_to: str | None = None,
        markdown_description: str | None = None,
        assignees_json: str | None = None,
        tags_json: str | None = None,
        custom_fields_json: str | None = None,
        points: int | None = None,
        check_required_custom_fields: bool | None = None
) -> str:
    """
    Create a task in a ClickUp list.

    Notes for JSON fields:
    - assignees_json: JSON array of user IDs, e.g. "[123456, 987654]"
    - tags_json: JSON array of tag strings, e.g. "[\"school\", \"urgent\"]"
    - custom_fields_json: JSON array for ClickUp custom fields payload
    """
    try:
        api_url = _get_clickup_url()
        headers = _get_clickup_headers()

        # Ensure list_id is an integer
        list_id = int(list_id)

        payload = {
            'name': name,
        }

        if description is not None and description != "":
            payload['description'] = str(description)
        if markdown_description is not None and markdown_description != "":
            payload['markdown_description'] = str(markdown_description)
        if status is not None and status != "":
            payload['status'] = str(status)
        if priority is not None:
            # ClickUp supports 1-4 or null. Map no-priority intents to null.
            if isinstance(priority, str) and priority.strip().lower() in {
                'none', 'null', 'no priority', 'clear', ''
            }:
                payload['priority'] = None
            else:
                try:
                    parsed_priority = int(priority)
                    if parsed_priority in {1, 2, 3, 4}:
                        payload['priority'] = parsed_priority
                except (TypeError, ValueError):
                    payload['priority'] = None
        else:
            payload['priority'] = None
        if due_date is not None:
            payload['due_date'] = int(due_date)
        if due_date_time is not None:
            # Ensure boolean type
            payload['due_date_time'] = bool(due_date_time) if not isinstance(due_date_time, str) else due_date_time.lower() == 'true'
        if start_date is not None:
            payload['start_date'] = int(start_date)
        if start_date_time is not None:
            payload['start_date_time'] = bool(start_date_time) if not isinstance(start_date_time, str) else start_date_time.lower() == 'true'
        if time_estimate is not None:
            payload['time_estimate'] = int(time_estimate)
        if notify_all is not None:
            payload['notify_all'] = bool(notify_all) if not isinstance(notify_all, str) else notify_all.lower() == 'true'
        if parent is not None and parent != "":
            payload['parent'] = str(parent)
        if links_to is not None and links_to != "":
            payload['links_to'] = str(links_to)
        if points is not None:
            payload['points'] = int(points)
        if check_required_custom_fields is not None:
            payload['check_required_custom_fields'] = bool(check_required_custom_fields) if not isinstance(check_required_custom_fields, str) else check_required_custom_fields.lower() == 'true'

        if assignees_json is not None and assignees_json != "":
            payload['assignees'] = json.loads(assignees_json)
        if tags_json is not None and tags_json != "":
            payload['tags'] = json.loads(tags_json)
        if custom_fields_json is not None and custom_fields_json != "":
            payload['custom_fields'] = json.loads(custom_fields_json)

        response = requests.post(
            f"{api_url}/list/{list_id}/task",
            headers=headers,
            json=payload,
            timeout=15
        )
        
        if response.status_code != 200:
            error_detail = ""
            try:
                error_detail = response.json()
            except:
                error_detail = response.text
            return (
                f"Error creating task in ClickUp API: {response.status_code}\n"
                f"Payload sent: {json.dumps(payload, indent=2)}\n"
                f"Response: {error_detail}"
            )
        
        data = response.json()

        return (
            "Task created successfully\n"
            f"Task ID: {data.get('id', 'N/A')}\n"
            f"Name: {data.get('name', 'N/A')}\n"
            f"Status: {data.get('status', {}).get('status', 'N/A')}\n"
            f"URL: {data.get('url', 'N/A')}"
        )
    except json.JSONDecodeError as e:
        return f"Invalid JSON in one of *_json parameters: {e}"
    except requests.exceptions.RequestException as e:
        return f"Error creating task in ClickUp API: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"
