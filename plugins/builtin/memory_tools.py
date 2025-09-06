"""
# Memory Management Tools Plugin

Provides project-specific memory management for AI agents, adapted from Serena's memory system.
These tools enable persistent knowledge storage and retrieval across sessions.

## 主要功能

- **项目记忆存储**: 保存项目特定的知识和信息
- **智能记忆检索**: 按名称、类型、标签搜索记忆
- **记忆分类管理**: 支持类型和标签分类
- **记忆统计分析**: 提供记忆使用统计和分析
- **全文搜索**: 在记忆内容中进行全文搜索

## Agent 可用工具 (Sandbox Methods)

### 记忆操作工具
- **write_memory**: 保存或更新项目记忆
- **read_memory**: 读取指定的项目记忆
- **list_memories**: 列出项目的所有记忆
- **delete_memory**: 删除指定的项目记忆

### 记忆搜索工具
- **search_memories**: 在记忆内容中搜索
- **get_memory_stats**: 获取记忆统计信息
- **get_memories_by_type**: 按类型获取记忆
- **get_memories_by_tags**: 按标签获取记忆
"""

import json
import os

# Import Serena memory tools
import sys
from typing import Any, Dict, List, Optional

from pydantic import Field

from nekro_agent.api.plugin import ConfigBase, NekroPlugin, SandboxMethodType
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.core.logger import logger
from nekro_agent.services.memory_service import memory_service

sys.path.append("serena/src")

from nekro_agent.adapters.serena_tool_adapter import (
    create_nekro_plugin_from_serena_tools,
    get_sandbox_project_root,
)
from serena.tools.memory_tools import (
    DeleteMemoryTool,
    ListMemoriesTool,
    ReadMemoryTool,
    WriteMemoryTool,
)

# Create the plugin using the adapter framework
plugin = create_nekro_plugin_from_serena_tools(
    plugin_name="项目记忆管理工具",
    module_name="memory_tools",
    description="提供项目特定的记忆管理功能，支持知识存储、检索和分析",
    tool_classes=[
        WriteMemoryTool,
        ReadMemoryTool,
        ListMemoriesTool,
        DeleteMemoryTool,
    ],
    version="1.0.0",
)


@plugin.mount_config()
class MemoryToolsConfig(ConfigBase):
    """记忆工具配置"""

    DEFAULT_PROJECT_ID: str = Field(
        default="default",
        title="默认项目ID",
        description="当未指定项目ID时使用的默认值",
    )

    MAX_MEMORY_SIZE: int = Field(
        default=100000,  # 100KB
        title="最大记忆大小",
        description="单个记忆内容的最大字符数",
    )

    MAX_MEMORIES_PER_PROJECT: int = Field(
        default=1000,
        title="每个项目最大记忆数",
        description="单个项目可以存储的最大记忆数量",
    )

    DEFAULT_MEMORY_TYPES: List[str] = Field(
        default=[
            "general",
            "onboarding",
            "task",
            "code_analysis",
            "architecture",
            "bug_fix",
            "feature",
            "documentation",
        ],
        title="默认记忆类型",
        description="可用的记忆类型列表",
    )

    ENABLE_AUTO_TAGGING: bool = Field(
        default=True,
        title="启用自动标签",
        description="是否自动从内容中提取标签",
    )


# ========================================================================================
# |                           增强的记忆管理工具                                          |
# ========================================================================================


@plugin.mount_sandbox_method(SandboxMethodType.AGENT, "write_memory_enhanced")
async def write_memory_enhanced(
    memory_name: str,
    content: str,
    memory_type: str = "general",
    tags: Optional[List[str]] = None,
    priority: int = 0,
    project_id: Optional[str] = None,
    _ctx: Optional[AgentCtx] = None,
) -> str:
    """保存或更新项目记忆（增强版）

    Args:
        memory_name (str): 记忆名称/键
        content (str): 记忆内容（Markdown格式）
        memory_type (str): 记忆类型（general, onboarding, task等）
        tags (List[str]): 标签列表
        priority (int): 优先级（数字越大优先级越高）
        project_id (str): 项目ID，默认使用当前项目

    Returns:
        str: 操作结果

    Example:
        write_memory_enhanced("api_design", "# API设计原则\\n\\n1. RESTful设计...", "architecture", ["api", "design"], 5)
    """
    try:
        config = plugin.get_config()

        # Validate content size
        if len(content) > config.MAX_MEMORY_SIZE:
            return f"❌ 记忆内容过大（{len(content)} 字符 > {config.MAX_MEMORY_SIZE} 限制）"

        # Use project root as project ID if not specified
        if not project_id:
            project_root = get_sandbox_project_root()
            project_id = os.path.basename(project_root) or config.DEFAULT_PROJECT_ID

        # Auto-extract tags if enabled
        if config.ENABLE_AUTO_TAGGING and not tags:
            tags = _extract_auto_tags(content)

        tags = tags or []

        # Validate memory type
        if memory_type not in config.DEFAULT_MEMORY_TYPES:
            logger.warning(f"Unknown memory type: {memory_type}")

        # Check memory count limit
        existing_memories = await memory_service.list_memories(project_id)
        if len(existing_memories) >= config.MAX_MEMORIES_PER_PROJECT:
            return f"❌ 项目记忆数量已达上限（{config.MAX_MEMORIES_PER_PROJECT}）"

        # Save memory
        result = await memory_service.save_memory(
            project_id=project_id,
            memory_name=memory_name,
            content=content,
            memory_type=memory_type,
            tags=tags,
            priority=priority,
            created_by=_ctx.user_id if _ctx else None,
        )

        return f"✅ {result}"

    except Exception as e:
        logger.error(f"Error in write_memory_enhanced: {e}")
        return f"❌ 保存记忆失败: {e!s}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "search_memories")
