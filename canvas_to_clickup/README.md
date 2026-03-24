# Canvas to ClickUp Workflow

This script pulls upcoming Canvas assignments and creates matching tasks in ClickUp.

## What You Need

- Python 3.10+
- A valid OpenAI API key
- Canvas API access (URL + token)
- ClickUp API access (URL + token)

## Dependencies

Install required packages:

```bash
pip install openai pyyaml requests python-dotenv
```

Used by this project:

- `openai`
- `pyyaml`
- `requests`
- `python-dotenv`

## Environment Variables

Create/update `.env` in this folder with:

```env
OPENAI_API_KEY=your_openai_key
CANVAS_API_URL=https://your-school.instructure.com/api/v1
CANVAS_API_TOKEN=your_canvas_token
CLICKUP_API_URL=https://api.clickup.com/api/v2
CLICKUP_API_TOKEN=your_clickup_token
CLICKUP_LIST_ID=your_clickup_list_id
```

## Config Files

- `canvas.yaml`: Canvas agent model, tools, and prompt format.
- `clickup.yaml`: ClickUp agent settings.

## Run Command

From this folder:

```bash
python canvas_to_clickup_workflow.py "I want the assignments for the next seven days"
```

Or run with no prompt to use the built-in default request (next 7 days):

```bash
python canvas_to_clickup_workflow.py
```

Optional full form:

```bash
python canvas_to_clickup_workflow.py "<request>" canvas.yaml clickup.yaml
```

## What It Does

1. Calls Canvas tools to fetch upcoming assignments.
2. Parses each assignment (name, due date, URL, estimate).
3. Creates a task in the ClickUp list set by `CLICKUP_LIST_ID`.
4. Prints output, parsed assignments, task creation results, and token usage.
