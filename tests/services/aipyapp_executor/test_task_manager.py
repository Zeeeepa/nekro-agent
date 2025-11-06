"""Tests for AipyappTaskManager - Session pool management"""

import pytest
import time
from pathlib import Path
from nekro_agent.services.aipyapp_executor.task_manager import AipyappTaskManager


class TestAipyappTaskManager:
    """Test suite for aipyapp task manager pool"""
    
    @pytest.fixture
    def temp_workdir(self, tmp_path):
        """Create temporary workdir for tests"""
        return tmp_path / "aipyapp_test"
    
    @pytest.fixture
    def task_manager(self, temp_workdir):
        """Create task manager instance"""
        return AipyappTaskManager(
            workdir=temp_workdir,
            max_sessions=5,
            session_timeout=10,
        )
    
    def test_initialization(self, task_manager, temp_workdir):
        """Test task manager initializes correctly"""
        assert task_manager.workdir == temp_workdir
        assert task_manager.max_sessions == 5
        assert task_manager.session_timeout == 10
        assert len(task_manager._sessions) == 0
        assert temp_workdir.exists()
    
    def test_create_session_basic(self, task_manager):
        """Test basic session creation"""
        # Act
        task_manager.create_session("session_1")
        
        # Assert
        assert "session_1" in task_manager._sessions
        session = task_manager._sessions["session_1"]
        assert session["workdir"].exists()
        assert session["config"] == {}
        assert session["task_manager"] is None
        assert session["task_count"] == 0
        assert "created_at" in session
        assert "last_accessed" in session
    
    def test_create_session_with_config(self, task_manager):
        """Test session creation with custom config"""
        # Arrange
        config = {"timeout": 600, "allow_network": True}
        
        # Act
        task_manager.create_session("session_2", config=config)
        
        # Assert
        session = task_manager._sessions["session_2"]
        assert session["config"] == config
    
    def test_create_duplicate_session_reuses(self, task_manager, caplog):
        """Test creating duplicate session reuses existing"""
        # Arrange
        task_manager.create_session("session_1")
        
        # Act
        task_manager.create_session("session_1")
        
        # Assert
        assert len(task_manager._sessions) == 1
        assert "Session already exists, reusing" in caplog.text
    
    def test_get_session_updates_last_accessed(self, task_manager):
        """Test getting session updates last accessed time"""
        # Arrange
        task_manager.create_session("session_1")
        session = task_manager._sessions["session_1"]
        original_time = session["last_accessed"]
        time.sleep(0.1)
        
        # Act
        retrieved = task_manager.get_session("session_1")
        
        # Assert
        assert retrieved is not None
        assert retrieved["last_accessed"] > original_time
    
    def test_get_nonexistent_session(self, task_manager):
        """Test getting nonexistent session returns None"""
        result = task_manager.get_session("nonexistent")
        assert result is None
    
    def test_cleanup_session_success(self, task_manager):
        """Test successful session cleanup"""
        # Arrange
        task_manager.create_session("session_1")
        assert "session_1" in task_manager._sessions
        
        # Act
        result = task_manager.cleanup_session("session_1")
        
        # Assert
        assert result is True
        assert "session_1" not in task_manager._sessions
    
    def test_cleanup_nonexistent_session(self, task_manager):
        """Test cleanup of nonexistent session"""
        result = task_manager.cleanup_session("nonexistent")
        assert result is False
    
    def test_max_sessions_limit(self, task_manager):
        """Test max sessions limit enforcement"""
        # Arrange - create max sessions
        for i in range(5):
            task_manager.create_session(f"session_{i}")
        
        assert len(task_manager._sessions) == 5
        
        # Act - create one more session
        time.sleep(0.1)  # Ensure different timestamps
        task_manager.create_session("session_6")
        
        # Assert - oldest session removed
        assert len(task_manager._sessions) == 5
        assert "session_6" in task_manager._sessions
        assert "session_0" not in task_manager._sessions
    
    def test_cleanup_idle_sessions(self, task_manager):
        """Test cleanup of idle sessions"""
        # Arrange - create sessions with old timestamps
        task_manager.create_session("session_1")
        task_manager.create_session("session_2")
        
        # Manually set old timestamp for session_1
        task_manager._sessions["session_1"]["last_accessed"] = time.time() - 20
        
        # Act
        cleaned = task_manager.cleanup_idle_sessions()
        
        # Assert
        assert cleaned == 1
        assert "session_1" not in task_manager._sessions
        assert "session_2" in task_manager._sessions
    
    def test_cleanup_idle_sessions_none_idle(self, task_manager):
        """Test cleanup when no sessions are idle"""
        # Arrange
        task_manager.create_session("session_1")
        task_manager.create_session("session_2")
        
        # Act
        cleaned = task_manager.cleanup_idle_sessions()
        
        # Assert
        assert cleaned == 0
        assert len(task_manager._sessions) == 2
    
    def test_get_stats_basic(self, task_manager):
        """Test getting pool statistics"""
        # Arrange
        task_manager.create_session("session_1")
        task_manager.create_session("session_2")
        task_manager._sessions["session_1"]["task_count"] = 5
        task_manager._sessions["session_2"]["task_count"] = 3
        
        # Act
        stats = task_manager.get_stats()
        
        # Assert
        assert stats["active_sessions"] == 2
        assert stats["max_sessions"] == 5
        assert stats["total_tasks"] == 8
    
    def test_get_stats_empty(self, task_manager):
        """Test getting stats with no sessions"""
        stats = task_manager.get_stats()
        
        assert stats["active_sessions"] == 0
        assert stats["max_sessions"] == 5
        assert stats["total_tasks"] == 0
    
    def test_cleanup_oldest_session(self, task_manager):
        """Test cleanup of oldest session when at capacity"""
        # Arrange - create sessions with different timestamps
        for i in range(5):
            task_manager.create_session(f"session_{i}")
            time.sleep(0.01)  # Ensure different timestamps
        
        oldest_id = min(
            task_manager._sessions.keys(),
            key=lambda sid: task_manager._sessions[sid]["last_accessed"],
        )
        
        # Act - trigger cleanup by adding new session
        task_manager.create_session("session_new")
        
        # Assert - oldest removed
        assert oldest_id not in task_manager._sessions
        assert "session_new" in task_manager._sessions
        assert len(task_manager._sessions) == 5

