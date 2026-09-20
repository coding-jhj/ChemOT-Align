from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field


class RedactionResult(BaseModel):
    """Redacted text and non-sensitive finding categories."""

    model_config = ConfigDict(extra="forbid")

    redacted_text: str
    findings: list[str] = Field(default_factory=list)
    changed: bool = False

    @property
    def text(self) -> str:
        """Convenience alias for callers that consume text-like results."""

        return self.redacted_text


_PRIVATE_KEY = re.compile(
    r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
    re.IGNORECASE | re.DOTALL,
)
_BEARER_TOKEN = re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE)
_SECRET_ASSIGNMENT = re.compile(
    r"\b(?:password|passwd|pwd|api[_-]?key|secret|token)\s*[:=]\s*"
    r"(?:\"[^\"\r\n]*\"|'[^'\r\n]*'|[^\s,;]+)",
    re.IGNORECASE,
)
_FLAG_VALUE = re.compile(
    r"\b(?:FLAG|CTF)\{[^}\r\n]{1,256}\}|"
    r"\b(?:flag|ctf[_-]?flag)\s*[:=]\s*[^\s,;]+",
    re.IGNORECASE,
)
_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


def _replace(
    text: str,
    pattern: re.Pattern[str],
    replacement: str,
    finding: str,
    findings: list[str],
) -> str:
    text, count = pattern.subn(replacement, text)
    if count and finding not in findings:
        findings.append(finding)
    return text


def redact_sensitive_text(text: str) -> RedactionResult:
    """Redact common secret-bearing values without recording their contents."""

    if not isinstance(text, str):
        raise TypeError("text must be a string")

    redacted = text
    findings: list[str] = []
    redacted = _replace(redacted, _PRIVATE_KEY, "[REDACTED_PRIVATE_KEY]", "private_key", findings)
    redacted = _replace(
        redacted, _BEARER_TOKEN, "[REDACTED_BEARER_TOKEN]", "bearer_token", findings
    )
    redacted = _replace(
        redacted, _SECRET_ASSIGNMENT, "[REDACTED_SECRET_ASSIGNMENT]", "secret_assignment", findings
    )
    redacted = _replace(redacted, _FLAG_VALUE, "[REDACTED_FLAG]", "flag", findings)
    redacted = _replace(redacted, _EMAIL, "[REDACTED_EMAIL]", "email", findings)
    redacted = _replace(redacted, _IPV4, "[REDACTED_IP]", "ip_address", findings)

    return RedactionResult(
        redacted_text=redacted,
        findings=findings,
        changed=redacted != text,
    )