async def search_memories(
    query: str,
    memory_type: Optional[str] = None,
    tags: Optional[List[str]] = None,
    limit: int = 20,
    project_id: Optional[str] = None,
    _ctx: Optional[AgentCtx] = None,
) -> str:
    """在项目记忆中搜索内容

    Args:
        query (str): 搜索查询
        memory_type (str): 按记忆类型过滤
        tags (List[str]): 按标签过滤
        limit (int): 最大结果数量
        project_id (str): 项目ID

    Returns:
        str: 搜索结果的JSON格式字符串

    Example:
        search_memories("API设计", "architecture", ["api"], 10)
    """
    try:
        # Use project root as project ID if not specified
        if not project_id:
            project_root = get_sandbox_project_root()
            project_id = (
                os.path.basename(project_root) or plugin.get_config().DEFAULT_PROJECT_ID
            )

        results = await memory_service.search_memories(
            project_id=project_id,
            query=query,
            memory_type=memory_type,
            tags=tags,
            limit=limit,
        )

        return json.dumps(
            {
                "query": query,
                "project_id": project_id,
                "filters": {
                    "memory_type": memory_type,
                    "tags": tags,
                },
                "total_results": len(results),
                "results": results,
            },
            indent=2,
            ensure_ascii=False,
        )

    except Exception as e:
        logger.error(f"Error in search_memories: {e}")
        return json.dumps({"error": str(e)})


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "get_memory_stats")
async def get_memory_stats(
    project_id: Optional[str] = None,
    _ctx: Optional[AgentCtx] = None,
) -> str:
    """获取项目记忆统计信息

    Args:
        project_id (str): 项目ID

    Returns:
        str: 统计信息的JSON格式字符串

    Example:
        get_memory_stats()
    """
    try:
        # Use project root as project ID if not specified
        if not project_id:
            project_root = get_sandbox_project_root()
            project_id = (
                os.path.basename(project_root) or plugin.get_config().DEFAULT_PROJECT_ID
            )

        stats = await memory_service.get_memory_stats(project_id)

        return json.dumps(
            {
                "project_id": project_id,
                "statistics": stats,
            },
            indent=2,
            ensure_ascii=False,
        )

    except Exception as e:
        logger.error(f"Error in get_memory_stats: {e}")
        return json.dumps({"error": str(e)})


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "get_memories_by_type")
async def get_memories_by_type(
    memory_type: str,
    limit: int = 50,
    project_id: Optional[str] = None,
    _ctx: Optional[AgentCtx] = None,
) -> str:
    """按类型获取项目记忆

    Args:
        memory_type (str): 记忆类型
        limit (int): 最大结果数量
        project_id (str): 项目ID

    Returns:
        str: 记忆列表的JSON格式字符串

    Example:
        get_memories_by_type("architecture", 20)
    """
    try:
        # Use project root as project ID if not specified
        if not project_id:
            project_root = get_sandbox_project_root()
            project_id = (
                os.path.basename(project_root) or plugin.get_config().DEFAULT_PROJECT_ID
            )

        memories = await memory_service.list_memories(
            project_id=project_id,
            memory_type=memory_type,
            limit=limit,
        )

        return json.dumps(
            {
                "project_id": project_id,
                "memory_type": memory_type,
                "total_memories": len(memories),
                "memories": memories,
            },
            indent=2,
            ensure_ascii=False,
        )

    except Exception as e:
        logger.error(f"Error in get_memories_by_type: {e}")
        return json.dumps({"error": str(e)})


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "get_memories_by_tags")
async def get_memories_by_tags(
    tags: List[str],
    match_all: bool = True,
    limit: int = 50,
    project_id: Optional[str] = None,
    _ctx: Optional[AgentCtx] = None,
) -> str:
    """按标签获取项目记忆

    Args:
        tags (List[str]): 标签列表
        match_all (bool): 是否匹配所有标签（True）或任意标签（False）
        limit (int): 最大结果数量
        project_id (str): 项目ID

    Returns:
        str: 记忆列表的JSON格式字符串

    Example:
        get_memories_by_tags(["api", "design"], True, 20)
    """
    try:
        # Use project root as project ID if not specified
        if not project_id:
            project_root = get_sandbox_project_root()
            project_id = (
                os.path.basename(project_root) or plugin.get_config().DEFAULT_PROJECT_ID
            )

        if match_all:
            # Use existing service method that requires all tags
            memories = await memory_service.list_memories(
                project_id=project_id,
                tags=tags,
                limit=limit,
            )
        else:
            # Get all memories and filter for any matching tag
            all_memories = await memory_service.list_memories(
                project_id=project_id,
                limit=limit * 2,  # Get more to filter
            )

            memories = []
            for memory in all_memories:
                if any(tag in memory["tags"] for tag in tags):
                    memories.append(memory)
                    if len(memories) >= limit:
                        break

        return json.dumps(
            {
                "project_id": project_id,
                "tags": tags,
                "match_all": match_all,
                "total_memories": len(memories),
                "memories": memories,
            },
            indent=2,
            ensure_ascii=False,
        )

    except Exception as e:
        logger.error(f"Error in get_memories_by_tags: {e}")
        return json.dumps({"error": str(e)})


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "get_memory_content")
async def get_memory_content(
    memory_name: str,
    project_id: Optional[str] = None,
    _ctx: Optional[AgentCtx] = None,
) -> str:
    """获取记忆的完整内容

    Args:
        memory_name (str): 记忆名称
        project_id (str): 项目ID

    Returns:
        str: 记忆内容

    Example:
        get_memory_content("api_design")
    """
    try:
        # Use project root as project ID if not specified
        if not project_id:
            project_root = get_sandbox_project_root()
            project_id = (
                os.path.basename(project_root) or plugin.get_config().DEFAULT_PROJECT_ID
            )

        return await memory_service.load_memory(
            project_id=project_id,
            memory_name=memory_name,
            update_access=True,
        )

    except KeyError as e:
        return f"❌ 记忆未找到: {e!s}"
    except Exception as e:
        logger.error(f"Error in get_memory_content: {e}")
        return f"❌ 获取记忆内容失败: {e!s}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "list_memory_types")
