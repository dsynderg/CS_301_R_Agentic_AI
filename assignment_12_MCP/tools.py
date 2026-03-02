import inspect
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
