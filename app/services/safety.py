import re

# shortcut: a denylist on normalised text is bypassable (quoting, base64, $(...)); upgrade to an allowlist of safe verbs or a dry-run.
DANGEROUS_PATTERNS = [
    r"\brm -(rf|fr)",
    r"\bdrop database\b",
    r"\bdrop table\b",
    r"\btruncate\b",
    r"\bmkfs\b",
    r"\bdd if=/dev/zero\b",
    r":\(\) ?\{ ?: ?\| ?: ?& ?\} ?; ?:",  # fork bomb
    r"\bkubectl delete (ns|namespaces?)\b",
    r"\bscale\b.*--replicas[= ]0\b",
]


def normalise(text: str) -> str:
    return " ".join(text.lower().split())


def is_unsafe(command: str) -> bool:
    text = normalise(command)
    return any(re.search(pattern, text) for pattern in DANGEROUS_PATTERNS)
