"""Lightweight eval runner for 02 - Memory + RAG Agent."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from agent import MemoryRagAgent


@dataclass
class EvalCaseResult:
    """One eval result with a small set of pass/fail checks."""

    case_id: str
    passed: bool
    checks: list[dict[str, str]]


def load_eval_cases(project_root: Path) -> list[dict]:
    path = project_root / "evals" / "test_cases.json"
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def evaluate_case(case: dict, agent: MemoryRagAgent) -> EvalCaseResult:
    last_result = None
    for turn in case["turns"]:
        last_result = agent.run_turn(turn)

    if last_result is None:
        return EvalCaseResult(
            case_id=case["id"],
            passed=False,
            checks=[{"status": "failed", "message": "case had no turns"}],
        )

    checks: list[dict[str, str]] = []
    final_text_lower = last_result.final_text.lower()

    for expected in case.get("required_substrings", []):
        if expected.lower() in final_text_lower:
            checks.append({"status": "passed", "message": f"contains '{expected}'"})
        else:
            checks.append({"status": "failed", "message": f"missing '{expected}'"})

    for forbidden in case.get("forbidden_substrings", []):
        if forbidden.lower() in final_text_lower:
            checks.append({"status": "failed", "message": f"contains forbidden '{forbidden}'"})
        else:
            checks.append({"status": "passed", "message": f"does not contain '{forbidden}'"})

    expected_retrieval = case.get("expect_retrieval_used")
    if expected_retrieval is not None:
        actual = str(last_result.retrieval_used).lower()
        expected = str(bool(expected_retrieval)).lower()
        checks.append(
            {
                "status": "passed" if actual == expected else "failed",
                "message": f"retrieval_used={actual}, expected={expected}",
            }
        )

    expected_origin = case.get("expect_response_origin")
    if expected_origin is not None:
        actual = last_result.response_origin
        checks.append(
            {
                "status": "passed" if actual == expected_origin else "failed",
                "message": f"response_origin={actual}, expected={expected_origin}",
            }
        )

    expected_citations = case.get("expect_citation_validation")
    if expected_citations is not None:
        actual = str(last_result.citation_validation_passed).lower()
        expected = str(bool(expected_citations)).lower()
        checks.append(
            {
                "status": "passed" if actual == expected else "failed",
                "message": f"citation_validation={actual}, expected={expected}",
            }
        )

    passed = all(check["status"] == "passed" for check in checks) if checks else True
    return EvalCaseResult(case_id=case["id"], passed=passed, checks=checks)
