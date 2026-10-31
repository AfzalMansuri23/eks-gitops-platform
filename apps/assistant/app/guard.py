"""Output and input guardrails for answers that contain shell commands.

Every answer passes through `check_answer` before it reaches the browser,
whether it came from the runbooks or from the LLM:

- BLOCK: commands a troubleshooting tool should never suggest: remote code
  execution, sending credentials or files off the machine, creating new
  credentials, disabling security controls, and wipes. Removed and counted.
- SENSITIVE: commands that print a secret value or a credential file on the
  user's own terminal (the Argo CD admin password, cat ~/.aws/credentials).
  Kept, flagged, so the UI can say not to paste the output anywhere.
- DESTRUCTIVE: commands that are sometimes the right fix but change or delete
  things (kubectl delete, force-unlock, git push --force). Kept, flagged.
- Secrets in the answer text are redacted, in case the model echoes one.

`injection_signals` spots prompt-injection attempts in pasted text. It does not
block (a real log can quote such a phrase); it feeds a metric and the log, and
the output checks above are the actual control.
"""

import re
from dataclasses import dataclass, field

from .redact import redact

I = re.IGNORECASE

# files that hold credentials
CRED = r"(?:\.aws/credentials|\.ssh/id_\w+|id_rsa|id_ed25519|\.kube/config|/etc/shadow|\.docker/config\.json|\.netrc|\.git-credentials)"
SEND = r"\b(?:curl|wget|nc|ncat|scp|rsync|ftp)\b"

BLOCK = [
    # remote code execution
    ("download-and-run", re.compile(r"\b(?:curl|wget|iwr|invoke-webrequest)\b[^|;&]*\|\s*(?:sudo\s+)?(?:ba|z|da)?sh\b", I)),
    ("download-and-run", re.compile(r"\b(?:iex|invoke-expression)\b", I)),
    ("decode-and-run", re.compile(r"base64\s+(?:-d|--decode)\b[^|]*\|\s*(?:sudo\s+)?(?:ba|z)?sh\b", I)),
    ("reverse-shell", re.compile(r"/dev/(?:tcp|udp)/|\bnc(?:at)?\b[^|;]*\s-(?:e|c)\s|\bsocat\b.*\bexec:", I)),
    # sending credentials, secrets or files off the machine
    ("exfiltrate", re.compile(SEND + r".*" + CRED + r"|" + CRED + r".*\|\s*" + SEND, I)),
    ("exfiltrate", re.compile(r"\b(?:printenv|env|set)\b\s*\|\s*" + SEND, I)),
    ("exfiltrate", re.compile(r"\bsecrets?\b.*\|\s*" + SEND, I)),
    ("exfiltrate", re.compile(r"\b(?:curl|wget)\b.*(?:-d\s*@|--data(?:-binary)?\s*@|-T\s|--upload-file|-F\s*\S+=@)", I)),
    # new credentials or wider access
    ("create-credentials", re.compile(r"\baws\s+iam\s+(?:create-access-key|create-login-profile|attach-user-policy|put-user-policy)\b|\bkubectl\s+create\s+(?:clusterrolebinding|token)\b", I)),
    ("disable-security", re.compile(r"\bchmod\s+(?:-R\s+)?777\s+/(?:\s|$)|\biptables\s+-F\b|\bufw\s+disable\b|\bsetenforce\s+0\b|\bsystemctl\s+(?:stop|disable)\s+(?:firewalld|auditd)\b", I)),
    # wipes
    ("wipe", re.compile(r"\brm\s+-(?:[a-z]*r[a-z]*f|[a-z]*f[a-z]*r)[a-z]*\s+(?:--no-preserve-root\s+)?(?:/|~|\*|/\*|\$HOME)(?:\s|$)", I)),
    ("wipe", re.compile(r"\bmkfs(?:\.\w+)?\b|\bdd\b[^|;]*\bof=/dev/(?!null)|\bshred\b|:\(\)\s*\{\s*:\|:&\s*\};:", I)),
    ("wipe", re.compile(r"\bterraform\s+destroy\b.*-auto-approve|\baws\s+s3\s+rb\b.*--force|\baws\s+s3\s+rm\b.*--recursive|\bdrop\s+(?:database|schema)\b", I)),
    ("wipe", re.compile(r"\bkubectl\s+delete\s+(?:ns|namespaces?)\s+(?:kube-system|kube-public|default|argocd|monitoring|logging)\b", I)),
    # cluster-wide delete with no selector; a targeted one (--field-selector, -l) is only destructive
    ("wipe", re.compile(r"\bkubectl\s+delete\b(?!.*(?:--field-selector|--selector|\s-l\s))(?:.*\s--all-namespaces\b|.*\s-A\b)", I)),
]

