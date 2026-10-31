"""Strip secrets from pasted errors before they leave the process.

Pasted output often carries credentials: an AWS key in a stack trace, a bearer
token in a curl -v dump, a password in a connection string. Anything matched
here is replaced with [REDACTED:<kind>] before the text is sent to an LLM.
It is a safety net, not a guarantee, so the UI still tells people not to
paste secrets.
"""

import re

# (kind, pattern). Where a pattern has a group named "secret", only that part
# is replaced, so the surrounding text (the key name) stays readable.
PATTERNS = [
    ("private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?(?:-----END [A-Z ]*PRIVATE KEY-----|\Z)", re.S)),
    ("aws-access-key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("anthropic-key", re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{10,}")),
    ("openai-key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_\-]{20,}")),
    ("github-token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})")),
    ("gitlab-token", re.compile(r"\bglpat-[A-Za-z0-9_\-]{20,}")),
    ("slack-token", re.compile(r"\bxox[abprs]-[A-Za-z0-9\-]{10,}")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}")),
    ("url-credentials", re.compile(r"(?<=://)(?P<secret>[^\s:/@]+:[^\s@/]+)(?=@)")),
    ("auth-header", re.compile(r"(?i)\b(?:authorization|proxy-authorization)\s*[:=]\s*(?:bearer|basic|token)?\s*(?P<secret>[A-Za-z0-9._~+/=\-]{8,})")),
    ("bearer", re.compile(r"(?i)\bbearer\s+(?P<secret>[A-Za-z0-9._~+/=\-]{16,})")),
    ("aws-secret", re.compile(r"(?i)aws_secret_access_key\s*[=:]\s*[\"']?(?P<secret>[A-Za-z0-9/+=]{30,})")),
    (
        "assignment",
        re.compile(
            # no leading \b: DB_PASSWORD and GITHUB_TOKEN must match too
            r"(?i)(?:password|passwd|pwd|secret|api[_-]?key|token)"
            r"\s*[=:]\s*[\"']?(?!\[REDACTED|(?:bearer|basic)\s)(?P<secret>[^\s\"',;&]{4,})"
        ),
    ),
]


def redact(text: str) -> tuple[str, int]:
    """Return the text with secrets replaced, and how many were replaced."""
    count = 0

    for kind, pattern in PATTERNS:
        def swap(m, kind=kind):
            nonlocal count
            count += 1
            if "secret" in m.groupdict() and m.group("secret") is not None:
                start, end = m.span("secret")
                s0 = m.start()
                return m.group(0)[: start - s0] + f"[REDACTED:{kind}]" + m.group(0)[end - s0 :]
            return f"[REDACTED:{kind}]"

        text = pattern.sub(swap, text)
    return text, count
