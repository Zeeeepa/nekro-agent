"""
LSP Caller for Sandbox Environment

This module provides LSP functionality within the sandbox environment,
allowing code execution containers to access LSP services.
"""

import asyncio
import json
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any

from nekro_agent.core.logger import logger
from nekro_agent.services.lsp_service import lsp_service


class SandboxLSPCaller:
    """
    LSP caller for sandbox environment.
    
    This class provides LSP functionality that can be used within
    the Docker sandbox for code analysis and manipulation.
    """
    
    def __init__(self):
        self._initialized = False
        self._sandbox_workspaces: Dict[str, str] = {}
    
    async def initialize(self) -> None:
        """Initialize the sandbox LSP caller."""
        if self._initialized:
            return
        
        try:
            # Initialize the main LSP service
            await lsp_service.initialize()
            self._initialized = True
            logger.info("Sandbox LSP caller initialized")
        except Exception as e:
            logger.error(f"Failed to initialize sandbox LSP caller: {e}")
            raise
    
    async def create_sandbox_workspace(
        self,
        workspace_path: str,
        language: str = "python"
    ) -> str:
        """
        Create a temporary LSP workspace for sandbox analysis.
        
        Args:
            workspace_path: Path to the workspace directory
            language: Programming language
            
        Returns:
            Workspace ID for the created workspace
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            # Generate unique workspace ID for sandbox
            workspace_id = f"sandbox_{abs(hash(workspace_path))}_{language}"
            
            # Create workspace in LSP service
            success = await lsp_service.create_workspace(
                workspace_id=workspace_id,
                workspace_path=workspace_path,
                language=language
            )
            
            if success:
                self._sandbox_workspaces[workspace_id] = workspace_path
                logger.info(f"Created sandbox workspace: {workspace_id}")
                return workspace_id
            else:
                raise Exception("Failed to create LSP workspace")
                
        except Exception as e:
            logger.error(f"Error creating sandbox workspace: {e}")
            raise
    
    async def analyze_code_file(
        self,
        file_path: str,
        language: str = "python"
    ) -> Dict[str, Any]:
        """
        Analyze a single code file.
        
        Args:
            file_path: Path to the code file
            language: Programming language
            
        Returns:
            Analysis results including diagnostics and symbols
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Create temporary workspace for the file's directory
            workspace_dir = os.path.dirname(file_path)
            workspace_id = await self.create_sandbox_workspace(workspace_dir, language)
            
            # Get diagnostics for the workspace
            diagnostics = await lsp_service.get_workspace_diagnostics(workspace_id)
            
            # Filter diagnostics for the specific file
            file_diagnostics = [
                d for d in diagnostics 
                if d.get("file") == file_path or os.path.basename(d.get("file", "")) == os.path.basename(file_path)
            ]
            
            return {
                "workspace_id": workspace_id,
                "file_path": file_path,
                "language": language,
                "diagnostics": file_diagnostics,
                "diagnostics_count": len(file_diagnostics),
                "error_count": sum(1 for d in file_diagnostics if d.get("severity") == "error"),
                "warning_count": sum(1 for d in file_diagnostics if d.get("severity") == "warning"),
            }
            
        except Exception as e:
            logger.error(f"Error analyzing code file: {e}")
            return {
                "error": str(e),
                "file_path": file_path,
                "diagnostics": [],
                "diagnostics_count": 0,
                "error_count": 0,
                "warning_count": 0,
            }
    
    async def find_symbol_in_code(
        self,
        workspace_path: str,
        symbol_name: str,
        language: str = "python"
    ) -> List[Dict[str, Any]]:
        """
        Find symbols in code workspace.
        
        Args:
            workspace_path: Path to the workspace
            symbol_name: Symbol name to search for
            language: Programming language
            
        Returns:
            List of symbol locations
        """
        try:
            # Create or get workspace
            workspace_id = await self.create_sandbox_workspace(workspace_path, language)
            
            # Find symbols
            symbols = await lsp_service.find_symbol(workspace_id, symbol_name)
            
            return symbols
            
        except Exception as e:
            logger.error(f"Error finding symbols: {e}")
            return []
    
    async def get_symbol_references_in_code(
        self,
        workspace_path: str,
        file_path: str,
        line: int,
        character: int,
        language: str = "python"
    ) -> List[Dict[str, Any]]:
        """
        Get symbol references in code.
        
        Args:
            workspace_path: Path to the workspace
            file_path: Path to the file
            line: Line number (0-based)
            character: Character position (0-based)
            language: Programming language
            
        Returns:
            List of reference locations
        """
        try:
            # Create or get workspace
            workspace_id = await self.create_sandbox_workspace(workspace_path, language)
            
            # Get references
            references = await lsp_service.get_symbol_references(
                workspace_id=workspace_id,
                file_path=file_path,
                line=line,
                character=character
            )
            
            return references
            
        except Exception as e:
            logger.error(f"Error getting symbol references: {e}")
            return []
    
    async def get_symbol_definition_in_code(
        self,
        workspace_path: str,
        file_path: str,
        line: int,
        character: int,
        language: str = "python"
    ) -> Optional[Dict[str, Any]]:
        """
        Get symbol definition in code.
        
        Args:
            workspace_path: Path to the workspace
            file_path: Path to the file
            line: Line number (0-based)
            character: Character position (0-based)
            language: Programming language
            
        Returns:
            Definition location or None
        """
        try:
            # Create or get workspace
            workspace_id = await self.create_sandbox_workspace(workspace_path, language)
            
            # Get definition
            definition = await lsp_service.get_symbol_definition(
                workspace_id=workspace_id,
                file_path=file_path,
                line=line,
                character=character
            )
            
            return definition
            
        except Exception as e:
            logger.error(f"Error getting symbol definition: {e}")
            return None
    
    async def analyze_code_quality(
        self,
        workspace_path: str,
        language: str = "python"
    ) -> Dict[str, Any]:
        """
        Perform comprehensive code quality analysis.
        
        Args:
            workspace_path: Path to the workspace
            language: Programming language
            
        Returns:
            Code quality analysis results
        """
        try:
            # Create or get workspace
            workspace_id = await self.create_sandbox_workspace(workspace_path, language)
            
            # Get all diagnostics
            diagnostics = await lsp_service.get_workspace_diagnostics(workspace_id)
            
            # Analyze diagnostics
            error_count = sum(1 for d in diagnostics if d.get("severity") == "error")
            warning_count = sum(1 for d in diagnostics if d.get("severity") == "warning")
            info_count = sum(1 for d in diagnostics if d.get("severity") == "info")
            hint_count = sum(1 for d in diagnostics if d.get("severity") == "hint")
            
            # Calculate quality score
            total_issues = len(diagnostics)
            if total_issues == 0:
                quality_score = 100
                quality_grade = "A+"
            elif error_count == 0 and warning_count <= 5:
                quality_score = 85
                quality_grade = "A"
            elif error_count <= 3:
                quality_score = 70
                quality_grade = "B"
            elif error_count <= 10:
                quality_score = 50
                quality_grade = "C"
            else:
                quality_score = 30
                quality_grade = "D"
            
            # Get file statistics
            files_with_issues = set()
            for diag in diagnostics:
                files_with_issues.add(diag.get("file", ""))
            
            return {
                "workspace_id": workspace_id,
                "workspace_path": workspace_path,
                "language": language,
                "quality_score": quality_score,
                "quality_grade": quality_grade,
                "total_issues": total_issues,
                "error_count": error_count,
                "warning_count": warning_count,
                "info_count": info_count,
                "hint_count": hint_count,
                "files_with_issues": len(files_with_issues),
                "diagnostics": diagnostics[:20],  # Limit to first 20 for performance
                "analysis_summary": self._generate_analysis_summary(
                    quality_grade, error_count, warning_count, total_issues
                )
            }
            
        except Exception as e:
            logger.error(f"Error analyzing code quality: {e}")
            return {
                "error": str(e),
                "workspace_path": workspace_path,
                "quality_score": 0,
                "quality_grade": "F",
                "total_issues": 0,
                "error_count": 0,
                "warning_count": 0,
                "diagnostics": []
            }
    
    def _generate_analysis_summary(
        self,
        grade: str,
        errors: int,
        warnings: int,
        total: int
    ) -> str:
        """Generate a human-readable analysis summary."""
        if total == 0:
            return "🟢 Excellent code quality! No issues found."
        elif grade == "A":
            return f"🟡 Good code quality with {warnings} warnings to address."
        elif grade == "B":
            return f"🟠 Moderate code quality. Fix {errors} errors and {warnings} warnings."
        elif grade == "C":
            return f"🔴 Poor code quality. {errors} errors need immediate attention."
        else:
            return f"🚨 Critical code quality issues. {errors} errors must be fixed urgently."
    
    async def cleanup_sandbox_workspaces(self) -> None:
        """Clean up temporary sandbox workspaces."""
        try:
            for workspace_id in list(self._sandbox_workspaces.keys()):
                try:
                    # Note: We don't actually delete the LSP workspace here
                    # as it might be used by other processes
                    del self._sandbox_workspaces[workspace_id]
                except Exception as e:
                    logger.warning(f"Error cleaning up workspace {workspace_id}: {e}")
            
            logger.info("Cleaned up sandbox workspaces")
            
        except Exception as e:
            logger.error(f"Error during sandbox cleanup: {e}")


