import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from run_agent import run_agent
from run_agent_practice import load_canvas_lookup_agent
from tools import ToolBox, get_assignments_for_next_days, get_courses


class _FakeResponsesClient:
    def __init__(self, response):
        self._response = response
        self.last_create_kwargs = None

    async def create(self, **kwargs):
        self.last_create_kwargs = kwargs
        return self._response


class _FakeClient:
    def __init__(self, response):
        self.responses = _FakeResponsesClient(response)


class CanvasLookupBotTests(unittest.IsolatedAsyncioTestCase):
    def test_load_canvas_lookup_agent_includes_yaml_reference(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            canvas_path = Path(temp_dir) / "canvas.yaml"
            yaml_text = (
                "model: gpt-5-nano\n"
                "tools: ['get_courses']\n"
                "prompt: |\n"
                "  test prompt\n"
            )
            canvas_path.write_text(yaml_text)

            agent = load_canvas_lookup_agent(canvas_path)

            self.assertIn("Reference configuration (canvas.yaml):", agent["prompt"])
            self.assertIn("```yaml", agent["prompt"])
            self.assertIn(yaml_text.strip(), agent["prompt"])

    async def test_run_agent_uses_reference_agent_and_tools(self):
        fake_message = SimpleNamespace(
            type="message",
            content=[SimpleNamespace(text="Canvas lookup result")],
        )
        fake_response = SimpleNamespace(
            usage=SimpleNamespace(
                input_tokens=1,
                output_tokens=1,
                input_tokens_details=SimpleNamespace(cached_tokens=0),
                output_tokens_details=SimpleNamespace(reasoning_tokens=0),
            ),
            output=[fake_message],
        )

        client = _FakeClient(fake_response)

        toolbox = ToolBox()
        toolbox.tool(get_assignments_for_next_days)
        toolbox.tool(get_courses)

        agent = {
            "model": "gpt-5-nano",
            "prompt": "Bot prompt",
            "tools": ["get_courses"],
            "kwargs": {"temperature": 0.0},
        }

        usage = []
        history = []

        result = await run_agent(
            client=client,
            toolbox=toolbox,
            agent=agent,
            user_message="What classes am I in?",
            history=history,
            usage=usage,
        )

        self.assertEqual("Canvas lookup result", result)
        self.assertEqual(1, len(usage))
        self.assertEqual("gpt-5-nano", client.responses.last_create_kwargs["model"])
        self.assertEqual(0.0, client.responses.last_create_kwargs["temperature"])

        tools_sent = client.responses.last_create_kwargs["tools"]
        self.assertEqual(1, len(tools_sent))
        self.assertEqual("get_courses", tools_sent[0]["name"])


if __name__ == "__main__":
    unittest.main()
