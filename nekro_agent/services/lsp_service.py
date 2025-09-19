"""
LSP Service for NekroAgent

This service provides Language Server Protocol integration for NekroAgent,
enabling advanced code analysis, diagnostics, and manipulation capabilities.
"""

import asyncio
import logging
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

from nekro_agent.core.config import config
from nekro_agent.core.logger import logger
from nekro_agent.services.solidlsp.ls import SolidLanguageServer
from nekro_agent.services.solidlsp.ls_config import Language, LanguageServerConfig
from nekro_agent.services.solidlsp.ls_exceptions import SolidLSPException
from nekro_agent.services.solidlsp.ls_types import UnifiedSymbolInformation, Location, Position, Range
from nekro_agent.services.solidlsp.settings import SolidLSPSettings


class LSPService:
    """
    Service for managing Language Server Protocol operations in NekroAgent.
    
    This service provides high-level interfaces for:
    - Workspace management
    - Code analysis and diagnostics
    - Symbol search and navigation
    - Code manipulation and refactoring
    """
    
    def __init__(self):
        self._language_servers: Dict[str, SolidLanguageServer] = {}
        self._workspaces: Dict[str, str] = {}  # workspace_id -> path
        self._settings = SolidLSPSettings()
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the LSP service."""
        if self._initialized:
            return
            
        try:
            # Set up LSP settings
            self._settings.cache_dir = str(Path(config.DATA_DIR) / "lsp_cache")
            self._settings.log_level = logging.INFO
            
            # Create cache directory
            os.makedirs(self._settings.cache_dir, exist_ok=True)
            
            self._initialized = True
            logger.info("LSP Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize LSP Service: {e}")
            raise
    
    async def create_workspace(self, workspace_id: str, workspace_path: str, language: str = "python") -> bool:
        """
        Create a new LSP workspace.
        
        Args:
            workspace_id: Unique identifier for the workspace
            workspace_path: Path to the workspace directory
            language: Programming language for the workspace
            
        Returns:
            True if workspace was created successfully
        """
        try:
            if not os.path.exists(workspace_path):
                raise ValueError(f"Workspace path does not exist: {workspace_path}")
            
            # Store workspace info
            self._workspaces[workspace_id] = workspace_path
            
            # Initialize language server for this workspace
            await self._get_or_create_language_server(workspace_path, language)
            
            logger.info(f"Created LSP workspace: {workspace_id} at {workspace_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create workspace {workspace_id}: {e}")
            return False
    
    async def get_workspace_diagnostics(self, workspace_id: str) -> List[Dict[str, Any]]:
        """
        Get diagnostics for all files in a workspace.
        
        Args:
            workspace_id: Workspace identifier
            
        Returns:
            List of diagnostic information
        """
        try:
            workspace_path = self._workspaces.get(workspace_id)
            if not workspace_path:
                raise ValueError(f"Workspace not found: {workspace_id}")
            
            language_server = await self._get_language_server_for_workspace(workspace_id)
            if not language_server:
                return []
            
            diagnostics = []
            
            # Get all Python files in workspace (extend for other languages)
            for file_path in Path(workspace_path).rglob("*.py"):
                try:
                    file_diagnostics = await self._get_file_diagnostics(language_server, str(file_path))
                    if file_diagnostics:
                        diagnostics.extend(file_diagnostics)
                except Exception as e:
                    logger.warning(f"Failed to get diagnostics for {file_path}: {e}")
            
            return diagnostics
            
        except Exception as e:
            logger.error(f"Failed to get workspace diagnostics: {e}")
            return []
    
    async def find_symbol(self, workspace_id: str, symbol_name: str) -> List[Dict[str, Any]]:
        """
        Find symbol definitions and references in workspace.
        
        Args:
            workspace_id: Workspace identifier
            symbol_name: Name of the symbol to find
            
        Returns:
            List of symbol locations
        """
        try:
            language_server = await self._get_language_server_for_workspace(workspace_id)
            if not language_server:
                return []
            
            # Use LSP workspace symbol search
            symbols = await language_server.workspace_symbols(symbol_name)
            
            result = []
            for symbol in symbols:
                result.append({
                    "name": symbol.name,
                    "kind": symbol.kind.name if hasattr(symbol.kind, 'name') else str(symbol.kind),
                    "location": {
                        "uri": symbol.location.uri,
                        "path": symbol.location.absolutePath,
                        "range": {
                            "start": {
                                "line": symbol.location.range.start.line,
                                "character": symbol.location.range.start.character
                            },
                            "end": {
                                "line": symbol.location.range.end.line,
                                "character": symbol.location.range.end.character
                            }
                        }
                    }
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to find symbol {symbol_name}: {e}")
            return []
    
    async def get_symbol_references(self, workspace_id: str, file_path: str, line: int, character: int) -> List[Dict[str, Any]]:
        """
        Get references to a symbol at a specific location.
        
        Args:
            workspace_id: Workspace identifier
            file_path: Path to the file
            line: Line number (0-based)
            character: Character position (0-based)
            
        Returns:
            List of reference locations
        """
        try:
            language_server = await self._get_language_server_for_workspace(workspace_id)
            if not language_server:
                return []
            
            # Get references using LSP
            references = await language_server.references(file_path, line, character, include_declaration=True)
            
            result = []
            for ref in references:
                result.append({
                    "uri": ref.uri,
                    "path": ref.absolutePath,
                    "range": {
                        "start": {
                            "line": ref.range.start.line,
                            "character": ref.range.start.character
                        },
                        "end": {
                            "line": ref.range.end.line,
                            "character": ref.range.end.character
                        }
                    }
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get symbol references: {e}")
            return []
    
    async def get_symbol_definition(self, workspace_id: str, file_path: str, line: int, character: int) -> Optional[Dict[str, Any]]:
        """
        Get definition of a symbol at a specific location.
        
        Args:
            workspace_id: Workspace identifier
            file_path: Path to the file
            line: Line number (0-based)
            character: Character position (0-based)
            
        Returns:
            Definition location or None
        """
        try:
            language_server = await self._get_language_server_for_workspace(workspace_id)
            if not language_server:
                return None
            
            # Get definition using LSP
            definition = await language_server.definition(file_path, line, character)
            
            if definition and len(definition) > 0:
                def_location = definition[0]
                return {
                    "uri": def_location.uri,
                    "path": def_location.absolutePath,
                    "range": {
                        "start": {
                            "line": def_location.range.start.line,
                            "character": def_location.range.start.character
                        },
                        "end": {
                            "line": def_location.range.end.line,
                            "character": def_location.range.end.character
                        }
                    }
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get symbol definition: {e}")
            return None
    
    async def _get_or_create_language_server(self, workspace_path: str, language: str) -> Optional[SolidLanguageServer]:
        """Get or create a language server for the given workspace and language."""
        try:
            server_key = f"{workspace_path}:{language}"
            
            if server_key not in self._language_servers:
                # Create language server configuration
                lang_config = Language.from_string(language)
                ls_config = LanguageServerConfig.create(lang_config, workspace_path, self._settings)
                
                # Create and initialize language server
                language_server = ls_config.create_server_instance()
                await language_server.start()
                
                self._language_servers[server_key] = language_server
                logger.info(f"Created language server for {language} in {workspace_path}")
            
            return self._language_servers[server_key]
            
        except Exception as e:
            logger.error(f"Failed to create language server: {e}")
            return None
    
    async def _get_language_server_for_workspace(self, workspace_id: str) -> Optional[SolidLanguageServer]:
        """Get the language server for a workspace."""
        workspace_path = self._workspaces.get(workspace_id)
        if not workspace_path:
            return None
        
        # For now, assume Python - extend this to detect language
        return await self._get_or_create_language_server(workspace_path, "python")
    
    async def _get_file_diagnostics(self, language_server: SolidLanguageServer, file_path: str) -> List[Dict[str, Any]]:
        """Get diagnostics for a specific file."""
        try:
            # Open the file in the language server
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            await language_server.open_file(file_path, content)
            
            # Get diagnostics
            diagnostics = await language_server.get_diagnostics(file_path)
            
            result = []
            for diagnostic in diagnostics:
                result.append({
                    "file": file_path,
                    "severity": diagnostic.severity.name if hasattr(diagnostic.severity, 'name') else str(diagnostic.severity),
                    "message": diagnostic.message,
                    "range": {
                        "start": {
                            "line": diagnostic.range.start.line,
                            "character": diagnostic.range.start.character
                        },
                        "end": {
                            "line": diagnostic.range.end.line,
                            "character": diagnostic.range.end.character
                        }
                    },
                    "source": getattr(diagnostic, 'source', 'lsp')
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get file diagnostics: {e}")
            return []
    
    async def cleanup(self) -> None:
        """Clean up LSP service resources."""
        try:
            # Stop all language servers
            for server in self._language_servers.values():
                try:
                    await server.stop()
                except Exception as e:
                    logger.warning(f"Error stopping language server: {e}")
            
            self._language_servers.clear()
            self._workspaces.clear()
            self._initialized = False
            
            logger.info("LSP Service cleaned up successfully")
            
        except Exception as e:
            logger.error(f"Error during LSP Service cleanup: {e}")


# Global LSP service instance
lsp_service = LSPService()
