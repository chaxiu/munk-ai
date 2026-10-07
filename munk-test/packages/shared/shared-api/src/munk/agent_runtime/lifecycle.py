from typing import Literal

AgentLifecycleState = Literal["started", "running", "canceled", "failed", "ended"]

__all__ = ["AgentLifecycleState"]
