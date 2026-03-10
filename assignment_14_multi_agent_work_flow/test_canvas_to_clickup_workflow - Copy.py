import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from canvas_to_clickup_workflow import (
    parse_assignment_blocks,
    sync_canvas_assignments_to_clickup,
)
from tools import ToolBox


def _usage_obj():
    return SimpleNamespace(
        input_tokens=1,
        output_tokens=1,
        input_tokens_details=SimpleNamespace(cached_tokens=0),
        output_tokens_details=SimpleNamespace(reasoning_tokens=0),
    )


class _QueuedResponsesClient:
    def __init__(self, outputs):
        self._outputs = outputs
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if not self._outputs:
            raise AssertionError("No fake response remaining for create()")
        return self._outputs.pop(0)


class _FakeClient:
    def __init__(self, outputs):
        self.responses = _QueuedResponsesClient(outputs)


class ParseAssignmentBlocksTests(unittest.TestCase):
    def test_parse_single_assignment(self):
        canvas_output = (
            "CS 301R Homework 3:\n"
            "Due: 03/15/2026 at 23:59\n"
            "URL: https://canvas.example/cs301r/hw3\n"
            "Time estimant: 2 hours."
        )
        
        assignments = parse_assignment_blocks(canvas_output)
        
        self.assertEqual(1, len(assignments))
        self.assertEqual("CS 301R Homework 3", assignments[0]["name"])
        self.assertEqual("https://canvas.example/cs301r/hw3", assignments[0]["url"])
        self.assertEqual(7200000, assignments[0]["time_estimate"])
        self.assertIsNotNone(assignments[0]["due_date"])

    def test_parse_multiple_assignments_separated_by_double_newline(self):
        canvas_output = (
            "CS 301R Homework 3:\n"
            "Due: 03/15/2026 at 23:59\n"
            "URL: https://canvas.example/cs301r/hw3\n"
            "Time estimant: 2 hours.\n"
            "\n"
            "MATH 290 HW 8:\n"
            "Due: 03/16/2026 at 23:59\n"
            "URL: https://canvas.example/math290/hw8\n"
            "Time estimant: 2 hours."
        )
        
        assignments = parse_assignment_blocks(canvas_output)
        
        self.assertEqual(2, len(assignments))
        self.assertEqual("CS 301R Homework 3", assignments[0]["name"])
        self.assertEqual("MATH 290 HW 8", assignments[1]["name"])

    def test_parse_handles_varying_time_formats(self):
        """Test that time estimants with 'hour' (singular) are handled."""
        canvas_output = (
            "Quick Assignment:\n"
            "Due: 03/20/2026 at 23:59\n"
            "URL: https://canvas.example/quick\n"
            "Time estimant: 0.5 hours."
        )
        
        assignments = parse_assignment_blocks(canvas_output)
        
        self.assertEqual(1, len(assignments))
        self.assertEqual(1800000, assignments[0]["time_estimate"])

    def test_parse_handles_minutes_in_time_estimate(self):
        """Test that time estimates in minutes are correctly converted to ms."""
        canvas_output = (
            "Section Assignment:\n"
            "Due: 03/20/2026 at 23:59\n"
            "URL: https://canvas.example/section\n"
            "Time estimant: 30 minutes."
        )
        
        assignments = parse_assignment_blocks(canvas_output)
        
        self.assertEqual(1, len(assignments))
        # 30 minutes = 30 * 60 * 1000 = 1800000 ms
        self.assertEqual(1800000, assignments[0]["time_estimate"])


class CanvasToClickUpWorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def test_creates_clickup_task_for_each_parsed_assignment(self):
        """Test that the workflow parses Canvas output and creates ClickUp tasks."""
        canvas_message = SimpleNamespace(
            type="message",
            content=[SimpleNamespace(text=(
                "CS 301R Homework 3:\n"
                "Due: 03/15/2026 at 23:59\n"
                "URL: https://canvas.example/cs301r/hw3\n"
                "Time estimant: 2 hours.\n"
                "\n"
                "MATH 290 HW 8:\n"
                "Due: 03/16/2026 at 23:59\n"
                "URL: https://canvas.example/math290/hw8\n"
                "Time estimant: 2 hours."
            ))],
        )

        fake_client = _FakeClient([
            SimpleNamespace(usage=_usage_obj(), output=[canvas_message]),
        ])

        created_tasks = []

        def create_clickup_task(
            list_id: int,
            name: str,
            description: str | None = None,
            due_date: int | None = None,
            due_date_time: bool | None = None,
            time_estimate: int | None = None,
            status: str | None = None,
        ) -> str:
            task = {
                "list_id": list_id,
                "name": name,
                "description": description,
                "due_date": due_date,
                "due_date_time": due_date_time,
                "time_estimate": time_estimate,
                "status": status,
            }
            created_tasks.append(task)
            return f"Task created successfully\nName: {name}"

        canvas_toolbox = ToolBox()
        canvas_toolbox.tool(create_clickup_task)

        canvas_agent = {
            "model": "gpt-5-nano",
            "prompt": "Canvas bot",
            "tools": [],
            "kwargs": {},
        }

        with patch('canvas_to_clickup_workflow.create_clickup_task', side_effect=create_clickup_task):
            result = await sync_canvas_assignments_to_clickup(
                user_message="Get assignments",
                client=fake_client,
                canvas_toolbox=canvas_toolbox,
                canvas_agent=canvas_agent,
            )

        self.assertEqual(2, len(result["created_tasks"]), "Should create one ClickUp task per Canvas assignment")
        self.assertEqual("CS 301R Homework 3", result["created_tasks"][0]["assignment_name"])
        self.assertEqual("MATH 290 HW 8", result["created_tasks"][1]["assignment_name"])


if __name__ == "__main__":
    unittest.main()