SENSITIVE = [
    ("prints-k8s-secret", re.compile(r"\bkubectl\b.*\bget\s+secrets?\b.*(?:-o\s*=?\s*(?:yaml|json|jsonpath|go-template)|--output|--template)|\bkubectl\b.*\bsecrets?\b.*\|\s*base64", I)),
    ("prints-cloud-secret", re.compile(r"\baws\s+secretsmanager\s+get-secret-value\b|\baws\s+ssm\s+get-parameters?\b.*--with-decryption|\bgcloud\s+secrets\s+versions\s+access\b|\baz\s+keyvault\s+secret\s+show\b|\bvault\s+(?:kv\s+get|read)\b", I)),
    ("prints-credentials", re.compile(r"\b(?:cat|less|more|head|tail|type|get-content|base64|xxd|strings)\b.*" + CRED, I)),
]

DESTRUCTIVE = re.compile(
    r"\bkubectl\s+(?:delete|drain|cordon|replace\s+--force|rollout\s+undo)\b|\bhelm\s+(?:uninstall|delete|rollback)\b"
    r"|\bterraform\s+(?:destroy|force-unlock|state\s+rm|taint|import|apply)\b|\bdocker\s+(?:system|volume|image)\s+prune\b"
    r"|\brm\s+-[a-z]*r|\bgit\s+(?:reset\s+--hard|push\s+(?:-f|--force)|clean\s+-[a-z]*f)"
    r"|\bkill\s+-9\b|\bsystemctl\s+(?:stop|restart|disable)\b|\breboot\b|\bshutdown\b|\btruncate\b|\bdelete\s+from\b|\bdrop\s+table\b"
    r"|\baws\s+\S+\s+(?:delete|terminate|remove)-|\bforce-unlock\b|\bchmod\s+(?:-R\s+)?777\b|--insecure-skip-tls-verify"
    # changes who can access what
    r"|\baws\s+eks\s+(?:create-access-entry|associate-access-policy)\b|\baws\s+iam\s+(?:attach|put|update)-\S*polic|\bkubectl\s+(?:create|apply)\b.*\brolebinding\b",
    I,
)

TAGS = re.compile(r"</?\s*(?:pasted_error|runbook_candidates|system|instructions)\s*>", I)

INJECTION = [
    ("override", re.compile(r"\b(?:ignore|disregard|forget)\b.{0,40}\b(?:instructions|rules|prompt|above|previous)\b", I)),
    ("prompt-leak", re.compile(r"\b(?:system\s+prompt|your\s+instructions|initial\s+prompt)\b", I)),
    ("role-play", re.compile(r"\byou\s+are\s+now\b|\bact\s+as\b|\bdeveloper\s+mode\b|\bjailbreak\b", I)),
    ("tag-escape", TAGS),
]


@dataclass
class Checked:
    cause: str | None
    fix: str | None
    commands: list[str]
    risks: list[str]  # "safe", "sensitive" or "destructive", one per kept command
    blocked: list[str] = field(default_factory=list)  # reason per removed command
    redactions: int = 0


def command_verdict(command: str) -> tuple[str, str | None]:
    for reason, pattern in BLOCK:
        if pattern.search(command):
            return "block", reason
    for reason, pattern in SENSITIVE:
        if pattern.search(command):
            return "sensitive", reason
    if DESTRUCTIVE.search(command):
        return "destructive", None
    return "safe", None


def check_answer(cause: str | None, fix: str | None, commands: list[str]) -> Checked:
    out = Checked(cause=None, fix=None, commands=[], risks=[])
    for name, value in (("cause", cause), ("fix", fix)):
        if value is not None:
            clean, n = redact(value)
            setattr(out, name, clean)
            out.redactions += n
    for command in commands:
        verdict, reason = command_verdict(command)
        if verdict == "block":
            out.blocked.append(reason)
            continue
        clean, n = redact(command)
        out.redactions += n
        out.commands.append(clean)
        out.risks.append(verdict)
    return out


def injection_signals(text: str) -> list[str]:
    return [kind for kind, pattern in INJECTION if pattern.search(text)]


def neutralize_tags(text: str) -> str:
    """Stop pasted text from closing or opening the prompt's own tags."""
    return TAGS.sub(lambda m: m.group(0).replace("<", "‹").replace(">", "›"), text)
