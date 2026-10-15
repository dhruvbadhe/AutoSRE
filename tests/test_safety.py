import re

import pytest

from app.services.safety import DANGEROUS_PATTERNS, is_unsafe, normalise

DANGEROUS = [
    "rm -rf /var/lib/postgresql",
    "rm -fr /tmp/cache",
    "DROP DATABASE payments;",
    "DROP TABLE users;",
    "TRUNCATE TABLE audit_log;",
    "truncate -s 0 /var/log/app.log",
    "mkfs.ext4 /dev/sda1",
    "dd if=/dev/zero of=/dev/sda bs=1M",
    ":(){ :|:& };:",
    ":(){:|:&};:",
    "kubectl delete ns production",
    "kubectl delete namespace production",
    "kubectl scale --replicas=0 deployment/auth-service",
    "kubectl scale deployment/auth-service --replicas=0",
]

OBFUSCATED_CASE_AND_SPACING = [
    "RM   -RF /",
    "Drop\tDatabase payments",
    "drop    TABLE users",
    "kubectl  DELETE   NS prod",
    "kubectl\nscale deployment/api   --REPLICAS=0",
    "MKFS.xfs /dev/sdb",
]

SAFE = [
    "kubectl get pods -n production",
    "kubectl describe pod auth-service-7d9f",
    "kubectl logs deployment/auth-service --tail=100",
    "kubectl rollout restart deployment/auth-service",
    "kubectl scale deployment/auth-service --replicas=3",
    "kubectl scale deployment/auth-service --replicas=10",
    "Increase the JVM heap; the old log lines were truncated by the collector.",
    "rm /tmp/app.lock",
    "",
]


@pytest.mark.parametrize("command", DANGEROUS)
def test_dangerous_command_is_blocked(command):
    assert is_unsafe(command)


@pytest.mark.parametrize("command", OBFUSCATED_CASE_AND_SPACING)
def test_mixed_case_and_extra_whitespace_is_blocked(command):
    assert is_unsafe(command)


@pytest.mark.parametrize("command", SAFE)
def test_safe_command_is_allowed(command):
    assert not is_unsafe(command)


def test_every_pattern_has_a_blocked_example():
    for pattern in DANGEROUS_PATTERNS:
        assert any(re.search(pattern, normalise(c)) for c in DANGEROUS), pattern


@pytest.mark.xfail(strict=True, reason="Known limit: a denylist can't see through shell quoting; needs an allowlist or dry-run")
def test_quoting_trick_bypasses_denylist():
    assert is_unsafe("'r''m' -rf /")
