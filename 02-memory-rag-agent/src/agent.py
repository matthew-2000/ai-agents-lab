"""Agent runtime for 02 - Memory + RAG Agent."""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from citations import extract_chunk_citations, format_sources_appendix
from config import LOGS_DIR, build_system_prompt
from documents import RetrievedSnippet
from memory import MemoryConflict, ShortTermMemoryStore
from retrieval import LocalKnowledgeBase, build_retrieval_block


@dataclass
class UsageSummary:
    """Aggregated token usage for one turn."""

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
class AgentTurnResult:
    """Normalized result of one user turn."""

    final_text: str
    model: str
    usage: UsageSummary
    trace_log_path: Path | None
    memory_block: str
    retrieval_used: bool
    retrieval_reason: str
    retrieved_snippets: list[dict[str, Any]]
    warnings: list[str]
    response_origin: str
    cited_chunk_ids: list[str]
    citation_validation_passed: bool


def build_diagnostics_block(warnings: list[str], relevant_conflicts: list[MemoryConflict]) -> str:
    """Render a small diagnostics section for the prompt."""

    lines: list[str] = []

    if warnings:
        lines.append("Warnings:")
        for warning in warnings:
            lines.append(f"- {warning}")

    if relevant_conflicts:
        lines.append("Relevant memory updates:")
        for conflict in relevant_conflicts:
            lines.append(
                f"- {conflict.label}: latest '{conflict.new_value}', earlier '{conflict.previous_value}'"
            )

    if not lines:
        return "No additional diagnostics."

    return "\n".join(lines)


class TraceLogger:
    """Writes lightweight JSONL traces for each session."""

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


