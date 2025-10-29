"""Bridge Layer - Translation between nekro-agent and aipyapp contexts

This module handles context translation, ensuring clean separation between
nekro-agent's orchestration layer and aipyapp's execution layer.
"""

from typing import Any, Dict, Optional

from nekro_agent.schemas.agent_ctx import AgentCtx


class AipyappBridge:
    """Translates between nekro-agent AgentCtx and aipyapp Task context
    
    This bridge ensures:
    - Clean separation of concerns
    - Context isolation per chat session
    - Proper error mapping between systems
    - Format translation for results
    """
    
    @staticmethod
    def create_aipyapp_context(ctx: AgentCtx) -> Dict[str, Any]:
        """Convert nekro-agent AgentCtx to aipyapp-compatible context
        
        Args:
            ctx: nekro-agent execution context
            
        Returns:
            Dictionary with aipyapp-compatible context data
        """
        return {
            # Session identification
            "chat_key": ctx.chat_key,
            "user_id": ctx.user_id,
            "platform_type": ctx.platform_type,
            "bot_id": ctx.bot_id,
            
            # Execution environment
            "workdir": f"/tmp/aipyapp_{ctx.chat_key}",
            "session_id": f"nekro_{ctx.chat_key}_{ctx.user_id}",
            
            # Metadata
            "created_by": "nekro-agent",
            "orchestrator": "nekro-agent",
        }
    
    @staticmethod
    def format_result_for_nekro(result: Dict[str, Any]) -> Dict[str, Any]:
        """Format aipyapp execution result for nekro-agent consumption
        
        Args:
            result: Raw result from aipyapp execution
            
        Returns:
            Formatted result with standard nekro-agent structure
        """
        return {
            "success": result.get("success", False),
            "output": result.get("output", ""),
            "error": result.get("error"),
            "artifacts": result.get("artifacts", []),
            "execution_time": result.get("execution_time", 0),
            "variables": result.get("variables", {}),
        }
    
    @staticmethod
    def map_error(aipyapp_error: Exception) -> Dict[str, Any]:
        """Map aipyapp errors to nekro-agent error format
        
        Args:
            aipyapp_error: Exception from aipyapp execution
            
        Returns:
            Standardized error dictionary
        """
        error_type = type(aipyapp_error).__name__
        error_message = str(aipyapp_error)
        
        return {
            "error_type": error_type,
            "error_message": error_message,
            "recovery_suggestion": _get_recovery_suggestion(error_type),
        }


def _get_recovery_suggestion(error_type: str) -> str:
    """Provide recovery suggestions based on error type"""
    suggestions = {
        "SyntaxError": "Check Python syntax in the generated code",
        "TimeoutError": "Task exceeded time limit, consider breaking into smaller tasks",
        "MemoryError": "Task used too much memory, optimize data processing",
        "ModuleNotFoundError": "Required Python module not available in sandbox",
        "ValueError": "Invalid input data, check task parameters",
    }
    return suggestions.get(error_type, "Review task requirements and try again")

