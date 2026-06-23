"""LLM safety guards: prompt-injection detection, RAG-poisoning detection,
input validation, output filtering and data-leakage prevention.

These are heuristic, defence-in-depth checks — not a substitute for the
provider's own safety systems, but they catch the common attack shapes and
keep tenant data from leaking across the boundary.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# ── Prompt injection ──────────────────────────────────────────
_INJECTION_PATTERNS = [
    r"ignore (all |the )?(previous|above|prior) (instructions|prompts)",
    r"disregard (all |the )?(previous|above|prior)",
    r"forget (everything|all|your) (instructions|rules)",
    r"you are now (a|an|in) ",
    r"system prompt",
    r"reveal (your |the )?(system )?(prompt|instructions)",
    r"act as (a |an )?(dan|developer mode|jailbreak)",
    r"</?(system|instructions?)>",
    r"new instructions:",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)

# ── RAG poisoning (suspicious content embedded in retrieved docs) ─
_POISON_PATTERNS = [
    r"ignore (the )?(retrieved|above) (context|documents?)",
    r"when (asked|answering).{0,40}(say|respond|reply)",
    r"do not (cite|mention|reveal)",
    r"assistant\s*:\s*",
    r"\bprompt\s*injection\b",
]
_POISON_RE = re.compile("|".join(_POISON_PATTERNS), re.IGNORECASE)

# ── Data leakage (secrets / PII shapes) ───────────────────────
_LEAK_PATTERNS = {
    "api_key": re.compile(r"\b(sk-[A-Za-z0-9]{20,}|cb_[A-Za-z0-9_-]{20,})\b"),
    "aws_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "private_key": re.compile(r"-----BEGIN (RSA |EC )?PRIVATE KEY-----"),
}


@dataclass
class GuardResult:
    allowed: bool
    reason: str | None = None
    score: float = 0.0


def check_prompt_injection(text: str) -> GuardResult:
    matches = _INJECTION_RE.findall(text or "")
    if matches:
        return GuardResult(False, "potential_prompt_injection", score=min(1.0, len(matches) * 0.5))
    return GuardResult(True)


def validate_input(text: str, *, max_len: int = 32000) -> GuardResult:
    if not text or not text.strip():
        return GuardResult(False, "empty_input")
    if len(text) > max_len:
        return GuardResult(False, "input_too_long")
    return GuardResult(True)


def detect_rag_poisoning(content: str) -> GuardResult:
    matches = _POISON_RE.findall(content or "")
    if matches:
        return GuardResult(False, "possible_rag_poisoning", score=min(1.0, len(matches) * 0.4))
    return GuardResult(True)


def sanitize_retrieved(content: str) -> str:
    """Neutralise instruction-like text in retrieved chunks before prompting."""
    cleaned = _POISON_RE.sub("[redacted-instruction]", content or "")
    return cleaned


def filter_output(text: str) -> tuple[str, list[str]]:
    """Redact leaked secrets from model output. Returns (clean_text, findings)."""
    findings: list[str] = []
    out = text or ""
    for label, pattern in _LEAK_PATTERNS.items():
        if pattern.search(out):
            findings.append(label)
            out = pattern.sub(f"[redacted-{label}]", out)
    return out, findings
