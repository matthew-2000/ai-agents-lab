"""Agent loop and OpenAI client integration."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from config import LOGS_DIR, SYSTEM_PROMPT
from tools import ToolDefinition


@dataclass
class UsageSummary:
    """Aggregated token usage across one agent run."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    def add(self, usage: Any) -> None:
        if usage is None:
            return

        if hasattr(usage, "model_dump"):
            usage_dict = usage.model_dump(mode="json")
        elif isinstance(usage, dict):
            usage_dict = usage
        else:
            return

        self.input_tokens += int(usage_dict.get("input_tokens", 0) or 0)
        self.output_tokens += int(usage_dict.get("output_tokens", 0) or 0)
        self.total_tokens += int(usage_dict.get("total_tokens", 0) or 0)


@dataclass
class AgentRunResult:
    """Normalized output of one complete agent run."""

    final_text: str
    model: str
    usage: UsageSummary
    trace_log_path: Path | None


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

    def run(self, user_input: str) -> AgentRunResult:
        input_items: list[Any] = [{"role": "user", "content": user_input}]
        usage_summary = UsageSummary()
        actual_model = self.model

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
            actual_model = getattr(response, "model", actual_model) or actual_model
            usage_summary.add(getattr(response, "usage", None))

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

                result = AgentRunResult(
                    final_text=final_text,
                    model=actual_model,
                    usage=usage_summary,
                    trace_log_path=self.logger.path,
                )
                self.logger.log(
                    "session_completed",
                    {
                        "step": step,
                        "final_output": final_text,
                        "usage": asdict(usage_summary),
                        "model": actual_model,
                    },
                )
                return result

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
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return

    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    load_dotenv(env_path)


def create_openai_client() -> Any:
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
            "The openai package is not installed. Run `python3 -m pip install -r "
            "01-tool-using-assistant/requirements.txt`."
        ) from exc

    return OpenAI(api_key=api_key)
