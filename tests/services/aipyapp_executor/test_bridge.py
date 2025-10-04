"""Tests for AipyappBridge - Context translation layer"""

import pytest
from nekro_agent.schemas.agent_ctx import AgentCtx
from nekro_agent.services.aipyapp_executor.bridge import AipyappBridge


class TestAipyappBridge:
    """Test suite for context translation between nekro-agent and aipyapp"""
    
    def test_create_aipyapp_context_basic(self):
        """Test basic context creation from AgentCtx"""
        # Arrange
        ctx = AgentCtx(
            chat_key="test_chat_123",
            user_id="user_456",
            platform_type="qq",
            bot_id="bot_789",
        )
        
        # Act
        result = AipyappBridge.create_aipyapp_context(ctx)
        
        # Assert
        assert result["chat_key"] == "test_chat_123"
        assert result["user_id"] == "user_456"
        assert result["platform_type"] == "qq"
        assert result["bot_id"] == "bot_789"
        assert result["created_by"] == "nekro-agent"
        assert result["orchestrator"] == "nekro-agent"
    
    def test_create_aipyapp_context_workdir_format(self):
        """Test workdir path format is correct"""
        # Arrange
        ctx = AgentCtx(chat_key="my_chat", user_id="user_1", platform_type="discord", bot_id="bot_1")
        
        # Act
        result = AipyappBridge.create_aipyapp_context(ctx)
        
        # Assert
        assert result["workdir"] == "/tmp/aipyapp_my_chat"
        assert result["session_id"] == "nekro_my_chat_user_1"
    
    def test_format_result_for_nekro_success(self):
        """Test successful result formatting"""
        # Arrange
        aipyapp_result = {
            "success": True,
            "output": "Calculation complete: 42",
            "artifacts": ["plot.png", "data.csv"],
            "execution_time": 2.5,
            "variables": {"result": 42, "count": 10},
        }
        
        # Act
        result = AipyappBridge.format_result_for_nekro(aipyapp_result)
        
        # Assert
        assert result["success"] is True
        assert result["output"] == "Calculation complete: 42"
        assert result["artifacts"] == ["plot.png", "data.csv"]
        assert result["execution_time"] == 2.5
        assert result["variables"] == {"result": 42, "count": 10}
        assert result["error"] is None
    
    def test_format_result_for_nekro_failure(self):
        """Test failure result formatting"""
        # Arrange
        aipyapp_result = {
            "success": False,
            "output": "",
            "error": "SyntaxError: invalid syntax",
            "artifacts": [],
            "execution_time": 0.1,
        }
        
        # Act
        result = AipyappBridge.format_result_for_nekro(aipyapp_result)
        
        # Assert
        assert result["success"] is False
        assert result["output"] == ""
        assert result["error"] == "SyntaxError: invalid syntax"
        assert result["artifacts"] == []
    
    def test_format_result_with_missing_fields(self):
        """Test result formatting handles missing fields gracefully"""
        # Arrange
        minimal_result = {"success": True}
        
        # Act
        result = AipyappBridge.format_result_for_nekro(minimal_result)
        
        # Assert
        assert result["success"] is True
        assert result["output"] == ""
        assert result["error"] is None
        assert result["artifacts"] == []
        assert result["execution_time"] == 0
        assert result["variables"] == {}
    
    def test_map_error_syntax_error(self):
        """Test error mapping for SyntaxError"""
        # Arrange
        error = SyntaxError("invalid syntax on line 5")
        
        # Act
        result = AipyappBridge.map_error(error)
        
        # Assert
        assert result["error_type"] == "SyntaxError"
        assert result["error_message"] == "invalid syntax on line 5"
        assert "Python syntax" in result["recovery_suggestion"]
    
    def test_map_error_timeout_error(self):
        """Test error mapping for TimeoutError"""
        # Arrange
        error = TimeoutError("Execution exceeded 300s")
        
        # Act
        result = AipyappBridge.map_error(error)
        
        # Assert
        assert result["error_type"] == "TimeoutError"
        assert "breaking into smaller tasks" in result["recovery_suggestion"]
    
    def test_map_error_memory_error(self):
        """Test error mapping for MemoryError"""
        # Arrange
        error = MemoryError("Out of memory")
        
        # Act
        result = AipyappBridge.map_error(error)
        
        # Assert
        assert result["error_type"] == "MemoryError"
        assert "optimize data processing" in result["recovery_suggestion"]
    
    def test_map_error_unknown_error_type(self):
        """Test error mapping for unknown error type"""
        # Arrange
        error = RuntimeError("Unknown error occurred")
        
        # Act
        result = AipyappBridge.map_error(error)
        
        # Assert
        assert result["error_type"] == "RuntimeError"
        assert result["error_message"] == "Unknown error occurred"
        assert "Review task requirements" in result["recovery_suggestion"]
    
    def test_map_error_module_not_found(self):
        """Test error mapping for ModuleNotFoundError"""
        # Arrange
        error = ModuleNotFoundError("No module named 'pandas'")
        
        # Act
        result = AipyappBridge.map_error(error)
        
        # Assert
        assert result["error_type"] == "ModuleNotFoundError"
        assert "not available in sandbox" in result["recovery_suggestion"]