class MemoryRagAgent:
    """Runs a single-turn response while preserving short-term memory across the session."""

    def __init__(
        self,
        client: Any,
        model: str,
        memory_store: ShortTermMemoryStore,
        knowledge_base: LocalKnowledgeBase,
        logger: TraceLogger,
    ) -> None:
        self.client = client
        self.model = model
        self.memory_store = memory_store
        self.knowledge_base = knowledge_base
        self.logger = logger

    def _build_safe_fallback_response(
        self,
        user_input: str,
        retrieval_reason: str,
        query_type: str,
        relevant_conflicts: list[MemoryConflict],
        needs_clarification: bool,
    ) -> str | None:
        normalized = user_input.lower()

        if relevant_conflicts and re.search(r"\bwhat\b|\bwhere\b|\bwhich\b", normalized):
            pieces = []
            for conflict in relevant_conflicts:
                pieces.append(
                    f"For {conflict.label.lower()}, the latest value I have is '{conflict.new_value}'. "
                    f"Earlier in the conversation you mentioned '{conflict.previous_value}'."
                )
            return " ".join(pieces)

        if needs_clarification:
            if query_type == "knowledge":
                return (
                    "I do not have enough grounded external context in the local knowledge base to "
                    "answer that reliably yet. Rephrase it more specifically or ask about a topic "
                    "covered by the local KB."
                )
            return "I am missing enough context to answer that safely. Can you clarify what you mean?"

        if query_type == "knowledge" and "no relevant snippets" in retrieval_reason:
            return (
                "I cannot answer that reliably from the current local knowledge base. "
                "Ask a more specific question or extend the KB for this topic."
            )

        return None

    def run_turn(self, user_input: str) -> AgentTurnResult:
        memory_block = self.memory_store.build_memory_block()
        retrieval_decision = self.knowledge_base.decide_retrieval(user_input, top_k=2)
        relevant_conflicts = self.memory_store.find_relevant_conflicts(user_input)
        warnings = list(retrieval_decision.warnings)
        if relevant_conflicts:
            warnings.append("memory contains updated values relevant to this question")
        retrieval_block = build_retrieval_block(retrieval_decision.snippets)
        diagnostics_block = build_diagnostics_block(warnings, relevant_conflicts)
        input_items = self.memory_store.recent_turns_as_input_items()
        input_items.append({"role": "user", "content": user_input})

        self.logger.log(
            "turn_started",
            {
                "user_input": user_input,
                "memory_snapshot": asdict(self.memory_store.snapshot()),
                "retrieval_decision": {
                    "should_retrieve": retrieval_decision.should_retrieve,
                    "reason": retrieval_decision.reason,
                    "query_type": retrieval_decision.query_type,
                    "needs_clarification": retrieval_decision.needs_clarification,
                    "warnings": retrieval_decision.warnings,
                    "analysis": asdict(retrieval_decision.analysis),
                    "snippets": [asdict(snippet) for snippet in retrieval_decision.snippets],
                },
                "relevant_conflicts": [asdict(conflict) for conflict in relevant_conflicts],
            },
        )

        fallback_response = self._build_safe_fallback_response(
            user_input=user_input,
            retrieval_reason=retrieval_decision.reason,
            query_type=retrieval_decision.query_type,
            relevant_conflicts=relevant_conflicts,
            needs_clarification=retrieval_decision.needs_clarification,
        )
        usage = UsageSummary()
        response_origin = "model"
        if fallback_response is not None:
            actual_model = "local-guardrail"
            raw_final_text = fallback_response
            response_origin = "local-guardrail"
        else:
            response = self.client.responses.create(
                model=self.model,
                instructions=build_system_prompt(
                    memory_block=memory_block,
                    retrieval_block=retrieval_block,
                    retrieval_active=retrieval_decision.should_retrieve,
                    diagnostics_block=diagnostics_block,
                ),
                input=input_items,
            )

            usage.add(getattr(response, "usage", None))
            actual_model = getattr(response, "model", self.model) or self.model
            raw_final_text = (response.output_text or "").strip()

        if not raw_final_text:
            raise RuntimeError("The model returned no final text for this turn.")

        allowed_chunk_ids = {snippet.id for snippet in retrieval_decision.snippets}
        cited_chunk_ids = extract_chunk_citations(raw_final_text)
        invalid_citations = [citation for citation in cited_chunk_ids if citation not in allowed_chunk_ids]
        citation_validation_passed = True
        if retrieval_decision.should_retrieve and response_origin == "model":
            if not cited_chunk_ids:
                warnings.append("model answer did not include inline chunk citations")
                citation_validation_passed = False
            if invalid_citations:
                warnings.append("model answer cited chunk ids that were not retrieved")
                citation_validation_passed = False

        sources_appendix = format_sources_appendix(retrieval_decision.snippets)
        final_text = raw_final_text
        if retrieval_decision.should_retrieve and response_origin == "model" and sources_appendix:
            final_text = f"{raw_final_text}\n\n{sources_appendix}"

        self.memory_store.remember_user_message(user_input)
        self.memory_store.remember_assistant_message(raw_final_text)

        self.logger.log(
            "turn_completed",
            {
                "model": actual_model,
                "final_output": final_text,
                "raw_final_output": raw_final_text,
                "response_origin": response_origin,
                "usage": asdict(usage),
                "memory_snapshot": asdict(self.memory_store.snapshot()),
                "retrieval_decision": {
                    "should_retrieve": retrieval_decision.should_retrieve,
                    "reason": retrieval_decision.reason,
                    "query_type": retrieval_decision.query_type,
                    "needs_clarification": retrieval_decision.needs_clarification,
                    "warnings": retrieval_decision.warnings,
                    "analysis": asdict(retrieval_decision.analysis),
                    "snippets": [asdict(snippet) for snippet in retrieval_decision.snippets],
                },
                "warnings": warnings,
                "cited_chunk_ids": cited_chunk_ids,
                "citation_validation_passed": citation_validation_passed,
                "relevant_conflicts": [asdict(conflict) for conflict in relevant_conflicts],
            },
        )

        return AgentTurnResult(
            final_text=final_text,
            model=actual_model,
            usage=usage,
            trace_log_path=self.logger.path,
            memory_block=memory_block,
            retrieval_used=retrieval_decision.should_retrieve,
            retrieval_reason=retrieval_decision.reason,
            retrieved_snippets=[asdict(snippet) for snippet in retrieval_decision.snippets],
            warnings=warnings,
            response_origin=response_origin,
            cited_chunk_ids=cited_chunk_ids,
            citation_validation_passed=citation_validation_passed,
        )


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
            "OPENAI_API_KEY is not set. Copy 02-memory-rag-agent/.env.example to "
            "02-memory-rag-agent/.env and add your key."
        )

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "The openai package is not installed. Run `python3 -m pip install -r "
            "02-memory-rag-agent/requirements.txt`."
        ) from exc

    return OpenAI(api_key=api_key)
