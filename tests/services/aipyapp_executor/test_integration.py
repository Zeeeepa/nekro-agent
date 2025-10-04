"""Integration tests for aipyapp executor system

These tests verify the complete flow from nekro-agent context
through to aipyapp execution and back.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from nekro_agent.schemas.agent_ctx import AgentCtx
from nekro_agent.services.aipyapp_executor import (
    AipyappSandboxExecutor,
    AipyappBridge,
    AipyappTaskManager,
)


@pytest.fixture
def mock_ctx():
    """Create mock AgentCtx"""
    return AgentCtx(
        chat_key="test_chat",
        user_id="test_user",
        platform_type="test",
        bot_id="test_bot",
    )


@pytest.fixture
def temp_workdir(tmp_path):
    """Create temporary workdir"""
    return tmp_path / "aipyapp_test"


class TestAipyappIntegration:
    """Integration tests for complete execution flow"""
    
    @pytest.mark.skipif(
        not hasattr(__import__("nekro_agent.services.aipyapp_executor.sandbox_executor", fromlist=["AIPYAPP_AVAILABLE"]), "AIPYAPP_AVAILABLE") or
        not __import__("nekro_agent.services.aipyapp_executor.sandbox_executor", fromlist=["AIPYAPP_AVAILABLE"]).AIPYAPP_AVAILABLE,
        reason="aipyapp not installed"
    )
    async def test_full_execution_flow_mock(self, mock_ctx, temp_workdir):
        """Test complete execution flow with mocked aipyapp"""
        # Arrange
        executor = AipyappSandboxExecutor(
            workdir=temp_workdir,
            timeout=30,
            max_memory_mb=256,
        )
        
        # Mock the aipyapp execution
        with patch.object(executor, '_execute_in_aipyapp', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = {
                "success": True,
                "output": "2 + 2 = 4",
                "artifacts": [],
                "execution_time": 0.5,
                "variables": {"result": 4},
            }
            
            # Act
            result = await executor.execute_task(
                ctx=mock_ctx,
                instruction="Calculate 2 + 2"
            )
            
            # Assert
            assert result["success"] is True
            assert "2 + 2 = 4" in result["output"]
            assert result["variables"]["result"] == 4
            assert result["execution_time"] == 0.5
    
    async def test_context_translation_flow(self, mock_ctx):
        """Test context translation from nekro to aipyapp"""
        # Arrange
        bridge = AipyappBridge()
        
        # Act
        aipyapp_context = bridge.create_aipyapp_context(mock_ctx)
        
        # Assert
        assert aipyapp_context["chat_key"] == "test_chat"
        assert aipyapp_context["user_id"] == "test_user"
        assert "nekro" in aipyapp_context["session_id"]
        assert aipyapp_context["created_by"] == "nekro-agent"
    
    async def test_error_propagation_flow(self, mock_ctx, temp_workdir):
        """Test error propagation through the system"""
        # Arrange
        executor = AipyappSandboxExecutor(
            workdir=temp_workdir,
            timeout=30,
        )
        
        # Mock aipyapp to raise error
        with patch.object(executor, '_execute_in_aipyapp', new_callable=AsyncMock) as mock_exec:
            mock_exec.side_effect = SyntaxError("invalid syntax on line 5")
            
            # Act & Assert
            with pytest.raises(Exception) as exc_info:
                await executor.execute_task(
                    ctx=mock_ctx,
                    instruction="Invalid Python code"
                )
            
            assert "syntax" in str(exc_info.value).lower()
    
    async def test_timeout_enforcement(self, mock_ctx, temp_workdir):
        """Test timeout is properly enforced"""
        # Arrange
        executor = AipyappSandboxExecutor(
            workdir=temp_workdir,
            timeout=1,  # 1 second timeout
        )
        
        # Mock slow execution
        async def slow_execution(*args, **kwargs):
            await asyncio.sleep(2)
            return {"success": True}
        
        with patch.object(executor, '_execute_in_aipyapp', new=slow_execution):
            # Act & Assert
            with pytest.raises(Exception) as exc_info:
                await executor.execute_task(
                    ctx=mock_ctx,
                    instruction="Slow task"
                )
            
            assert "timeout" in str(exc_info.value).lower()
    
    async def test_session_isolation(self, temp_workdir):
        """Test that different sessions are properly isolated"""
        # Arrange
        executor = AipyappSandboxExecutor(workdir=temp_workdir)
        
        ctx1 = AgentCtx(chat_key="chat1", user_id="user1", platform_type="test", bot_id="bot1")
        ctx2 = AgentCtx(chat_key="chat2", user_id="user2", platform_type="test", bot_id="bot2")
        
        # Mock execution
        with patch.object(executor, '_execute_in_aipyapp', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = {"success": True, "output": "", "artifacts": [], "execution_time": 0, "variables": {}}
            
            # Act - execute for both sessions
            await executor.execute_task(ctx1, "Task 1")
            await executor.execute_task(ctx2, "Task 2")
            
            # Assert - separate task managers created
            assert "chat1_user1" in executor._task_managers
            assert "chat2_user2" in executor._task_managers
            assert len(executor._task_managers) == 2
    
    async def test_session_cleanup(self, mock_ctx, temp_workdir):
        """Test session cleanup removes resources"""
        # Arrange
        executor = AipyappSandboxExecutor(workdir=temp_workdir)
        
        with patch.object(executor, '_execute_in_aipyapp', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = {"success": True, "output": "", "artifacts": [], "execution_time": 0, "variables": {}}
            
            # Act - create session
            await executor.execute_task(mock_ctx, "Test task")
            session_id = f"{mock_ctx.chat_key}_{mock_ctx.user_id}"
            assert session_id in executor._task_managers
            
            # Cleanup
            await executor.cleanup_session(mock_ctx)
            
            # Assert - session removed
            assert session_id not in executor._task_managers
    
    def test_bridge_and_task_manager_integration(self, temp_workdir):
        """Test bridge and task manager work together"""
        # Arrange
        bridge = AipyappBridge()
        task_manager = AipyappTaskManager(
            workdir=temp_workdir,
            max_sessions=10,
        )
        
        ctx = AgentCtx(chat_key="test", user_id="user1", platform_type="test", bot_id="bot1")
        
        # Act - create context and session
        aipyapp_ctx = bridge.create_aipyapp_context(ctx)
        session_id = aipyapp_ctx["session_id"]
        task_manager.create_session(session_id)
        
        # Assert
        assert task_manager.get_session(session_id) is not None
        stats = task_manager.get_stats()
        assert stats["active_sessions"] == 1
    
    async def test_result_formatting_flow(self, mock_ctx, temp_workdir):
        """Test result flows through formatting correctly"""
        # Arrange
        executor = AipyappSandboxExecutor(workdir=temp_workdir)
        
        raw_result = {
            "success": True,
            "output": "Processed data",
            "artifacts": ["output.csv", "plot.png"],
            "execution_time": 2.5,
            "variables": {"count": 100, "mean": 42.5},
        }
        
        # Mock execution
        with patch.object(executor, '_execute_in_aipyapp', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = raw_result
            
            # Act
            result = await executor.execute_task(mock_ctx, "Process data")
            
            # Assert - result properly formatted
            assert result["success"] is True
            assert result["output"] == "Processed data"
            assert len(result["artifacts"]) == 2
            assert result["execution_time"] == 2.5
            assert result["variables"]["count"] == 100


# Import asyncio for timeout test
import asyncio

