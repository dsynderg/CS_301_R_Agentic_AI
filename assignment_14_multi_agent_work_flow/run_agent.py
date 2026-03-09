import json
from typing import TypedDict


class Agent(TypedDict):
    model: str
    prompt: str
    tools: list[str]
    kwargs: dict


def _normalize_tools_for_responses(tools: list[dict] | None) -> list[dict]:
    if not tools:
        return []

    normalized = []
    for tool in tools:
        # Convert Chat Completions-style function tools to Responses API style.
        if (
            isinstance(tool, dict)
            and tool.get('type') == 'function'
            and isinstance(tool.get('function'), dict)
        ):
            fn = tool['function']
            normalized.append({
                'type': 'function',
                'name': fn.get('name'),
                'description': fn.get('description', ''),
                'parameters': fn.get('parameters', {'type': 'object', 'properties': {}})
            })
        else:
            normalized.append(tool)

    return normalized


async def run_agent(
        client,
        toolbox,
        agent: Agent,
        user_message: str = None,
        history=None,
        usage=None
) -> str:
    if history is None:
        history = []
    if usage is None:
        usage = []

    if prompt := agent.get('prompt'):
        history.append({'role': 'system', 'content': prompt})

    if user_message:
        history.append({'role': 'user', 'content': user_message})

    while True:
        response = await client.responses.create(
            input=history,
            model=agent.get('model', 'gpt-5-mini'),
            tools=_normalize_tools_for_responses(toolbox.get_tools(agent.get('tools', []))),
            **agent.get('kwargs', {})
        )

        usage.append(response.usage)
        history.extend(
            response.output
        )

        for item in response.output:
            if item.type == 'function_call':
                print(f'{item.name}({item.arguments})')

                func = toolbox.get_tool_function(item.name)
                args = json.loads(item.arguments)
                result = func(**args)
                history.append({
                    'type': 'function_call_output',
                    'call_id': item.call_id,
                    'output': str(result)
                })

            elif item.type == 'message':
                return '\n'.join(chunk.text for chunk in item.content)
