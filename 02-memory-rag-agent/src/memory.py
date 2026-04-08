"""Short-term memory management for 02 - Memory + RAG Agent."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass


@dataclass
class ConversationTurn:
    """One conversational turn stored for short-term continuity."""

    role: str
    text: str


@dataclass
class MemoryFact:
    """A structured fact recalled from the conversation."""

    key: str
    label: str
    value: str
    evidence: str


@dataclass
class MemorySnapshot:
    """Serializable memory state for debugging and prompting."""

    facts: list[dict[str, str]]
    recent_turns: list[dict[str, str]]
    conflicts: list[dict[str, str]]


@dataclass
class MemoryConflict:
    """Represents a memory fact that was updated to a different value later on."""

    key: str
    label: str
    previous_value: str
    new_value: str
    previous_evidence: str
    new_evidence: str


def _clean_capture(value: str) -> str:
    value = re.sub(r"\s+", " ", value.strip())
    return value.rstrip(".,!?;:")


def _trim_preference_value(value: str) -> str:
    trimmed = re.split(r"\band my favorite\b", value, maxsplit=1, flags=re.IGNORECASE)[0]
    return _clean_capture(trimmed)


def _append_unique(items: list[str], value: str) -> None:
    normalized = value.casefold()
    if any(existing.casefold() == normalized for existing in items):
        return
    items.append(value)


def extract_candidate_facts(text: str) -> list[MemoryFact]:
    """Extract a narrow set of explicit user facts and preferences."""

    facts: list[MemoryFact] = []
    compact = " ".join(text.split())

    patterns: list[tuple[str, str, str, str]] = [
        ("user_name", "Name", r"\b(?:my name is|call me)\s+([^.!?\n]{1,40})", "value"),
        (
            "user_location",
            "Location",
            r"\b(?:i live in|i am based in|i'm based in|i moved to|i relocated to)\s+([^.!?\n]{1,40})",
            "value",
        ),
        ("user_role", "Role", r"\b(?:i work as|i am a|i'm a)\s+([^.!?\n]{1,50})", "value"),
        ("preferred_language", "Preferred language", r"\b(?:please answer in|i prefer answers in)\s+([^.!?\n]{1,30})", "value"),
    ]

    for key, label, pattern, mode in patterns:
        match = re.search(pattern, compact, flags=re.IGNORECASE)
        if not match:
            continue
        value = _clean_capture(match.group(1))
        if value:
            facts.append(MemoryFact(key=key, label=label, value=value, evidence=text))

    preference_patterns = [
        r"\bI prefer ([^.!?\n]{1,80})",
        r"\bI like ([^.!?\n]{1,80})",
        r"\bI love ([^.!?\n]{1,80})",
        r"\bI do not like ([^.!?\n]{1,80})",
        r"\bI don't like ([^.!?\n]{1,80})",
    ]

    preferences: list[str] = []
    for pattern in preference_patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            value = _trim_preference_value(match.group(1))
            if value:
                _append_unique(preferences, value)

    favorite_match = re.search(
        r"\bmy favorite ([a-z][a-z -]{0,30}) is ([^.!?\n]{1,60})",
        compact,
        flags=re.IGNORECASE,
    )
    if favorite_match:
        subject = _clean_capture(favorite_match.group(1))
        value = _clean_capture(favorite_match.group(2))
        if subject and value:
            _append_unique(preferences, f"favorite {subject}: {value}")

    for index, value in enumerate(preferences, start=1):
        facts.append(
            MemoryFact(
                key=f"preference_{index}",
                label="Preference",
                value=value,
                evidence=text,
            )
        )

    return facts


class ShortTermMemoryStore:
    """Stores recent turns and explicit user facts for one active session."""

    def __init__(self, max_recent_turns: int = 8) -> None:
        self.max_recent_turns = max_recent_turns
        self._recent_turns: list[ConversationTurn] = []
        self._facts_by_key: dict[str, MemoryFact] = {}
        self._preference_items: list[str] = []
        self._conflicts: list[MemoryConflict] = []

    def reset(self) -> None:
        self._recent_turns.clear()
        self._facts_by_key.clear()
        self._preference_items.clear()
        self._conflicts.clear()

    def remember_user_message(self, text: str) -> None:
        self._append_turn("user", text)
        for fact in extract_candidate_facts(text):
            if fact.key.startswith("preference_"):
                _append_unique(self._preference_items, fact.value)
                continue
            current_fact = self._facts_by_key.get(fact.key)
            if current_fact is not None and current_fact.value != fact.value:
                self._record_conflict(current_fact, fact)
            self._facts_by_key[fact.key] = fact

    def remember_assistant_message(self, text: str) -> None:
        self._append_turn("assistant", text)

    def _append_turn(self, role: str, text: str) -> None:
        self._recent_turns.append(ConversationTurn(role=role, text=text.strip()))
        self._recent_turns = self._recent_turns[-self.max_recent_turns :]

    def snapshot(self) -> MemorySnapshot:
        facts = [asdict(fact) for fact in self._facts_by_key.values()]
        for value in self._preference_items:
            facts.append(
                {
                    "key": "preference",
                    "label": "Preference",
                    "value": value,
                    "evidence": "user-stated preference",
                }
            )
        recent_turns = [asdict(turn) for turn in self._recent_turns]
        conflicts = [asdict(conflict) for conflict in self._conflicts]
        return MemorySnapshot(facts=facts, recent_turns=recent_turns, conflicts=conflicts)

    def _record_conflict(self, previous: MemoryFact, current: MemoryFact) -> None:
        candidate = MemoryConflict(
            key=current.key,
            label=current.label,
            previous_value=previous.value,
            new_value=current.value,
            previous_evidence=previous.evidence,
            new_evidence=current.evidence,
        )
        if self._conflicts and asdict(self._conflicts[-1]) == asdict(candidate):
            return
        self._conflicts.append(candidate)

    def build_memory_block(self) -> str:
        lines: list[str] = []

        if self._facts_by_key:
            lines.append("Known user facts:")
            for fact in self._facts_by_key.values():
                lines.append(f"- {fact.label}: {fact.value}")

        if self._preference_items:
            lines.append("Known preferences:")
            for item in self._preference_items:
                lines.append(f"- {item}")

        if self._conflicts:
            lines.append("Potential memory updates:")
            for conflict in self._conflicts[-3:]:
                lines.append(
                    f"- {conflict.label}: latest '{conflict.new_value}', earlier '{conflict.previous_value}'"
                )

        if not lines:
            return "No stored memory yet."

        return "\n".join(lines)

    def recent_turns_as_input_items(self) -> list[dict[str, str]]:
        return [{"role": turn.role, "content": turn.text} for turn in self._recent_turns]

    def get_conflicts(self) -> list[MemoryConflict]:
        return list(self._conflicts)

    def get_fact(self, key: str) -> MemoryFact | None:
        return self._facts_by_key.get(key)

    def find_relevant_conflicts(self, query: str) -> list[MemoryConflict]:
        normalized = query.lower()
        relevant_keys: set[str] = set()

        if re.search(r"\bname\b", normalized):
            relevant_keys.add("user_name")
        if re.search(r"\bwhere\b|\blive\b|\bbased\b|\blocation\b", normalized):
            relevant_keys.add("user_location")
        if re.search(r"\bwork\b|\bjob\b|\brole\b", normalized):
            relevant_keys.add("user_role")
        if re.search(r"\blanguage\b|\banswer in\b", normalized):
            relevant_keys.add("preferred_language")

        if not relevant_keys:
            return []

        return [conflict for conflict in self._conflicts if conflict.key in relevant_keys]
