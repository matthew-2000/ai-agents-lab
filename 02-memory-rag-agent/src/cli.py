"""CLI for 02 - Memory + RAG Agent."""

from __future__ import annotations

import argparse
from dataclasses import asdict, is_dataclass
import json
import os
import sys

from agent import AgentTurnResult, MemoryRagAgent, TraceLogger, create_openai_client, load_environment
from config import DEFAULT_MAX_RECENT_TURNS, DEFAULT_MODEL
from memory import ShortTermMemoryStore
from retrieval import LocalKnowledgeBase, load_knowledge_base


def load_json(path: str) -> object:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_prompt_examples() -> list[dict[str, str]]:
    project_root = os.path.dirname(os.path.dirname(__file__))
    return load_json(os.path.join(project_root, "data", "prompt_examples.json"))


def load_prompt_example_map() -> dict[str, dict[str, str]]:
    examples = load_prompt_examples()
    return {example["id"]: example for example in examples}


def print_json(payload: object) -> None:
    if is_dataclass(payload):
        payload = asdict(payload)
    print(json.dumps(payload, indent=2, ensure_ascii=True))


class FakeResponse:
    """Minimal fake response object used by local self-checks."""

    def __init__(self, output_text: str) -> None:
        self.output_text = output_text
        self.model = "self-check-model"
        self.usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}


class FakeResponsesAPI:
    """Minimal fake Responses API to validate retrieval wiring locally."""

    def create(self, model: str, instructions: str, input: list[dict[str, str]]) -> FakeResponse:
        latest_user_input = input[-1]["content"] if input else ""
        if "snippet_id:" in instructions:
            return FakeResponse(
                "Retrieval augmented generation combines a model with external documents so answers "
                "can be grounded in retrieved evidence."
            )
        if "what is my name" in latest_user_input.lower():
            return FakeResponse("You told me your name is Matteo.")
        return FakeResponse("I stored that in short-term conversation memory.")


class FakeOpenAIClient:
    """Small fake client used for self-check coverage without an API key."""

    def __init__(self) -> None:
        self.responses = FakeResponsesAPI()


def run_self_check() -> None:
    memory = ShortTermMemoryStore(max_recent_turns=6)
    memory.remember_user_message("My name is Matteo. I live in Rome. I prefer concise answers.")
    memory.remember_assistant_message("Nice to meet you, Matteo.")
    memory.remember_user_message("I like weekend trips and my favorite cuisine is Japanese.")
    memory.remember_user_message("I moved to Milan.")

    kb = LocalKnowledgeBase(load_knowledge_base())
    retrieval_result = kb.search("memory and retrieval in ai agents", top_k=2)
    memory_decision = kb.decide_retrieval("What is my name?")
    knowledge_decision = kb.decide_retrieval("Explain retrieval augmented generation.")
    ambiguity_decision = kb.decide_retrieval("Which one is better?")

    fake_agent = MemoryRagAgent(
        client=FakeOpenAIClient(),
        model="self-check-model",
        memory_store=ShortTermMemoryStore(max_recent_turns=6),
        knowledge_base=kb,
        logger=TraceLogger(enabled=False),
    )
    fake_agent.run_turn("My name is Matteo.")
    fake_agent.run_turn("I live in Rome.")
    fake_agent.run_turn("I moved to Milan.")
    fake_result = fake_agent.run_turn("Explain retrieval augmented generation.")
    conflict_result = fake_agent.run_turn("Where do I live?")
    ambiguity_result = fake_agent.run_turn("Which one is better?")

    print("Running local self-checks...\n")
    print("[memory_snapshot]")
    print_json(memory.snapshot())
    print()
    print("[memory_block]")
    print(memory.build_memory_block())
    print()
    print("[retrieval_scaffold]")
    print_json(retrieval_result)
    print()
    print("[retrieval_decision_memory_query]")
    print_json(memory_decision)
    print()
    print("[retrieval_decision_knowledge_query]")
    print_json(knowledge_decision)
    print()
    print("[retrieval_decision_ambiguous_query]")
    print_json(ambiguity_decision)
    print()
    print("[agent_turn_with_retrieval]")
    print_json(
        {
            "final_text": fake_result.final_text,
            "retrieval_used": fake_result.retrieval_used,
            "retrieval_reason": fake_result.retrieval_reason,
            "retrieved_snippets": fake_result.retrieved_snippets,
            "warnings": fake_result.warnings,
            "response_origin": fake_result.response_origin,
        }
    )
    print()
    print("[agent_turn_with_memory_conflict]")
    print_json(
        {
            "final_text": conflict_result.final_text,
            "warnings": conflict_result.warnings,
            "response_origin": conflict_result.response_origin,
        }
    )
    print()
    print("[agent_turn_with_ambiguity]")
    print_json(
        {
            "final_text": ambiguity_result.final_text,
            "warnings": ambiguity_result.warnings,
            "response_origin": ambiguity_result.response_origin,
        }
    )


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
    raise RuntimeError(f"Unknown example '{example_id}'. Available examples: {available}")


