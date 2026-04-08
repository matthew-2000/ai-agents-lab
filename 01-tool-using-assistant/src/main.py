"""Entry point for 01 - Tool-Using Assistant."""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"

DEFAULT_MODEL = "gpt-5-mini"
DEFAULT_MAX_STEPS = 6

SYSTEM_PROMPT = """
You are a minimal LLM-powered tool-using assistant.

Follow these rules:
- Use the calculator tool for arithmetic instead of mental math.
- Use the weather tool for weather questions.
- Use the knowledge base tool when the answer depends on the local demo knowledge base.
- Never invent a tool result.
- If a tool says data is mocked, make that clear in your answer.
- Keep answers concise but useful.
""".strip()


@dataclass(frozen=True)
class ToolDefinition:
    """Defines one callable tool exposed to the model."""

    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., dict[str, Any]]

    def to_response_tool(self) -> dict[str, Any]:
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


class TraceLogger:
    """Writes lightweight JSONL traces for each run."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self.path: Path | None = None

        if not enabled:
            return

        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.path = LOGS_DIR / f"session-{timestamp}.jsonl"

    def log(self, event: str, payload: dict[str, Any]) -> None:
        if not self.enabled or self.path is None:
            return

        entry = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "event": event,
            "payload": payload,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=True, default=str) + "\n")


def load_json_file(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_weather_snapshots() -> list[dict[str, Any]]:
    return load_json_file(DATA_DIR / "weather_snapshots.json")


def load_knowledge_base() -> list[dict[str, Any]]:
    return load_json_file(DATA_DIR / "knowledge_base.json")


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def tokenize(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.lower()))


def format_number(value: float | int) -> float | int:
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return round(value, 8) if isinstance(value, float) else value


def safe_calculate(expression: str) -> dict[str, Any]:
    if len(expression) > 120:
        raise ValueError("Expression is too long for the demo calculator.")

    tree = ast.parse(expression, mode="eval")

    def eval_node(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return eval_node(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            operand = eval_node(node.operand)
            return operand if isinstance(node.op, ast.UAdd) else -operand
        if isinstance(node, ast.BinOp):
            left = eval_node(node.left)
            right = eval_node(node.right)

            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right
            if isinstance(node.op, ast.FloorDiv):
                return left // right
            if isinstance(node.op, ast.Mod):
                return left % right
            if isinstance(node.op, ast.Pow):
                if abs(right) > 10 or abs(left) > 1_000_000:
                    raise ValueError("Exponentiation request is outside safe demo limits.")
                return left**right

        raise ValueError("Unsupported calculator expression.")

    result = eval_node(tree)
    return {
        "expression": expression,
        "result": format_number(result),
    }


def build_calculator_tool() -> ToolDefinition:
    def handler(expression: str) -> dict[str, Any]:
        return {
            "status": "ok",
            "tool": "calculator",
            **safe_calculate(expression),
        }

    return ToolDefinition(
        name="calculator",
        description="Evaluate a basic arithmetic expression exactly.",
        parameters={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Arithmetic expression such as 17 * 24 or (5 + 3) / 2.",
                }
            },
            "required": ["expression"],
        },
        handler=handler,
    )


def build_weather_tool(weather_snapshots: list[dict[str, Any]]) -> ToolDefinition:
    alias_map: dict[str, dict[str, Any]] = {}
    for snapshot in weather_snapshots:
        for alias in snapshot["aliases"]:
            alias_map[normalize_text(alias)] = snapshot

    def handler(location: str) -> dict[str, Any]:
        normalized = normalize_text(location)

        selected = alias_map.get(normalized)
        if selected is None:
            for alias, snapshot in alias_map.items():
                if alias in normalized or normalized in alias:
                    selected = snapshot
                    break

        if selected is None:
            return {
                "status": "not_found",
                "tool": "get_weather",
                "requested_location": location,
                "available_locations": sorted(
                    {snapshot["location"] for snapshot in weather_snapshots}
                ),
                "note": "This demo weather tool only supports a small mocked local dataset.",
            }

        return {
            "status": "ok",
            "tool": "get_weather",
            "location": selected["location"],
            "date": selected["date"],
            "condition": selected["condition"],
            "temperature_c": selected["temperature_c"],
            "feels_like_c": selected["feels_like_c"],
            "humidity_pct": selected["humidity_pct"],
            "wind_kph": selected["wind_kph"],
            "note": "Weather data comes from a mocked local snapshot for demo purposes, not a live forecast.",
        }

    return ToolDefinition(
        name="get_weather",
        description="Look up weather information from a small local demo dataset.",
        parameters={
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City or city and country, such as Rome or New York.",
                }
            },
            "required": ["location"],
        },
        handler=handler,
    )


def build_knowledge_base_tool(knowledge_base: list[dict[str, Any]]) -> ToolDefinition:
    def handler(query: str) -> dict[str, Any]:
        query_tokens = tokenize(query)
        scored_entries: list[tuple[int, dict[str, Any]]] = []

        for entry in knowledge_base:
            keywords = set(entry.get("keywords", []))
            score = len(query_tokens & keywords)
            if score:
                scored_entries.append((score, entry))

        scored_entries.sort(
            key=lambda item: (-item[0], item[1]["title"].lower()),
        )

        matches = [
            {
                "title": entry["title"],
                "content": entry["content"],
                "score": score,
            }
            for score, entry in scored_entries[:3]
        ]

        status = "ok" if matches else "not_found"
        return {
            "status": status,
            "tool": "search_knowledge_base",
            "query": query,
            "matches": matches,
            "note": "This tool searches only the local demo knowledge base bundled with the project.",
        }

    return ToolDefinition(
        name="search_knowledge_base",
        description="Search a small local knowledge base for demo facts and project context.",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What to search for in the local knowledge base.",
                }
            },
            "required": ["query"],
        },
        handler=handler,
    )


def build_tools() -> list[ToolDefinition]:
    weather_snapshots = load_weather_snapshots()
    knowledge_base = load_knowledge_base()
    return [
        build_calculator_tool(),
        build_weather_tool(weather_snapshots),
        build_knowledge_base_tool(knowledge_base),
    ]


class ToolUsingAgent:
    """Runs a simple OpenAI Responses API tool loop."""

    def __init__(
        self,
        client: Any,
        model: str,
        tools: list[ToolDefinition],
        max_steps: int,
        logger: TraceLogger,
    ) -> None:
        self.client = client
        self.model = model
        self.tools = tools
        self.max_steps = max_steps
        self.logger = logger
        self.tools_by_name = {tool.name: tool for tool in tools}

    def run(self, user_input: str) -> str:
        input_items: list[Any] = [{"role": "user", "content": user_input}]
        self.logger.log(
            "session_started",
            {"model": self.model, "user_input": user_input, "max_steps": self.max_steps},
        )

        for step in range(1, self.max_steps + 1):
            response = self.client.responses.create(
                model=self.model,
                instructions=SYSTEM_PROMPT,
                tools=[tool.to_response_tool() for tool in self.tools],
                input=input_items,
            )
            self.logger.log(
                "model_response",
                {
                    "step": step,
                    "response": response.model_dump(mode="json"),
                },
            )

            function_calls = [
                item for item in response.output if getattr(item, "type", None) == "function_call"
            ]

            if not function_calls:
                final_text = (response.output_text or "").strip()
                if not final_text:
                    raise RuntimeError("The model returned no tool calls and no final text.")

                self.logger.log(
                    "session_completed",
                    {"step": step, "final_output": final_text},
                )
                return final_text

            input_items.extend(response.output)

            for tool_call in function_calls:
                tool_result = self.execute_tool_call(tool_call.name, tool_call.arguments)
                output_item = {
                    "type": "function_call_output",
                    "call_id": tool_call.call_id,
                    "output": json.dumps(tool_result, ensure_ascii=True),
                }
                input_items.append(output_item)
                self.logger.log(
                    "tool_result",
                    {
                        "step": step,
                        "tool_name": tool_call.name,
                        "tool_arguments": tool_call.arguments,
                        "tool_output": tool_result,
                    },
                )

        raise RuntimeError(
            f"The agent reached the max step limit ({self.max_steps}) before finishing."
        )

    def execute_tool_call(self, name: str, arguments_json: str) -> dict[str, Any]:
        tool = self.tools_by_name.get(name)
        if tool is None:
            return {
                "status": "error",
                "tool": name,
                "error": f"Tool '{name}' is not registered.",
            }

        try:
            arguments = json.loads(arguments_json)
        except json.JSONDecodeError as exc:
            return {
                "status": "error",
                "tool": name,
                "error": f"Invalid JSON arguments: {exc}",
            }

        try:
            return tool.handler(**arguments)
        except Exception as exc:  # noqa: BLE001
            return {
                "status": "error",
                "tool": name,
                "error": str(exc),
            }


def load_environment() -> None:
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return

    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    load_dotenv(env_path)


def create_openai_client() -> Any:
    load_environment()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Copy 01-tool-using-assistant/.env.example to "
            "01-tool-using-assistant/.env and add your key."
        )

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "The openai package is not installed. Run `pip install -r 01-tool-using-assistant/requirements.txt`."
        ) from exc

    return OpenAI(api_key=api_key)


def run_self_check() -> int:
    tools = build_tools()
    tool_map = {tool.name: tool for tool in tools}

    samples = [
        ("calculator", {"expression": "17 * 24"}),
        ("get_weather", {"location": "Rome"}),
        ("search_knowledge_base", {"query": "What is ai-agents-lab?"}),
    ]

    print("Running local tool self-checks...\n")
    for tool_name, arguments in samples:
        result = tool_map[tool_name].handler(**arguments)
        print(f"[{tool_name}]")
        print(json.dumps(result, indent=2, ensure_ascii=True))
        print()

    return 0


def run_single_prompt(prompt: str, model: str, max_steps: int, no_log: bool) -> int:
    client = create_openai_client()
    logger = TraceLogger(enabled=not no_log)
    agent = ToolUsingAgent(
        client=client,
        model=model,
        tools=build_tools(),
        max_steps=max_steps,
        logger=logger,
    )

    answer = agent.run(prompt)
    print(answer)

    if logger.path is not None:
        print(f"\nTrace log: {logger.path}")

    return 0


def interactive_loop(model: str, max_steps: int, no_log: bool) -> int:
    print("01 - Tool-Using Assistant")
    print("Type a prompt, or type 'exit' to quit.\n")

    while True:
        try:
            prompt = input("You> ").strip()
        except EOFError:
            print()
            return 0

        if not prompt:
            continue
        if prompt.lower() in {"exit", "quit"}:
            return 0

        try:
            run_single_prompt(prompt, model=model, max_steps=max_steps, no_log=no_log)
        except RuntimeError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        except Exception as exc:  # noqa: BLE001
            print(f"Unexpected error: {exc}", file=sys.stderr)
            return 1

        print()


def build_parser() -> argparse.ArgumentParser:
    load_environment()
    default_model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
    default_max_steps = int(os.getenv("AGENT_MAX_STEPS", str(DEFAULT_MAX_STEPS)))

    parser = argparse.ArgumentParser(
        description="Run the minimal LLM-powered tool-using assistant.",
    )
    parser.add_argument(
        "--prompt",
        help="Run the agent once for a single user prompt.",
    )
    parser.add_argument(
        "--model",
        default=default_model,
        help=f"OpenAI model to use. Defaults to {default_model}.",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=default_max_steps,
        help=f"Maximum tool loop iterations. Defaults to {default_max_steps}.",
    )
    parser.add_argument(
        "--no-log",
        action="store_true",
        help="Disable JSONL trace logging under 01-tool-using-assistant/logs/.",
    )
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="Run local tool checks without calling the OpenAI API.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.self_check:
            raise SystemExit(run_self_check())

        if args.prompt:
            raise SystemExit(
                run_single_prompt(
                    prompt=args.prompt,
                    model=args.model,
                    max_steps=args.max_steps,
                    no_log=args.no_log,
                )
            )

        raise SystemExit(
            interactive_loop(
                model=args.model,
                max_steps=args.max_steps,
                no_log=args.no_log,
            )
        )
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
