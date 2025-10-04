"""aipyapp Executor Service

This module provides sandboxed Python execution capabilities via aipyapp integration.
nekro-agent acts as an orchestrator that decomposes user requests into atomic tasks,
which are then executed by aipyapp in isolated sandbox environments.

Architecture:
    nekro-agent (Orchestrator) → Atomic Tasks → aipyapp (Executor) → Results → Validation

Components:
    - sandbox_executor: Main executor managing aipyapp instances
    - task_manager: Pool management for isolated aipyapp environments
    - bridge: Translation layer between nekro and aipyapp contexts
"""

from .bridge import AipyappBridge
from .sandbox_executor import AipyappSandboxExecutor
from .task_manager import AipyappTaskManager

__all__ = [
    "AipyappBridge",
    "AipyappSandboxExecutor",
    "AipyappTaskManager",
]

