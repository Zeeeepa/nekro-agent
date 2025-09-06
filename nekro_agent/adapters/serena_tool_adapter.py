"""
Serena Tool Adapter Framework

This module provides an adapter layer to integrate Serena's tools with NekroAgent's plugin system.
It bridges the architectural differences between the two systems while preserving Serena's tool functionality.
"""

import asyncio
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from nekro_agent.api.plugin import NekroPlugin, SandboxMethodType
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.core.logger import logger
from nekro_agent.services.lsp_service import lsp_service


class MockSerenaAgent:
    """Mock Serena agent for tool compatibility"""

    def __init__(self, project_root: str, workspace_id: Optional[str] = None):
        self.project_root = project_root
        self.workspace_id = workspace_id
        self.memories = {}

    def get_project_root(self) -> str:
        return self.project_root

    def get_active_project_or_raise(self):
        return MockProject(self.project_root)

    def is_using_language_server(self) -> bool:
        return True

    @property
    def language_server(self):
        return lsp_service

    @property
    def memories_manager(self):
        return MockMemoriesManager(self.memories)


class MockProject:
    """Mock Serena project for tool compatibility"""

    def __init__(self, project_root: str):
        self.project_root = project_root

    def validate_relative_path(self, relative_path: str):
        """Validate that the path is within the project"""
        abs_path = (Path(self.project_root) / relative_path).resolve()
        project_root_abs = Path(self.project_root).resolve()
        if not str(abs_path).startswith(str(project_root_abs)):
            raise ValueError(f"Path {relative_path} is outside project root")

    def relative_path_exists(self, relative_path: str) -> bool:
        """Check if relative path exists"""
        full_path = os.path.join(self.project_root, relative_path)
        return os.path.exists(full_path)

    def read_file(self, relative_path: str) -> str:
        """Read file content"""
        full_path = os.path.join(self.project_root, relative_path)
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()

    def is_ignored_path(self, path: str) -> bool:
        """Check if path should be ignored (simplified)"""
        ignored_patterns = [".git", "__pycache__", ".pyc", "node_modules", ".DS_Store"]
        return any(pattern in path for pattern in ignored_patterns)

    def retrieve_content_around_line(
        self,
        relative_file_path: str,
        line: int,
        context_lines_before: int = 1,
        context_lines_after: int = 1,
    ):
        """Retrieve content around a specific line"""
        content = self.read_file(relative_file_path)
        lines = content.splitlines()

        start_line = max(0, line - context_lines_before)
        end_line = min(len(lines), line + context_lines_after + 1)

        context_lines = lines[start_line:end_line]

        return MockContentAroundLine(context_lines, start_line, line)


class MockContentAroundLine:
    """Mock content around line for tool compatibility"""

    def __init__(self, lines: List[str], start_line: int, target_line: int):
        self.lines = lines
        self.start_line = start_line
        self.target_line = target_line

    def to_display_string(self) -> str:
        """Convert to display string"""
        result = []
        for i, line in enumerate(self.lines):
            line_num = self.start_line + i
            marker = ">>>" if line_num == self.target_line else "   "
            result.append(f"{marker} {line_num + 1}: {line}")
        return "\n".join(result)


class MockMemoriesManager:
    """Mock memories manager for tool compatibility"""

    def __init__(self, memories: Dict[str, str]):
        self.memories = memories

    def save_memory(self, name: str, content: str) -> str:
        """Save memory content"""
        self.memories[name] = content
        return f"Memory '{name}' saved successfully"

    def load_memory(self, name: str) -> str:
        """Load memory content"""
        if name not in self.memories:
            raise KeyError(f"Memory '{name}' not found")
        return self.memories[name]

    def list_memories(self) -> List[str]:
        """List available memories"""
        return list(self.memories.keys())

    def delete_memory(self, name: str) -> str:
        """Delete memory"""
        if name not in self.memories:
            raise KeyError(f"Memory '{name}' not found")
        del self.memories[name]
        return f"Memory '{name}' deleted successfully"


