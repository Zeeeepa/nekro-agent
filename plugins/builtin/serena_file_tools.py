"""
# Serena File System Tools Plugin

Provides comprehensive file system operations for AI agents, adapted from Serena's file tools.
These tools enable intelligent file manipulation, content searching, and directory operations.

## 主要功能

- **智能文件读取**: 支持行范围读取和内容长度限制
- **文件创建和编辑**: 安全的文件创建和覆写操作
- **目录浏览**: 递归目录列表和文件查找
- **内容搜索**: 基于内容的文件搜索和模式匹配
- **正则替换**: 强大的正则表达式文件内容替换
- **文件管理**: 文件删除和路径验证

## Agent 可用工具 (Sandbox Methods)

### 文件读取工具
- **read_file**: 读取文件内容，支持行范围和长度限制
- **list_dir**: 列出目录内容，支持递归浏览
- **find_file**: 按文件名模式查找文件

### 文件操作工具
- **create_text_file**: 创建或覆写文本文件
- **replace_regex**: 使用正则表达式替换文件内容
- **delete_file**: 安全删除文件

### 内容搜索工具
- **search_files**: 在文件中搜索文本内容
- **search_files_for_pattern**: 使用正则模式搜索文件
"""

import json
import os
import re
import shutil
from collections import defaultdict
from fnmatch import fnmatch
from pathlib import Path
from typing import Dict, List, Optional, Any

from pydantic import Field

from nekro_agent.api.plugin import ConfigBase, NekroPlugin, SandboxMethodType
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.core.logger import logger

# Import Serena tools
import sys
sys.path.append('serena/src')

from serena.tools.file_tools import (
    ReadFileTool,
    CreateTextFileTool, 
    ListDirTool,
    FindFileTool,
    ReplaceRegexTool
)
from nekro_agent.adapters.serena_tool_adapter import (
    create_nekro_plugin_from_serena_tools,
    serena_tool_registry,
    get_sandbox_project_root,
    resolve_relative_path,
    ensure_directory_exists
)

# Create the plugin using the adapter framework
plugin = create_nekro_plugin_from_serena_tools(
    plugin_name="Serena 文件系统工具",
    module_name="serena_file_tools",
    description="提供全面的文件系统操作工具，支持智能文件读取、创建、搜索和编辑功能",
    tool_classes=[
        ReadFileTool,
        CreateTextFileTool,
        ListDirTool,
        FindFileTool,
        ReplaceRegexTool
    ],
    version="1.0.0"
)


@plugin.mount_config()
class SerenaFileToolsConfig(ConfigBase):
    """Serena 文件工具配置"""
    
    MAX_FILE_SIZE: int = Field(
        default=1048576,  # 1MB
        title="最大文件大小",
        description="单个文件读取的最大字节数"
    )
    
    MAX_SEARCH_RESULTS: int = Field(
        default=100,
        title="最大搜索结果数",
        description="文件搜索返回的最大结果数量"
    )
    
    DEFAULT_MAX_CHARS: int = Field(
        default=50000,
        title="默认最大字符数",
        description="工具输出的默认最大字符数限制"
    )
    
    IGNORED_PATTERNS: List[str] = Field(
        default=[
            ".git", "__pycache__", "*.pyc", "node_modules", 
            ".DS_Store", "*.log", ".env", "*.tmp"
        ],
        title="忽略的文件模式",
        description="在文件操作中忽略的文件和目录模式"
    )


