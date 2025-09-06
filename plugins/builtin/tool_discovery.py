"""
# Tool Discovery and Documentation Plugin

Provides comprehensive tool discovery and documentation for AI agents.
This plugin helps agents understand what tools are available and how to use them effectively.

## 主要功能

- **工具发现**: 自动发现所有可用的工具和插件
- **工具文档**: 提供详细的工具使用文档和示例
- **工具分类**: 按功能分类组织工具
- **使用统计**: 跟踪工具使用情况和效果
- **智能推荐**: 基于上下文推荐合适的工具

## Agent 可用工具 (Sandbox Methods)

### 工具发现
- **list_all_tools**: 列出所有可用工具
- **get_tool_info**: 获取特定工具的详细信息
- **search_tools**: 搜索工具
- **get_tools_by_category**: 按分类获取工具

### 工具文档
- **get_tool_documentation**: 获取工具文档
- **get_tool_examples**: 获取工具使用示例
- **get_tool_best_practices**: 获取工具最佳实践

### 工具推荐
- **recommend_tools**: 推荐适合的工具
- **get_tool_alternatives**: 获取工具替代方案
"""

import json
import os
import inspect
from typing import Dict, List, Optional, Any, Set
from collections import defaultdict

from pydantic import Field

from nekro_agent.api.plugin import ConfigBase, NekroPlugin, SandboxMethodType
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.core.logger import logger

# Create the plugin
plugin = NekroPlugin(
    name="工具发现和文档系统",
    module_name="tool_discovery",
    description="提供全面的工具发现、文档和推荐功能，帮助AI代理了解和使用可用工具",
    version="1.0.0",
    author="NekroAgent Team",
    support_adapter=["onebot_v11", "minecraft", "sse", "discord", "wechatpad"],
)


@plugin.mount_config()
class ToolDiscoveryConfig(ConfigBase):
    """工具发现配置"""
    
    ENABLE_USAGE_TRACKING: bool = Field(
        default=True,
        title="启用使用跟踪",
        description="是否跟踪工具使用统计"
    )
    
    TOOL_CATEGORIES: Dict[str, List[str]] = Field(
        default={
            "文件操作": [
                "read_file", "create_text_file", "list_dir", "find_file", 
                "replace_regex", "delete_file", "search_files", "get_file_info"
            ],
            "符号操作": [
                "get_symbols_overview", "find_symbol", "find_referencing_symbols",
                "replace_symbol_body", "insert_after_symbol", "insert_before_symbol",
                "analyze_symbol_usage", "get_symbol_hierarchy"
            ],
            "记忆管理": [
                "write_memory", "read_memory", "list_memories", "delete_memory",
                "search_memories", "get_memory_stats", "write_memory_enhanced"
            ],
            "命令执行": [
                "execute_shell_command", "execute_command_with_timeout",
                "execute_batch_commands", "get_command_history", "get_system_info"
            ],
            "LSP功能": [
                "lsp_initialize", "lsp_get_diagnostics", "lsp_get_completions",
                "lsp_get_hover", "lsp_goto_definition", "lsp_find_references"
            ],
            "项目管理": [
                "activate_project", "remove_project", "get_current_config",
                "switch_modes", "onboarding"
            ],
            "工作流": [
                "think_about_collected_information", "think_about_task_adherence",
                "think_about_whether_you_are_done", "summarize_changes"
            ]
        },
        title="工具分类",
        description="工具按功能分类的映射"
    )
    
    TOOL_DIFFICULTY_LEVELS: Dict[str, str] = Field(
        default={
            "beginner": "初级 - 基础操作，易于使用",
            "intermediate": "中级 - 需要一定经验",
            "advanced": "高级 - 复杂操作，需要深入理解",
            "expert": "专家级 - 高度专业化工具"
        },
        title="工具难度等级",
        description="工具难度等级定义"
    )


# Global tool usage statistics
_tool_usage_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
    "usage_count": 0,
    "success_count": 0,
    "error_count": 0,
    "last_used": None,
    "average_execution_time": 0.0
})