# Global sandbox LSP caller instance
sandbox_lsp_caller = SandboxLSPCaller()


# Convenience functions for sandbox code execution
async def analyze_current_code(language: str = "python") -> Dict[str, Any]:
    """
    Analyze code in the current working directory.
    
    Args:
        language: Programming language
        
    Returns:
        Analysis results
    """
    current_dir = os.getcwd()
    return await sandbox_lsp_caller.analyze_code_quality(current_dir, language)


async def check_code_file(file_path: str, language: str = "python") -> Dict[str, Any]:
    """
    Check a specific code file for issues.
    
    Args:
        file_path: Path to the code file
        language: Programming language
        
    Returns:
        File analysis results
    """
    return await sandbox_lsp_caller.analyze_code_file(file_path, language)


async def find_code_symbol(symbol_name: str, language: str = "python") -> List[Dict[str, Any]]:
    """
    Find a symbol in the current workspace.
    
    Args:
        symbol_name: Symbol name to search for
        language: Programming language
        
    Returns:
        List of symbol locations
    """
    current_dir = os.getcwd()
    return await sandbox_lsp_caller.find_symbol_in_code(current_dir, symbol_name, language)


# Export functions for sandbox use
__all__ = [
    "SandboxLSPCaller",
    "sandbox_lsp_caller",
    "analyze_current_code",
    "check_code_file",
    "find_code_symbol"
]