# ========================================================================================
# |                           额外的文件系统工具                                          |
# ========================================================================================


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "search_files")
async def search_files(
    search_text: str,
    directory: str = ".",
    file_pattern: str = "*",
    case_sensitive: bool = False,
    max_results: int = None,
    _ctx: AgentCtx = None
) -> str:
    """在指定目录中搜索包含特定文本的文件
    
    Args:
        search_text (str): 要搜索的文本内容
        directory (str): 搜索目录，默认为当前目录
        file_pattern (str): 文件名模式，支持通配符，默认为所有文件
        case_sensitive (bool): 是否区分大小写，默认为 False
        max_results (int): 最大结果数量，默认使用配置值
    
    Returns:
        str: 搜索结果的 JSON 格式字符串
    
    Example:
        search_files("TODO", "src", "*.py", False, 50)
    """
    try:
        config = plugin.get_config()
        max_results = max_results or config.MAX_SEARCH_RESULTS
        
        project_root = get_sandbox_project_root()
        search_dir = resolve_relative_path(directory, project_root)
        
        if not os.path.exists(search_dir):
            return json.dumps({"error": f"Directory not found: {directory}"})
        
        results = []
        search_flags = 0 if case_sensitive else re.IGNORECASE
        
        for root, dirs, files in os.walk(search_dir):
            # Filter out ignored directories
            dirs[:] = [d for d in dirs if not any(
                fnmatch(d, pattern) for pattern in config.IGNORED_PATTERNS
            )]
            
            for file in files:
                if not fnmatch(file, file_pattern):
                    continue
                    
                if any(fnmatch(file, pattern) for pattern in config.IGNORED_PATTERNS):
                    continue
                
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, project_root)
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        
                    if re.search(re.escape(search_text), content, search_flags):
                        # Find line numbers where text appears
                        lines = content.splitlines()
                        matches = []
                        
                        for line_num, line in enumerate(lines, 1):
                            if re.search(re.escape(search_text), line, search_flags):
                                matches.append({
                                    "line_number": line_num,
                                    "line_content": line.strip(),
                                    "context": _get_line_context(lines, line_num - 1, 1)
                                })
                                
                                if len(matches) >= 5:  # Limit matches per file
                                    break
                        
                        results.append({
                            "file": relative_path,
                            "matches": matches,
                            "total_matches": len(matches)
                        })
                        
                        if len(results) >= max_results:
                            break
                            
                except (UnicodeDecodeError, PermissionError, IsADirectoryError):
                    continue
            
            if len(results) >= max_results:
                break
        
        return json.dumps({
            "search_text": search_text,
            "directory": directory,
            "file_pattern": file_pattern,
            "case_sensitive": case_sensitive,
            "total_files": len(results),
            "results": results
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Error in search_files: {e}")
        return json.dumps({"error": str(e)})


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "search_files_for_pattern")
async def search_files_for_pattern(
    regex_pattern: str,
    directory: str = ".",
    file_pattern: str = "*",
    max_results: int = None,
    _ctx: AgentCtx = None
) -> str:
    """使用正则表达式模式在文件中搜索内容
    
    Args:
        regex_pattern (str): 正则表达式模式
        directory (str): 搜索目录，默认为当前目录
        file_pattern (str): 文件名模式，支持通配符
        max_results (int): 最大结果数量
    
    Returns:
        str: 搜索结果的 JSON 格式字符串
    
    Example:
        search_files_for_pattern(r"def\s+(\w+)\s*\(", "src", "*.py", 20)
    """
    try:
        config = plugin.get_config()
        max_results = max_results or config.MAX_SEARCH_RESULTS
        
        project_root = get_sandbox_project_root()
        search_dir = resolve_relative_path(directory, project_root)
        
        if not os.path.exists(search_dir):
            return json.dumps({"error": f"Directory not found: {directory}"})
        
        try:
            compiled_pattern = re.compile(regex_pattern, re.MULTILINE)
        except re.error as e:
            return json.dumps({"error": f"Invalid regex pattern: {e}"})
        
        results = []
        
        for root, dirs, files in os.walk(search_dir):
            # Filter out ignored directories
            dirs[:] = [d for d in dirs if not any(
                fnmatch(d, pattern) for pattern in config.IGNORED_PATTERNS
            )]
            
            for file in files:
                if not fnmatch(file, file_pattern):
                    continue
                    
                if any(fnmatch(file, pattern) for pattern in config.IGNORED_PATTERNS):
                    continue
                
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, project_root)
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    matches = []
                    for match in compiled_pattern.finditer(content):
                        # Find line number for match
                        line_num = content[:match.start()].count('\n') + 1
                        
                        matches.append({
                            "line_number": line_num,
                            "match_text": match.group(0),
                            "groups": match.groups(),
                            "start_pos": match.start(),
                            "end_pos": match.end()
                        })
                        
                        if len(matches) >= 10:  # Limit matches per file
                            break
                    
                    if matches:
                        results.append({
                            "file": relative_path,
                            "matches": matches,
                            "total_matches": len(matches)
                        })
                        
                        if len(results) >= max_results:
                            break
                            
                except (UnicodeDecodeError, PermissionError, IsADirectoryError):
                    continue
            
            if len(results) >= max_results:
                break
        
        return json.dumps({
            "regex_pattern": regex_pattern,
            "directory": directory,
            "file_pattern": file_pattern,
            "total_files": len(results),
            "results": results
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Error in search_files_for_pattern: {e}")
        return json.dumps({"error": str(e)})


@plugin.mount_sandbox_method(SandboxMethodType.AGENT, "delete_file")
async def delete_file(
    relative_path: str,
    confirm: bool = False,
    _ctx: AgentCtx = None
) -> str:
    """安全删除文件
    
    Args:
        relative_path (str): 要删除的文件相对路径
        confirm (bool): 确认删除操作，默认为 False
    
    Returns:
        str: 删除操作结果
    
    Example:
        delete_file("temp/old_file.txt", True)
    """
    try:
        if not confirm:
            return "❌ 删除操作需要确认。请设置 confirm=True 来确认删除操作。"
        
        project_root = get_sandbox_project_root()
        file_path = resolve_relative_path(relative_path, project_root)
        
        if not os.path.exists(file_path):
            return f"❌ 文件不存在: {relative_path}"
        
        if os.path.isdir(file_path):
            return f"❌ 路径是目录，不是文件: {relative_path}"
        
        # Get file info before deletion
        file_size = os.path.getsize(file_path)
        
        os.remove(file_path)
        
        return f"✅ 成功删除文件: {relative_path} (大小: {file_size} 字节)"
        
    except Exception as e:
        logger.error(f"Error in delete_file: {e}")
        return f"❌ 删除文件失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "get_file_info")
async def get_file_info(
    relative_path: str,
    _ctx: AgentCtx = None
) -> str:
    """获取文件或目录的详细信息
    
    Args:
        relative_path (str): 文件或目录的相对路径
    
    Returns:
        str: 文件信息的 JSON 格式字符串
    
    Example:
        get_file_info("src/main.py")
    """
    try:
        project_root = get_sandbox_project_root()
        full_path = resolve_relative_path(relative_path, project_root)
        
        if not os.path.exists(full_path):
            return json.dumps({"error": f"Path not found: {relative_path}"})
        
        stat = os.stat(full_path)
        
        info = {
            "path": relative_path,
            "absolute_path": full_path,
            "exists": True,
            "is_file": os.path.isfile(full_path),
            "is_directory": os.path.isdir(full_path),
            "is_symlink": os.path.islink(full_path),
            "size_bytes": stat.st_size,
            "size_human": _format_file_size(stat.st_size),
            "modified_time": stat.st_mtime,
            "created_time": stat.st_ctime,
            "permissions": oct(stat.st_mode)[-3:],
        }
        
        if os.path.isfile(full_path):
            # Additional file info
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    info["line_count"] = len(content.splitlines())
                    info["char_count"] = len(content)
                    info["encoding"] = "utf-8"
            except UnicodeDecodeError:
                info["encoding"] = "binary"
                info["line_count"] = None
                info["char_count"] = None
            except Exception:
                pass
        
        elif os.path.isdir(full_path):
            # Directory info
            try:
                items = os.listdir(full_path)
                info["item_count"] = len(items)
                info["subdirectories"] = len([item for item in items 
                                            if os.path.isdir(os.path.join(full_path, item))])
                info["files"] = len([item for item in items 
                                   if os.path.isfile(os.path.join(full_path, item))])
            except PermissionError:
                info["item_count"] = "Permission denied"
        
        return json.dumps(info, indent=2)
        
    except Exception as e:
        logger.error(f"Error in get_file_info: {e}")
        return json.dumps({"error": str(e)})


# ========================================================================================
# |                              辅助函数                                               |
# ========================================================================================


def _get_line_context(lines: List[str], line_index: int, context_lines: int = 1) -> List[str]:
    """获取指定行的上下文"""
    start = max(0, line_index - context_lines)
    end = min(len(lines), line_index + context_lines + 1)
    return lines[start:end]


def _format_file_size(size_bytes: int) -> str:
    """格式化文件大小为人类可读格式"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    
    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1
    
    return f"{size:.1f} {size_names[i]}"


def clean_up():
    """清理插件资源"""
    logger.info("Serena File Tools plugin cleaned up")