# ========================================================================================
# |                           工具发现和文档功能                                          |
# ========================================================================================


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "list_all_tools")
async def list_all_tools(
    include_hidden: bool = False,
    category_filter: str = None,
    _ctx: AgentCtx = None
) -> str:
    """列出所有可用的工具
    
    Args:
        include_hidden (bool): 是否包含隐藏工具
        category_filter (str): 按分类过滤工具
    
    Returns:
        str: 工具列表的JSON格式字符串
    
    Example:
        list_all_tools(False, "文件操作")
    """
    try:
        config = plugin.get_config()
        
        # Discover all available tools
        all_tools = await _discover_all_tools()
        
        # Filter by category if specified
        if category_filter and category_filter in config.TOOL_CATEGORIES:
            category_tools = set(config.TOOL_CATEGORIES[category_filter])
            all_tools = {name: info for name, info in all_tools.items() 
                        if name in category_tools}
        
        # Filter hidden tools
        if not include_hidden:
            all_tools = {name: info for name, info in all_tools.items() 
                        if not info.get("hidden", False)}
        
        # Organize by categories
        categorized_tools = {}
        uncategorized_tools = {}
        
        for tool_name, tool_info in all_tools.items():
            category = _get_tool_category(tool_name, config)
            if category:
                if category not in categorized_tools:
                    categorized_tools[category] = {}
                categorized_tools[category][tool_name] = tool_info
            else:
                uncategorized_tools[tool_name] = tool_info
        
        return json.dumps({
            "total_tools": len(all_tools),
            "category_filter": category_filter,
            "include_hidden": include_hidden,
            "categorized_tools": categorized_tools,
            "uncategorized_tools": uncategorized_tools,
            "available_categories": list(config.TOOL_CATEGORIES.keys())
        }, indent=2, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"Error in list_all_tools: {e}")
        return json.dumps({"error": str(e)})


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "get_tool_info")
async def get_tool_info(
    tool_name: str,
    include_examples: bool = True,
    include_usage_stats: bool = True,
    _ctx: AgentCtx = None
) -> str:
    """获取特定工具的详细信息
    
    Args:
        tool_name (str): 工具名称
        include_examples (bool): 是否包含使用示例
        include_usage_stats (bool): 是否包含使用统计
    
    Returns:
        str: 工具信息的JSON格式字符串
    
    Example:
        get_tool_info("read_file", True, True)
    """
    try:
        config = plugin.get_config()
        
        # Get tool information
        all_tools = await _discover_all_tools()
        
        if tool_name not in all_tools:
            return json.dumps({
                "tool_name": tool_name,
                "found": False,
                "message": "Tool not found",
                "suggestions": _get_similar_tool_names(tool_name, list(all_tools.keys()))
            })
        
        tool_info = all_tools[tool_name].copy()
        
        # Add category information
        tool_info["category"] = _get_tool_category(tool_name, config)
        tool_info["difficulty_level"] = _get_tool_difficulty(tool_name)
        
        # Add examples if requested
        if include_examples:
            tool_info["examples"] = _get_tool_examples(tool_name)
            tool_info["best_practices"] = _get_tool_best_practices(tool_name)
        
        # Add usage statistics if requested
        if include_usage_stats and config.ENABLE_USAGE_TRACKING:
            tool_info["usage_stats"] = _tool_usage_stats.get(tool_name, {})
        
        # Add related tools
        tool_info["related_tools"] = _get_related_tools(tool_name, config)
        
        return json.dumps({
            "tool_name": tool_name,
            "found": True,
            "info": tool_info
        }, indent=2, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"Error in get_tool_info: {e}")
        return json.dumps({"error": str(e)})


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "search_tools")
async def search_tools(
    query: str,
    search_in_description: bool = True,
    search_in_examples: bool = True,
    limit: int = 20,
    _ctx: AgentCtx = None
) -> str:
    """搜索工具
    
    Args:
        query (str): 搜索查询
        search_in_description (bool): 是否在描述中搜索
        search_in_examples (bool): 是否在示例中搜索
        limit (int): 最大结果数量
    
    Returns:
        str: 搜索结果的JSON格式字符串
    
    Example:
        search_tools("文件读取", True, True, 10)
    """
    try:
        all_tools = await _discover_all_tools()
        query_lower = query.lower()
        
        results = []
        
        for tool_name, tool_info in all_tools.items():
            score = 0
            matches = []
            
            # Search in tool name
            if query_lower in tool_name.lower():
                score += 10
                matches.append("name")
            
            # Search in description
            if search_in_description:
                description = tool_info.get("description", "")
                if query_lower in description.lower():
                    score += 5
                    matches.append("description")
            
            # Search in docstring
            docstring = tool_info.get("docstring", "")
            if query_lower in docstring.lower():
                score += 3
                matches.append("docstring")
            
            # Search in examples
            if search_in_examples:
                examples = _get_tool_examples(tool_name)
                for example in examples:
                    if query_lower in example.lower():
                        score += 2
                        matches.append("examples")
                        break
            
            if score > 0:
                results.append({
                    "tool_name": tool_name,
                    "score": score,
                    "matches": matches,
                    "description": tool_info.get("description", ""),
                    "category": _get_tool_category(tool_name, plugin.get_config())
                })
        
        # Sort by score
        results.sort(key=lambda x: x["score"], reverse=True)
        
        return json.dumps({
            "query": query,
            "total_results": len(results),
            "returned_results": min(len(results), limit),
            "results": results[:limit]
        }, indent=2, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"Error in search_tools: {e}")
        return json.dumps({"error": str(e)})


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "recommend_tools")
async def recommend_tools(
    task_description: str,
    context: str = "",
    max_recommendations: int = 5,
    _ctx: AgentCtx = None
) -> str:
    """基于任务描述推荐合适的工具
    
    Args:
        task_description (str): 任务描述
        context (str): 额外上下文信息
        max_recommendations (int): 最大推荐数量
    
    Returns:
        str: 工具推荐的JSON格式字符串
    
    Example:
        recommend_tools("我需要读取一个Python文件并分析其中的函数", "代码分析任务", 5)
    """
    try:
        config = plugin.get_config()
        all_tools = await _discover_all_tools()
        
        # Analyze task description for keywords
        task_keywords = _extract_task_keywords(task_description + " " + context)
        
        recommendations = []
        
        # Score tools based on relevance
        for tool_name, tool_info in all_tools.items():
            score = _calculate_tool_relevance(
                tool_name, tool_info, task_keywords, config
            )
            
            if score > 0:
                recommendations.append({
                    "tool_name": tool_name,
                    "relevance_score": score,
                    "description": tool_info.get("description", ""),
                    "category": _get_tool_category(tool_name, config),
                    "difficulty": _get_tool_difficulty(tool_name),
                    "usage_example": _get_tool_examples(tool_name)[0] if _get_tool_examples(tool_name) else None,
                    "why_recommended": _explain_recommendation(tool_name, task_keywords)
                })
        
        # Sort by relevance score
        recommendations.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        return json.dumps({
            "task_description": task_description,
            "context": context,
            "extracted_keywords": task_keywords,
            "total_recommendations": len(recommendations),
            "recommendations": recommendations[:max_recommendations]
        }, indent=2, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"Error in recommend_tools: {e}")
        return json.dumps({"error": str(e)})


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "get_tool_usage_stats")
async def get_tool_usage_stats(
    tool_name: str = None,
    sort_by: str = "usage_count",
    limit: int = 20,
    _ctx: AgentCtx = None
) -> str:
    """获取工具使用统计
    
    Args:
        tool_name (str): 特定工具名称，None表示所有工具
        sort_by (str): 排序字段 (usage_count, success_rate, last_used)
        limit (int): 最大结果数量
    
    Returns:
        str: 使用统计的JSON格式字符串
    
    Example:
        get_tool_usage_stats(None, "usage_count", 10)
    """
    try:
        config = plugin.get_config()
        
        if not config.ENABLE_USAGE_TRACKING:
            return json.dumps({
                "usage_tracking_enabled": False,
                "message": "Usage tracking is disabled"
            })
        
        if tool_name:
            # Get stats for specific tool
            if tool_name not in _tool_usage_stats:
                return json.dumps({
                    "tool_name": tool_name,
                    "found": False,
                    "message": "No usage statistics found for this tool"
                })
            
            stats = _tool_usage_stats[tool_name].copy()
            stats["success_rate"] = (
                stats["success_count"] / stats["usage_count"] 
                if stats["usage_count"] > 0 else 0
            )
            
            return json.dumps({
                "tool_name": tool_name,
                "found": True,
                "stats": stats
            }, indent=2)
        
        else:
            # Get stats for all tools
            all_stats = []
            
            for tool_name, stats in _tool_usage_stats.items():
                tool_stats = stats.copy()
                tool_stats["tool_name"] = tool_name
                tool_stats["success_rate"] = (
                    stats["success_count"] / stats["usage_count"] 
                    if stats["usage_count"] > 0 else 0
                )
                all_stats.append(tool_stats)
            
            # Sort by specified field
            if sort_by == "success_rate":
                all_stats.sort(key=lambda x: x["success_rate"], reverse=True)
            elif sort_by == "last_used":
                all_stats.sort(key=lambda x: x["last_used"] or "", reverse=True)
            else:  # usage_count
                all_stats.sort(key=lambda x: x["usage_count"], reverse=True)
            
            return json.dumps({
                "total_tools_tracked": len(all_stats),
                "sort_by": sort_by,
                "returned_results": min(len(all_stats), limit),
                "stats": all_stats[:limit]
            }, indent=2)
        
    except Exception as e:
        logger.error(f"Error in get_tool_usage_stats: {e}")
        return json.dumps({"error": str(e)})