class SerenaToolAdapter:
    """
    Base adapter class for Serena tools.

    This class provides the bridge between Serena's tool architecture and NekroAgent's plugin system.
    """

    def __init__(
        self,
        tool_class: Type,
        project_root: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ):
        self.tool_class = tool_class
        self.project_root = project_root or os.getcwd()
        self.workspace_id = workspace_id
        self._tool_instance = None

    def get_tool_instance(self):
        """Get or create tool instance"""
        if self._tool_instance is None:
            mock_agent = MockSerenaAgent(self.project_root, self.workspace_id)
            self._tool_instance = self.tool_class(mock_agent)
        return self._tool_instance

    def get_tool_name(self) -> str:
        """Get the tool name"""
        return self.tool_class.get_name_from_cls()

    def get_tool_description(self) -> str:
        """Get the tool description"""
        return self.tool_class.get_tool_description()

    def get_apply_docstring(self) -> str:
        """Get the apply method docstring"""
        return self.tool_class.get_apply_docstring_from_cls()

    def can_edit(self) -> bool:
        """Check if tool can edit files"""
        return self.tool_class.can_edit()

    async def apply(self, *args, **kwargs) -> str:
        """Apply the tool with given arguments"""
        try:
            tool_instance = self.get_tool_instance()
            return tool_instance.apply(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error applying {self.get_tool_name()}: {e}")
            return f"Error: {e!s}"

    def _limit_length(self, content: str, max_chars: int = -1) -> str:
        """Limit content length (mimics Serena's behavior)"""
        if max_chars == -1:
            max_chars = 50000  # Default limit
        if len(content) > max_chars:
            return f"Content too long ({len(content)} chars > {max_chars} limit). Please use more specific parameters."
        return content


class SerenaToolRegistry:
    """
    Registry for managing Serena tool adapters.

    This class maintains a registry of available Serena tools and provides
    methods to create and manage tool adapters.
    """

    def __init__(self):
        self._tools: Dict[str, Type] = {}
        self._adapters: Dict[str, SerenaToolAdapter] = {}

    def register_tool(self, tool_class: Type):
        """Register a Serena tool class"""
        tool_name = tool_class.get_name_from_cls()
        self._tools[tool_name] = tool_class
        logger.info(f"Registered Serena tool: {tool_name}")

    def get_tool_adapter(
        self,
        tool_name: str,
        project_root: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> SerenaToolAdapter:
        """Get or create a tool adapter"""
        if tool_name not in self._tools:
            raise ValueError(f"Tool '{tool_name}' not registered")

        adapter_key = f"{tool_name}:{project_root}:{workspace_id}"
        if adapter_key not in self._adapters:
            tool_class = self._tools[tool_name]
            self._adapters[adapter_key] = SerenaToolAdapter(
                tool_class,
                project_root,
                workspace_id,
            )

        return self._adapters[adapter_key]

    def list_tools(self) -> List[str]:
        """List all registered tools"""
        return list(self._tools.keys())

    def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """Get information about a tool"""
        if tool_name not in self._tools:
            raise ValueError(f"Tool '{tool_name}' not registered")

        tool_class = self._tools[tool_name]
        return {
            "name": tool_name,
            "description": tool_class.get_tool_description(),
            "can_edit": tool_class.can_edit(),
            "docstring": tool_class.get_apply_docstring_from_cls(),
        }

    def get_all_tools_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all registered tools"""
        return {name: self.get_tool_info(name) for name in self._tools}


# Global registry instance
serena_tool_registry = SerenaToolRegistry()


def create_nekro_plugin_from_serena_tools(
    plugin_name: str,
    module_name: str,
    description: str,
    tool_classes: List[Type],
    version: str = "1.0.0",
    author: str = "NekroAgent Team",
) -> NekroPlugin:
    """
    Create a NekroAgent plugin from Serena tool classes.

    This function automatically generates a NekroAgent plugin that exposes
    Serena tools as sandbox methods for AI agents.
    """

    # Register all tools
    for tool_class in tool_classes:
        serena_tool_registry.register_tool(tool_class)

    # Create the plugin
    plugin = NekroPlugin(
        name=plugin_name,
        module_name=module_name,
        description=description,
        version=version,
        author=author,
        support_adapter=["onebot_v11", "minecraft", "sse", "discord", "wechatpad"],
    )

    # Create sandbox methods for each tool
    for tool_class in tool_classes:
        tool_name = tool_class.get_name_from_cls()
        tool_description = tool_class.get_tool_description()
        apply_docstring = tool_class.get_apply_docstring_from_cls()
        can_edit = tool_class.can_edit()

        # Determine sandbox method type
        method_type = SandboxMethodType.TOOL
        if can_edit:
            method_type = SandboxMethodType.AGENT

        # Create the sandbox method
        async def create_tool_method(tool_cls=tool_class):
            async def tool_method(*args, _ctx: AgentCtx = None, **kwargs) -> str:
                try:
                    # Get current working directory as project root
                    project_root = os.getcwd()

                    # Create adapter and apply tool
                    adapter = serena_tool_registry.get_tool_adapter(
                        tool_cls.get_name_from_cls(),
                        project_root=project_root,
                    )

                    return await adapter.apply(*args, **kwargs)

                except Exception as e:
                    logger.error(f"Error in {tool_cls.get_name_from_cls()}: {e}")
                    return f"❌ Error: {e!s}"

            # Set function metadata
            tool_method.__name__ = tool_name
            tool_method.__doc__ = f"{tool_description}\n\n{apply_docstring}"

            return tool_method

        # Mount the method to the plugin
        tool_method = asyncio.run(create_tool_method())
        plugin.mount_sandbox_method(method_type, tool_name)(tool_method)

    return plugin


# Utility functions for working with file paths in sandbox
def get_sandbox_project_root() -> str:
    """Get the current project root in sandbox environment"""
    return os.getcwd()


def resolve_relative_path(
    relative_path: str, project_root: Optional[str] = None,
) -> str:
    """Resolve relative path within project root"""
    if project_root is None:
        project_root = get_sandbox_project_root()

    abs_path = os.path.abspath(os.path.join(project_root, relative_path))
    if not abs_path.startswith(os.path.abspath(project_root)):
        raise ValueError(f"Path {relative_path} is outside project root")

    return abs_path


def ensure_directory_exists(file_path: str):
    """Ensure directory exists for file path"""
    directory = os.path.dirname(file_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