def print_run_result(result: AgentTurnResult) -> None:
    print(f"Assistant> {result.final_text}")
    print(f"Model> {result.model}")
    print(f"Origin> {result.response_origin}")
    print(
        f"Retrieval> used={str(result.retrieval_used).lower()} | reason={result.retrieval_reason}"
    )
    if result.warnings:
        print("Warnings>")
        for warning in result.warnings:
            print(f"- {warning}")
    print(
        "Usage> "
        f"input_tokens={result.usage.input_tokens}, "
        f"output_tokens={result.usage.output_tokens}, "
        f"total_tokens={result.usage.total_tokens}"
    )

    if result.trace_log_path is not None:
        print(f"\nTrace log: {result.trace_log_path}")


def print_memory(memory_store: ShortTermMemoryStore) -> None:
    print("[memory]")
    print_json(memory_store.snapshot())


def print_repl_help() -> None:
    print("Interactive commands:")
    print("/help                Show this help message")
    print("/examples            List bundled prompt examples")
    print("/example <id>        Run one bundled example in the current session")
    print("/memory              Show the current memory snapshot")
    print("/retrieve <query>    Preview retrieval results without calling the model")
    print("/reset               Clear the current conversation memory")
    print("/self-check          Run local deterministic checks")
    print("/exit                Quit the CLI")
    print()
    print("Any line that does not start with '/' is sent to the agent as a prompt.")


def handle_repl_command(command: str, agent: MemoryRagAgent) -> bool:
    normalized = command.strip()

    if normalized in {"/exit", "/quit"}:
        return False
    if normalized == "/help":
        print_repl_help()
        return True
    if normalized == "/examples":
        list_examples()
        return True
    if normalized == "/memory":
        print_memory(agent.memory_store)
        return True
    if normalized.startswith("/retrieve "):
        query = normalized.removeprefix("/retrieve ").strip()
        if not query:
            print("Usage: /retrieve <query>", file=sys.stderr)
            return True

        decision = agent.knowledge_base.decide_retrieval(query, top_k=2)
        print_json(decision)
        return True
    if normalized == "/reset":
        agent.memory_store.reset()
        print("Memory cleared.")
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
        result = agent.run_turn(prompt)
        print_run_result(result)
        return True

    print(f"Unknown command: {normalized}", file=sys.stderr)
    print("Type /help to see the available commands.", file=sys.stderr)
    return True


def interactive_loop(model: str, max_recent_turns: int, no_log: bool) -> int:
    client = create_openai_client()
    knowledge_base = LocalKnowledgeBase(load_knowledge_base())
    memory_store = ShortTermMemoryStore(max_recent_turns=max_recent_turns)
    logger = TraceLogger(enabled=not no_log)
    agent = MemoryRagAgent(
        client=client,
        model=model,
        memory_store=memory_store,
        knowledge_base=knowledge_base,
        logger=logger,
    )

    print("02 - Memory + RAG Agent")
    print("Sprint 3: memory, retrieval, and safety-oriented diagnostics are active.")
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
                should_continue = handle_repl_command(prompt, agent)
                if not should_continue:
                    return 0
                print()
                continue

            result = agent.run_turn(prompt)
            print_run_result(result)
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
    default_max_recent_turns = int(
        os.getenv("AGENT_MAX_RECENT_TURNS", str(DEFAULT_MAX_RECENT_TURNS))
    )

    parser = argparse.ArgumentParser(
        description="Run the standalone memory-aware assistant.",
    )
    parser.add_argument(
        "--model",
        default=default_model,
        help=f"OpenAI model to use. Defaults to {default_model}.",
    )
    parser.add_argument(
        "--max-recent-turns",
        type=int,
        default=default_max_recent_turns,
        help=f"Recent turns to preserve in memory. Defaults to {default_max_recent_turns}.",
    )
    parser.add_argument(
        "--no-log",
        action="store_true",
        help="Disable JSONL trace logging under 02-memory-rag-agent/logs/.",
    )
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="Run local deterministic checks without calling the OpenAI API.",
    )
    parser.add_argument(
        "--prompt",
        action="append",
        dest="prompts",
        help="Run one prompt non-interactively. Repeat to keep the same session across turns.",
    )
    return parser


def run_prompt_sequence(model: str, max_recent_turns: int, no_log: bool, prompts: list[str]) -> int:
    client = create_openai_client()
    knowledge_base = LocalKnowledgeBase(load_knowledge_base())
    memory_store = ShortTermMemoryStore(max_recent_turns=max_recent_turns)
    logger = TraceLogger(enabled=not no_log)
    agent = MemoryRagAgent(
        client=client,
        model=model,
        memory_store=memory_store,
        knowledge_base=knowledge_base,
        logger=logger,
    )

    for prompt in prompts:
        print(f"You> {prompt}")
        result = agent.run_turn(prompt)
        print_run_result(result)
        print()

    return 0


def main() -> None:
    load_environment()
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.self_check:
            run_self_check()
            raise SystemExit(0)

        if args.prompts:
            raise SystemExit(
                run_prompt_sequence(
                    model=args.model,
                    max_recent_turns=args.max_recent_turns,
                    no_log=args.no_log,
                    prompts=args.prompts,
                )
            )

        raise SystemExit(
            interactive_loop(
                model=args.model,
                max_recent_turns=args.max_recent_turns,
                no_log=args.no_log,
            )
        )
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