# ========================================================================================
# |                              辅助函数                                               |
# ========================================================================================


async def _discover_all_tools() -> Dict[str, Dict[str, Any]]:
    """发现所有可用工具"""
    tools = {}
    
    # Try to discover tools from various sources
    try:
        # Import Serena tool registry
        from nekro_agent.adapters.serena_tool_adapter import serena_tool_registry
        
        # Get Serena tools
        serena_tools = serena_tool_registry.get_all_tools_info()
        for tool_name, tool_info in serena_tools.items():
            tools[tool_name] = {
                "source": "serena",
                "description": tool_info.get("description", ""),
                "docstring": tool_info.get("docstring", ""),
                "can_edit": tool_info.get("can_edit", False),
                "type": "serena_tool"
            }
    except ImportError:
        pass
    
    # Add built-in tools (mock data for now)
    builtin_tools = {
        "lsp_initialize": {
            "source": "builtin",
            "description": "初始化语言服务器协议连接",
            "docstring": "Initialize LSP connection for a workspace",
            "can_edit": False,
            "type": "lsp_tool"
        },
        "lsp_get_diagnostics": {
            "source": "builtin", 
            "description": "获取代码诊断信息",
            "docstring": "Get diagnostic information for files",
            "can_edit": False,
            "type": "lsp_tool"
        }
    }
    
    tools.update(builtin_tools)
    
    return tools


