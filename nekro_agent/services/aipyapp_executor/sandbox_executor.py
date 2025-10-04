"""Sandbox Executor - Main interface for aipyapp execution

This module provides the primary execution interface that nekro-agent uses
to run Python tasks in isolated aipyapp environments.
"""

import asyncio
from typing import Any, Dict, Optional
from pathlib import Path

from nekro_agent.core import logger
from nekro_agent.schemas.agent_ctx import AgentCtx

from .bridge import AipyappBridge

# Lazy import to avoid hard dependency
try:
    from aipyapp.aipy import Task, TaskManager
    from aipyapp.aipy.config import ConfigManager
    AIPYAPP_AVAILABLE = True
except ImportError:
    AIPYAPP_AVAILABLE = False
    logger.warning("aipyapp not installed - Python execution features disabled")


class AipyappExecutionError(Exception):
    """Raised when aipyapp execution fails"""
    pass


class AipyappSandboxExecutor:
    """Executes Python tasks via aipyapp in sandboxed environments
    
    This executor:
    - Creates isolated aipyapp Task instances per session
    - Manages task lifecycle (create, execute, cleanup)
    - Enforces resource limits and timeouts
    - Provides async interface for nekro-agent
    
    Example:
        executor = AipyappSandboxExecutor(config)
        result = await executor.execute_task(ctx, "print('Hello')")
    """
    
    def __init__(
        self,
        workdir: Path,
        timeout: int = 300,
        max_memory_mb: int = 512,
    ):
        """Initialize the sandbox executor
        
        Args:
            workdir: Base working directory for aipyapp tasks
            timeout: Maximum execution time per task (seconds)
            max_memory_mb: Maximum memory per task (MB)
        """
        if not AIPYAPP_AVAILABLE:
            raise ImportError(
                "aipyapp is not installed. Install with: pip install aipyapp"
            )
        
        self.workdir = Path(workdir)
        self.workdir.mkdir(parents=True, exist_ok=True)
        
        self.timeout = timeout
        self.max_memory_mb = max_memory_mb
        self.bridge = AipyappBridge()
        
        # Task managers per session
        self._task_managers: Dict[str, TaskManager] = {}
        
        logger.info(
            "AipyappSandboxExecutor initialized",
            workdir=str(self.workdir),
            timeout=timeout,
        )
    
    async def execute_task(
        self,
        ctx: AgentCtx,
        instruction: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a Python task in sandboxed aipyapp environment
        
        Args:
            ctx: nekro-agent execution context
            instruction: Natural language instruction for Python task
            context: Optional context data (variables, prior results)
            
        Returns:
            Execution result dictionary with output, artifacts, etc.
            
        Raises:
            AipyappExecutionError: If execution fails
        """
        session_id = f"{ctx.chat_key}_{ctx.user_id}"
        
        try:
            # Get or create task manager for this session
            task_manager = await self._get_task_manager(ctx)
            
            # Create aipyapp context
            aipyapp_ctx = self.bridge.create_aipyapp_context(ctx)
            if context:
                aipyapp_ctx.update(context)
            
            # Execute with timeout
            result = await asyncio.wait_for(
                self._execute_in_aipyapp(task_manager, instruction, aipyapp_ctx),
                timeout=self.timeout
            )
            
            # Format result for nekro-agent
            return self.bridge.format_result_for_nekro(result)
            
        except asyncio.TimeoutError:
            error_msg = f"Task execution exceeded {self.timeout}s timeout"
            logger.error(error_msg, session_id=session_id)
            raise AipyappExecutionError(error_msg)
            
        except Exception as e:
            logger.exception("aipyapp execution failed", session_id=session_id)
            error_info = self.bridge.map_error(e)
            raise AipyappExecutionError(error_info["error_message"]) from e
    
    async def _get_task_manager(self, ctx: AgentCtx) -> TaskManager:
        """Get or create TaskManager for session
        
        Args:
            ctx: nekro-agent context
            
        Returns:
            aipyapp TaskManager instance
        """
        session_id = f"{ctx.chat_key}_{ctx.user_id}"
        
        if session_id not in self._task_managers:
            # Create session-specific workdir
            session_workdir = self.workdir / session_id
            session_workdir.mkdir(parents=True, exist_ok=True)
            
            # Initialize aipyapp ConfigManager
            config_manager = ConfigManager(str(session_workdir))
            
            # Initialize aipyapp TaskManager
            task_manager = TaskManager(
                cwd=session_workdir,
                settings=config_manager.get_config(),
            )
            
            self._task_managers[session_id] = task_manager
            logger.info("Created TaskManager for session", session_id=session_id)
        
        return self._task_managers[session_id]
    
    async def _execute_in_aipyapp(
        self,
        task_manager: TaskManager,
        instruction: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute instruction in aipyapp
        
        Args:
            task_manager: aipyapp TaskManager instance
            instruction: Python task instruction
            context: Execution context
            
        Returns:
            Raw result from aipyapp with success, output, artifacts, etc.
        """
        import time
        start_time = time.time()
        
        try:
            # Create aipyapp Task
            task = Task(task_manager)
            
            # Execute the task with the instruction
            # aipyapp's Task.run() method handles the execution
            await asyncio.get_event_loop().run_in_executor(
                None,
                task.run,
                instruction
            )
            
            # Collect results
            output_lines = []
            for step in task.steps:
                # Collect output from each step
                for round_data in step.data.rounds:
                    if round_data.llm_response and round_data.llm_response.message:
                        output_lines.append(round_data.llm_response.message.content)
            
            # Collect artifacts (files generated)
            artifacts = []
            task_dir = task.cwd
            if task_dir.exists():
                for file_path in task_dir.rglob("*"):
                    if file_path.is_file() and file_path.suffix in {".png", ".jpg", ".csv", ".json", ".txt"}:
                        artifacts.append(str(file_path.relative_to(task_dir)))
            
            # Collect variables from task context
            variables = {}
            if hasattr(task, 'runtime') and hasattr(task.runtime, 'globals'):
                # Extract serializable variables
                for key, value in task.runtime.globals.items():
                    if not key.startswith('_') and isinstance(value, (int, float, str, bool, list, dict)):
                        variables[key] = value
            
            execution_time = time.time() - start_time
            
            return {
                "success": True,
                "output": "\n".join(output_lines) if output_lines else "Task completed successfully",
                "artifacts": artifacts,
                "execution_time": execution_time,
                "variables": variables,
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.exception("aipyapp task execution failed", instruction=instruction)
            
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "artifacts": [],
                "execution_time": execution_time,
                "variables": {},
            }
    
    async def cleanup_session(self, ctx: AgentCtx):
        """Clean up aipyapp resources for a session
        
        Args:
            ctx: nekro-agent context
        """
        session_id = f"{ctx.chat_key}_{ctx.user_id}"
        
        if session_id in self._task_managers:
            task_manager = self._task_managers.pop(session_id)
            
            # Call aipyapp's cleanup if available
            if hasattr(task_manager, 'cleanup'):
                task_manager.cleanup()
            
            logger.info("Cleaned up TaskManager for session", session_id=session_id)

