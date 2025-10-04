"""aipyapp Orchestrator Plugin

This plugin integrates aipyapp Python execution capabilities into nekro-agent.
It exposes sandbox methods that allow the AI agent to execute Python code
in isolated, controlled environments.

Architecture:
    User Request → nekro-agent (orchestrator)
                        ↓
                  [Decompose & Plan]
                        ↓
                  [Generate Prompts]
                        ↓
                  aipyapp (sandboxed executor) ← Atomic Task
                        ↓
                  [Execute Python]
                        ↓
                  Results → nekro-agent
                        ↓
                  [Validate & Decide]
                        ↓
             Next Task or Complete
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import Field

from nekro_agent.core import logger
from nekro_agent.core.config import config as core_config
from nekro_agent.core.core_utils import ConfigBase
from nekro_agent.schemas.agent_ctx import AgentCtx
from nekro_agent.services.plugin import (
    NekroPlugin,
    SandboxMethodType,
)
from nekro_agent.services.aipyapp_executor import (
    AipyappSandboxExecutor,
    AipyappTaskManager,
)

# Create plugin instance
plugin = NekroPlugin(
    name="aipyapp Orchestrator",
    module_name="aipyapp_orchestrator",
    description="Python execution engine powered by aipyapp for sandboxed code execution",
    version="1.0.0",
    author="nekro-agent",
    url="https://github.com/Zeeeepa/nekro-agent",
    support_adapter=["onebot_v11", "minecraft", "sse", "discord"],
)


@plugin.mount_config()
class AipyappConfig(ConfigBase):
    """Configuration for aipyapp Python execution"""
    
    ENABLE_AIPYAPP: bool = Field(
        default=True,
        title="Enable aipyapp Python execution",
        description="Enable sandboxed Python code execution via aipyapp",
    )
    
    TASK_TIMEOUT: int = Field(
        default=300,
        title="Task execution timeout (seconds)",
        description="Maximum time allowed for a single task execution",
    )
    
    MAX_TASKS_PER_SESSION: int = Field(
        default=50,
        title="Maximum tasks per session",
        description="Limit on number of tasks per chat session",
    )
    
    SESSION_TIMEOUT: int = Field(
        default=3600,
        title="Session idle timeout (seconds)",
        description="Time before idle session is cleaned up",
    )
    
    ALLOW_NETWORK: bool = Field(
        default=False,
        title="Allow network access",
        description="Whether tasks can access network resources",
    )
    
    ALLOW_FILE_IO: bool = Field(
        default=True,
        title="Allow file I/O",
        description="Whether tasks can read/write files",
    )
    
    MAX_MEMORY_MB: int = Field(
        default=512,
        title="Maximum memory per task (MB)",
        description="Memory limit for task execution",
    )
    
    AIPYAPP_WORKDIR: str = Field(
        default="./data/aipyapp_workdir",
        title="Working directory",
        description="Base directory for aipyapp task execution",
    )


# Check if aipyapp is available
try:
    import aipyapp
    AIPYAPP_AVAILABLE = True
except ImportError:
    AIPYAPP_AVAILABLE = False
    logger.warning(
        "aipyapp not installed - Python execution features disabled. "
        "Install with: pip install 'nekro-agent[aipyapp]'"
    )


class AipyappOrchestratorPlugin(NekroPlugin):
    """Plugin that orchestrates Python task execution via aipyapp
    
    This plugin:
    - Exposes Python execution sandbox methods to the AI agent
    - Manages isolated aipyapp environments per chat session
    - Handles task lifecycle and resource cleanup
    - Provides result formatting and error handling
    """
    
    def __init__(self):
        super().__init__()
        self.executor: Optional[AipyappSandboxExecutor] = None
        self.task_manager: Optional[AipyappTaskManager] = None
        self._initialized = False
    
    async def init(self, **kwargs):
        """Initialize the plugin"""
        if not AIPYAPP_AVAILABLE:
            logger.warning("aipyapp not available, plugin will not initialize")
            return
        
        config = kwargs.get("config", AipyappConfig())
        
        if not config.ENABLE_AIPYAPP:
            logger.info("aipyapp execution disabled in config")
            return
        
        # Initialize workdir
        workdir = Path(config.AIPYAPP_WORKDIR)
        workdir.mkdir(parents=True, exist_ok=True)
        
        # Initialize executor
        self.executor = AipyappSandboxExecutor(
            workdir=workdir,
            timeout=config.TASK_TIMEOUT,
            max_memory_mb=config.MAX_MEMORY_MB,
        )
        
        # Initialize task manager
        self.task_manager = AipyappTaskManager(
            workdir=workdir,
            max_sessions=100,  # Could be configurable
            session_timeout=config.SESSION_TIMEOUT,
        )
        
        self._initialized = True
        logger.info("AipyappOrchestratorPlugin initialized successfully")
    
    @plugin.mount_sandbox_method(SandboxMethodType.TOOL, "execute_python_task")
    async def execute_python_task(
        self,
        _ctx: AgentCtx,
        instruction: str,
        context: Optional[str] = None,
    ) -> str:
        """Execute a Python task using aipyapp in isolated sandbox
        
        This method allows the AI agent to execute Python code for data analysis,
        visualization, calculations, and other computational tasks.
        
        Args:
            instruction: Natural language description of Python task to execute.
                Examples:
                - "Load data.csv and calculate mean of column A"
                - "Create a bar chart of sales data and save as plot.png"
                - "Parse JSON response and extract email addresses"
            
            context: Optional JSON string with context data (variables, prior results).
                Format: {"variables": {"df": "..."}, "imports": ["pandas", "numpy"]}
        
        Returns:
            JSON string with execution result containing:
            - success: bool - whether execution succeeded
            - output: str - printed output and results
            - error: str | None - error message if failed
            - artifacts: list - generated files (plots, CSVs, etc.)
            - execution_time: float - time taken in seconds
            - variables: dict - resulting Python variables
        
        Example:
            ```python
            result = await execute_python_task(
                ctx,
                "Load data.csv and calculate mean of column A"
            )
            # Returns: {"success": true, "output": "Mean: 42.5", ...}
            ```
        
        Security:
            - Executes in isolated sandbox environment
            - Resource limits enforced (memory, time, CPU)
            - Network access controlled by configuration
            - File system access restricted to sandbox directory
        """
        if not self._initialized:
            return json.dumps({
                "success": False,
                "error": "aipyapp executor not initialized",
                "output": "",
            })
        
        try:
            # Parse context if provided
            context_dict = None
            if context:
                try:
                    context_dict = json.loads(context)
                except json.JSONDecodeError:
                    return json.dumps({
                        "success": False,
                        "error": "Invalid context JSON format",
                        "output": "",
                    })
            
            # Execute task
            result = await self.executor.execute_task(
                ctx=_ctx,
                instruction=instruction,
                context=context_dict,
            )
            
            return json.dumps(result, ensure_ascii=False)
            
        except Exception as e:
            logger.exception("Python task execution failed", instruction=instruction)
            return json.dumps({
                "success": False,
                "error": str(e),
                "output": "",
            })
    
    @plugin.mount_sandbox_method(SandboxMethodType.TOOL, "execute_python_workflow")
    async def execute_python_workflow(
        self,
        _ctx: AgentCtx,
        instructions: str,
    ) -> str:
        """Execute a multi-step Python workflow as atomic tasks
        
        This method executes a sequence of related Python tasks, maintaining
        state (variables, imports) across steps for data processing pipelines.
        
        Args:
            instructions: JSON string with list of task instructions.
                Format: ["step 1 instruction", "step 2 instruction", ...]
                Example: [
                    "Load data.csv into DataFrame df",
                    "Calculate mean and std of column 'price'",
                    "Create histogram of prices and save as hist.png"
                ]
        
        Returns:
            JSON string with workflow results containing:
            - success: bool - whether entire workflow succeeded
            - steps: list - results for each step
            - final_output: str - combined output
            - artifacts: list - all generated files
            - total_time: float - total execution time
        
        Example:
            ```python
            workflow = json.dumps([
                "Load data.csv",
                "Calculate statistics",
                "Create visualization"
            ])
            result = await execute_python_workflow(ctx, workflow)
            ```
        
        Note:
            All steps share the same Python environment and variables.
            If any step fails, subsequent steps are skipped.
        """
        if not self._initialized:
            return json.dumps({
                "success": False,
                "error": "aipyapp executor not initialized",
                "steps": [],
            })
        
        try:
            # Parse instructions
            try:
                instruction_list = json.loads(instructions)
                if not isinstance(instruction_list, list):
                    raise ValueError("Instructions must be a JSON array")
            except (json.JSONDecodeError, ValueError) as e:
                return json.dumps({
                    "success": False,
                    "error": f"Invalid instructions format: {e}",
                    "steps": [],
                })
            
            # Execute steps sequentially
            steps_results = []
            context_dict = {}
            total_time = 0.0
            
            for i, instruction in enumerate(instruction_list):
                step_result = await self.executor.execute_task(
                    ctx=_ctx,
                    instruction=instruction,
                    context=context_dict,
                )
                
                steps_results.append({
                    "step": i + 1,
                    "instruction": instruction,
                    **step_result,
                })
                
                # If step failed, stop workflow
                if not step_result.get("success"):
                    return json.dumps({
                        "success": False,
                        "steps": steps_results,
                        "error": f"Step {i+1} failed: {step_result.get('error')}",
                        "total_time": total_time,
                    })
                
                # Update context with variables from this step
                context_dict["variables"] = step_result.get("variables", {})
                total_time += step_result.get("execution_time", 0)
            
            # Collect all artifacts
            all_artifacts = []
            for step in steps_results:
                all_artifacts.extend(step.get("artifacts", []))
            
            return json.dumps({
                "success": True,
                "steps": steps_results,
                "final_output": steps_results[-1].get("output", ""),
                "artifacts": all_artifacts,
                "total_time": total_time,
            }, ensure_ascii=False)
            
        except Exception as e:
            logger.exception("Python workflow execution failed")
            return json.dumps({
                "success": False,
                "error": str(e),
                "steps": steps_results if 'steps_results' in locals() else [],
            })


# Register the plugin
aipyapp_plugin = AipyappOrchestratorPlugin()