def _get_tool_category(tool_name: str, config: ToolDiscoveryConfig) -> Optional[str]:
    """获取工具分类"""
    for category, tool_list in config.TOOL_CATEGORIES.items():
        if tool_name in tool_list:
            return category
    return None


def _get_tool_difficulty(tool_name: str) -> str:
    """获取工具难度等级"""
    # Simple heuristic based on tool name patterns
    if any(pattern in tool_name for pattern in ["execute", "batch", "advanced"]):
        return "advanced"
    elif any(pattern in tool_name for pattern in ["symbol", "refactor", "analyze"]):
        return "intermediate"
    elif any(pattern in tool_name for pattern in ["get", "list", "read", "search"]):
        return "beginner"
    else:
        return "intermediate"


def _get_tool_examples(tool_name: str) -> List[str]:
    """获取工具使用示例"""
    examples_db = {
        "read_file": [
            'read_file("src/main.py", 0, 50)',
            'read_file("config.json")',
            'read_file("README.md", 10, 20)'
        ],
        "search_files": [
            'search_files("TODO", "src", "*.py")',
            'search_files("function", ".", "*.js", False, 10)'
        ],
        "write_memory": [
            'write_memory("api_design", "# API设计原则\\n\\n1. RESTful...")',
            'write_memory("bug_fix", "修复了用户登录问题", "bug_fix", ["auth", "login"])'
        ],
        "execute_shell_command": [
            'execute_shell_command("ls -la")',
            'execute_shell_command("git status", ".", True)'
        ]
    }
    
    return examples_db.get(tool_name, [f'{tool_name}("example_parameter")'])


