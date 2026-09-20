from __future__ import annotations

import pytest

from chemot_align.safety.redaction import redact_sensitive_text


@pytest.mark.parametrize(
    ("text", "finding"),
    [
        ("-----BEGIN PRIVATE KEY-----\nsecret\n-----END PRIVATE KEY-----", "private_key"),
        ("password=super-secret", "secret_assignment"),
        ("Authorization: Bearer abc.def.ghi", "bearer_token"),
        ("contact researcher@example.com", "email"),
        ("host=192.0.2.10", "ip_address"),
        ("result=FLAG{not-public}", "flag"),
    ],
)
def test_sensitive_text_is_redacted(text: str, finding: str) -> None:
    result = redact_sensitive_text(text)

    assert result.changed is True
    assert finding in result.findings
    assert text not in result.redacted_text


def test_normal_words_and_synthetic_case_ids_are_preserved() -> None:
    text = "case-000001 has a password policy and normal process status"

    result = redact_sensitive_text(text)

    assert result.changed is False
    assert result.redacted_text == text
