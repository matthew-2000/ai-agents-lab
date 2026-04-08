"""CLI for 01 - Tool-Using Assistant."""

from __future__ import annotations

import argparse
import os
import sys

from agent import ToolUsingAgent, create_openai_client, load_environment, AgentRunResult, TraceLogger
from config import DEFAULT_MAX_STEPS, DEFAULT_MODEL
from tools import build_tools, load_prompt_example_map, load_prompt_examples


def run_self_check() -> None:
    tools = build_tools(enable_live_weather=False)
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
        print_json(result)
        print()


def print_json(payload: object) -> None:
    import json

    print(json.dumps(payload, indent=2, ensure_ascii=True))


def format_example_line(example: dict[str, str]) -> str:
    category = example.get("category", "general")
    summary = example.get("summary", "")
    return f"{example['id']:<24} [{category}] {summary}".rstrip()


def list_examples() -> None:
    examples = load_prompt_examples()

    print("Available prompt examples:\n")
    for example in examples:
        print(format_example_line(example))
    print("\nInside the interactive CLI, run one with:")
    print("/example <example-id>")


def get_example_prompt(example_id: str) -> str:
    example_map = load_prompt_example_map()
    example = example_map.get(example_id)
    if example is not None:
        return example["prompt"]

    available = ", ".join(example_map)
    raise RuntimeError(
        f"Unknown example '{example_id}'. Available examples: {available}"
    )


def print_run_result(result: AgentRunResult) -> None:
    print(f"Assistant> {result.final_text}")
    print(f"Model> {result.model}")
    print(
        "Usage> "
        f"input_tokens={result.usage.input_tokens}, "
        f"output_tokens={result.usage.output_tokens}, "
        f"total_tokens={result.usage.total_tokens}"
    )

    if result.trace_log_path is not None:
        print(f"\nTrace log: {result.trace_log_path}")


def run_agent_prompt(prompt: str, model: str, max_steps: int, no_log: bool) -> None:
    client = create_openai_client()
    logger = TraceLogger(enabled=not no_log)
    agent = ToolUsingAgent(
        client=client,
        model=model,
        tools=build_tools(enable_live_weather=True),
        max_steps=max_steps,
        logger=logger,
    )
    result = agent.run(prompt)
    print_run_result(result)


def print_repl_help() -> None:
    print("Interactive commands:")
    print("/help                Show this help message")
    print("/examples            List bundled prompt examples")
    print("/example <id>        Run one bundled example")
    print("/self-check          Run local deterministic tool checks")
    print("/exit                Quit the CLI")
    print()
    print("Any line that does not start with '/' is sent to the agent as a prompt.")


def handle_repl_command(command: str, model: str, max_steps: int, no_log: bool) -> bool:
    normalized = command.strip()

    if normalized in {"/exit", "/quit"}:
        return False
    if normalized == "/help":
        print_repl_help()
        return True
    if normalized == "/examples":
        list_examples()
        return True
    if normalized == "/self-check":
        run_self_check()
        return True
    if normalized.startswith("/example "):
        example_id = normalized.removeprefix("/example ").strip()
        if not example_id:
            print("Usage: /example <example-id>", file=sys.stderr)
            return True

        prompt = get_example_prompt(example_id)
        print(f"You> {prompt}")
        run_agent_prompt(prompt, model=model, max_steps=max_steps, no_log=no_log)
        return True

    print(f"Unknown command: {normalized}", file=sys.stderr)
    print("Type /help to see the available commands.", file=sys.stderr)
    return True


def interactive_loop(model: str, max_steps: int, no_log: bool) -> int:
    print("01 - Tool-Using Assistant")
    print("Enter a prompt to send it to the agent.")
    print("Type /help for commands, or /exit to quit.\n")

    while True:
        try:
            prompt = input("You> ").strip()
        except EOFError:
            print()
            return 0

        if not prompt:
            continue

        try:
            if prompt.startswith("/"):
                should_continue = handle_repl_command(
                    prompt,
                    model=model,
                    max_steps=max_steps,
                    no_log=no_log,
                )
                if not should_continue:
                    return 0
                print()
                continue

            run_agent_prompt(prompt, model=model, max_steps=max_steps, no_log=no_log)
        except RuntimeError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            print()
            continue
        except Exception as exc:  # noqa: BLE001
            print(f"Unexpected error: {exc}", file=sys.stderr)
            print()
            continue

        print()


def build_parser() -> argparse.ArgumentParser:
    default_model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
    default_max_steps = int(os.getenv("AGENT_MAX_STEPS", str(DEFAULT_MAX_STEPS)))

    parser = argparse.ArgumentParser(
        description="Run the minimal LLM-powered tool-using assistant.",
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
    load_environment()
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.self_check:
            run_self_check()
            raise SystemExit(0)

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