def _get_tool_best_practices(tool_name: str) -> List[str]:
    """获取工具最佳实践"""
    best_practices_db = {
        "read_file": [
            "使用行范围参数避免读取过大文件",
            "优先使用符号工具而不是直接读取文件",
            "检查文件是否存在再读取"
        ],
        "execute_shell_command": [
            "始终检查命令执行结果",
            "使用相对路径而不是绝对路径",
            "避免执行危险命令"
        ],
        "write_memory": [
            "使用描述性的记忆名称",
            "添加适当的标签便于检索",
            "定期清理过时的记忆"
        ]
    }
    
    return best_practices_db.get(tool_name, ["遵循工具文档中的使用指南"])


def _get_related_tools(tool_name: str, config: ToolDiscoveryConfig) -> List[str]:
    """获取相关工具"""
    category = _get_tool_category(tool_name, config)
    if category and category in config.TOOL_CATEGORIES:
        related = [t for t in config.TOOL_CATEGORIES[category] if t != tool_name]
        return related[:5]  # Limit to 5 related tools
    return []


def _get_similar_tool_names(tool_name: str, all_tool_names: List[str]) -> List[str]:
    """获取相似的工具名称"""
    import difflib
    
    similar = difflib.get_close_matches(tool_name, all_tool_names, n=3, cutoff=0.6)
    return similar


def _extract_task_keywords(text: str) -> List[str]:
    """从任务描述中提取关键词"""
    import re
    
    # Simple keyword extraction
    keywords = []
    
    # Technical terms
    tech_terms = [
        "文件", "读取", "写入", "搜索", "分析", "执行", "命令", "代码",
        "函数", "类", "变量", "符号", "记忆", "项目", "配置", "测试",
        "调试", "重构", "编译", "构建", "部署", "监控"
    ]
    
    text_lower = text.lower()
    for term in tech_terms:
        if term in text_lower:
            keywords.append(term)
    
    # Extract words that might be relevant
    words = re.findall(r'\b\w+\b', text_lower)
    keywords.extend([w for w in words if len(w) > 3])
    
    return list(set(keywords))[:10]  # Limit to 10 keywords


def _calculate_tool_relevance(
    tool_name: str, 
    tool_info: Dict[str, Any], 
    keywords: List[str],
    config: ToolDiscoveryConfig
) -> float:
    """计算工具与任务的相关性分数"""
    score = 0.0
    
    tool_text = f"{tool_name} {tool_info.get('description', '')} {tool_info.get('docstring', '')}"
    tool_text_lower = tool_text.lower()
    
    # Keyword matching
    for keyword in keywords:
        if keyword.lower() in tool_text_lower:
            score += 1.0
    
    # Category bonus
    category = _get_tool_category(tool_name, config)
    if category:
        category_keywords = {
            "文件操作": ["文件", "读取", "写入", "搜索"],
            "符号操作": ["代码", "函数", "类", "符号", "分析"],
            "记忆管理": ["记忆", "存储", "检索", "知识"],
            "命令执行": ["命令", "执行", "运行", "脚本"]
        }
        
        if category in category_keywords:
            for keyword in keywords:
                if keyword in category_keywords[category]:
                    score += 0.5
    
    return score


def _explain_recommendation(tool_name: str, keywords: List[str]) -> str:
    """解释为什么推荐这个工具"""
    explanations = {
        "read_file": "适合读取和查看文件内容",
        "search_files": "适合在多个文件中搜索内容",
        "find_symbol": "适合查找代码中的符号和函数",
        "write_memory": "适合保存重要信息供后续使用",
        "execute_shell_command": "适合执行系统命令和脚本"
    }
    
    base_explanation = explanations.get(tool_name, "与任务需求匹配")
    
    # Add keyword-specific explanation
    if any(kw in ["文件", "读取"] for kw in keywords):
        if "read" in tool_name or "file" in tool_name:
            return f"{base_explanation}，特别适合文件读取操作"
    
    return base_explanation


def clean_up():
    """清理插件资源"""
    global _tool_usage_stats
    _tool_usage_stats.clear()
    logger.info("Tool Discovery plugin cleaned up")