async def list_memory_types(_ctx: Optional[AgentCtx] = None) -> str:
    """列出可用的记忆类型

    Returns:
        str: 记忆类型列表的JSON格式字符串

    Example:
        list_memory_types()
    """
    try:
        config = plugin.get_config()

        return json.dumps(
            {
                "available_types": config.DEFAULT_MEMORY_TYPES,
                "descriptions": {
                    "general": "通用记忆，用于存储一般性信息",
                    "onboarding": "项目入门信息，包括设置和初始化指南",
                    "task": "任务相关记忆，包括待办事项和任务说明",
                    "code_analysis": "代码分析结果和见解",
                    "architecture": "架构设计和系统结构信息",
                    "bug_fix": "错误修复记录和解决方案",
                    "feature": "功能开发记录和规范",
                    "documentation": "文档和说明信息",
                },
            },
            indent=2,
            ensure_ascii=False,
        )

    except Exception as e:
        logger.error(f"Error in list_memory_types: {e}")
        return json.dumps({"error": str(e)})


# ========================================================================================
# |                              辅助函数                                               |
# ========================================================================================


def _extract_auto_tags(content: str) -> List[str]:
    """从内容中自动提取标签"""
    tags = []

    # Extract from markdown headers
    import re

    headers = re.findall(r"^#+\s+(.+)$", content, re.MULTILINE)
    for header in headers:
        # Extract meaningful words from headers
        words = re.findall(r"\b\w+\b", header.lower())
        tags.extend([word for word in words if len(word) > 3])

    # Extract from code blocks (programming languages)
    code_blocks = re.findall(r"```(\w+)", content)
    tags.extend(code_blocks)

    # Extract from common technical terms
    technical_terms = [
        "api",
        "database",
        "frontend",
        "backend",
        "ui",
        "ux",
        "design",
        "architecture",
        "security",
        "performance",
        "testing",
        "deployment",
        "docker",
        "kubernetes",
        "react",
        "vue",
        "angular",
        "python",
        "javascript",
        "typescript",
        "java",
        "go",
        "rust",
        "c++",
        "sql",
        "nosql",
        "mongodb",
        "postgresql",
        "mysql",
        "redis",
        "nginx",
        "apache",
        "aws",
        "azure",
        "gcp",
    ]

    content_lower = content.lower()
    for term in technical_terms:
        if term in content_lower:
            tags.append(term)

    # Remove duplicates and limit to 10 tags
    return list(set(tags))[:10]


def clean_up():
    """清理插件资源"""
    logger.info("Memory Tools plugin cleaned up")
