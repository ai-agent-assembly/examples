"""Plain Python tool functions for the policy-enforcement scenario.

Each function represents an agent tool.  Safe tools are allowed; risky tools
are blocked by the policy rules in ../../policy.yaml.
"""
from __future__ import annotations


def read_config(key: str) -> str:
    """Return a configuration value by key (safe, read-only)."""
    _config = {
        "database.host": "localhost:5432",
        "service.port": "8080",
        "log.level": "INFO",
    }
    return _config.get(key, f"(no value for '{key}')")


def list_agents() -> list[str]:
    """Return the registered agent IDs (safe, read-only)."""
    return ["agent-001", "agent-002", "agent-003"]


def delete_agent(agent_id: str) -> str:
    """Delete an agent from the registry (RISKY — DENIED by policy)."""
    return f"Deleted agent {agent_id}"


def send_email(to: str, subject: str, body: str) -> str:
    """Send an email (RISKY — DENIED by policy: network egress)."""
    return f"Email sent to {to}: {subject}"
