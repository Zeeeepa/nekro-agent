"""Task Manager - Pool management for aipyapp instances

This module manages a pool of isolated aipyapp TaskManager instances,
ensuring proper resource allocation and session isolation.
"""

from typing import Dict, Optional
from pathlib import Path

from nekro_agent.core import logger


class AipyappTaskManager:
    """Manages pool of isolated aipyapp TaskManager instances
    
    Responsibilities:
    - Session-to-executor mapping
    - Resource cleanup and memory management
    - Session lifecycle management
    - Garbage collection of idle sessions
    
    This ensures each nekro-agent chat session gets its own
    isolated aipyapp environment with persistent state.
    """
    
    def __init__(
        self,
        workdir: Path,
        max_sessions: int = 100,
        session_timeout: int = 3600,
    ):
        """Initialize the task manager pool
        
        Args:
            workdir: Base directory for all aipyapp sessions
            max_sessions: Maximum concurrent sessions
            session_timeout: Idle timeout before session cleanup (seconds)
        """
        self.workdir = Path(workdir)
        self.workdir.mkdir(parents=True, exist_ok=True)
        
        self.max_sessions = max_sessions
        self.session_timeout = session_timeout
        
        # Active sessions: session_id -> TaskManager instance
        self._sessions: Dict[str, Dict] = {}
        
        logger.info(
            "AipyappTaskManager initialized",
            workdir=str(self.workdir),
            max_sessions=max_sessions,
        )
    
    def create_session(
        self,
        session_id: str,
        config: Optional[Dict] = None,
    ) -> None:
        """Create a new aipyapp session
        
        Args:
            session_id: Unique session identifier
            config: Optional session-specific configuration
        """
        if session_id in self._sessions:
            logger.warning(
                "Session already exists, reusing",
                session_id=session_id,
            )
            return
        
        if len(self._sessions) >= self.max_sessions:
            # Cleanup oldest idle session
            self._cleanup_oldest_session()
        
        # Create session workdir
        session_workdir = self.workdir / session_id
        session_workdir.mkdir(parents=True, exist_ok=True)
        
        # Store session metadata
        self._sessions[session_id] = {
            "workdir": session_workdir,
            "config": config or {},
            "task_manager": None,  # Will be lazily initialized
            "created_at": self._get_timestamp(),
            "last_accessed": self._get_timestamp(),
            "task_count": 0,
        }
        
        logger.info("Created aipyapp session", session_id=session_id)
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session metadata
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session metadata dictionary or None if not found
        """
        session = self._sessions.get(session_id)
        if session:
            session["last_accessed"] = self._get_timestamp()
        return session
    
    def cleanup_session(self, session_id: str) -> bool:
        """Clean up a specific session
        
        Args:
            session_id: Session to cleanup
            
        Returns:
            True if session was cleaned up, False if not found
        """
        session = self._sessions.pop(session_id, None)
        if not session:
            return False
        
        # Cleanup task manager if initialized
        if session.get("task_manager"):
            # TODO: Implement proper aipyapp TaskManager cleanup
            pass
        
        logger.info(
            "Cleaned up session",
            session_id=session_id,
            task_count=session.get("task_count", 0),
        )
        return True
    
    def cleanup_idle_sessions(self) -> int:
        """Clean up sessions that have been idle too long
        
        Returns:
            Number of sessions cleaned up
        """
        current_time = self._get_timestamp()
        idle_sessions = [
            session_id
            for session_id, session in self._sessions.items()
            if current_time - session["last_accessed"] > self.session_timeout
        ]
        
        for session_id in idle_sessions:
            self.cleanup_session(session_id)
        
        if idle_sessions:
            logger.info(
                f"Cleaned up {len(idle_sessions)} idle sessions",
                count=len(idle_sessions),
            )
        
        return len(idle_sessions)
    
    def _cleanup_oldest_session(self) -> None:
        """Cleanup the oldest idle session to make room"""
        if not self._sessions:
            return
        
        # Find oldest by last_accessed
        oldest_id = min(
            self._sessions.keys(),
            key=lambda sid: self._sessions[sid]["last_accessed"],
        )
        
        self.cleanup_session(oldest_id)
        logger.info(
            "Cleaned up oldest session to make room",
            session_id=oldest_id,
        )
    
    def get_stats(self) -> Dict:
        """Get pool statistics
        
        Returns:
            Statistics dictionary
        """
        return {
            "active_sessions": len(self._sessions),
            "max_sessions": self.max_sessions,
            "total_tasks": sum(
                s["task_count"] for s in self._sessions.values()
            ),
        }
    
    @staticmethod
    def _get_timestamp() -> float:
        """Get current timestamp"""
        import time
        return time.time()

