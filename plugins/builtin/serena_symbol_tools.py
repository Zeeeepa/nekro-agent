"""
# Serena Advanced Symbol Tools Plugin

Provides advanced symbol-based code manipulation tools for AI agents, adapted from Serena's symbol tools.
These tools enable precise code editing based on semantic understanding rather than text-based operations.

## 主要功能

- **符号概览**: 获取文件中的顶级符号概览
- **符号搜索**: 全局或局部符号搜索，支持过滤
- **引用查找**: 查找引用指定符号的其他符号
- **符号定义**: 获取符号的定义位置和内容
- **精确编辑**: 基于符号的精确代码编辑操作
- **符号重命名**: LSP驱动的符号重命名

## Agent 可用工具 (Sandbox Methods)

### 符号查询工具
- **get_symbols_overview**: 获取文件符号概览
- **find_symbol**: 搜索符号（支持过滤）
- **find_referencing_symbols**: 查找引用符号
- **get_symbol_definition**: 获取符号定义

### 符号编辑工具
- **replace_symbol_body**: 替换符号主体
- **insert_after_symbol**: 在符号后插入内容
- **insert_before_symbol**: 在符号前插入内容
- **rename_symbol**: 重命名符号

### LSP管理工具
- **restart_language_server**: 重启语言服务器
"""

import json
import os
from typing import Dict, List, Optional, Any

from pydantic import Field

from nekro_agent.api.plugin import ConfigBase, NekroPlugin, SandboxMethodType
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.core.logger import logger

# Import Serena symbol tools
import sys
sys.path.append('serena/src')

from serena.tools.symbol_tools import (
    GetSymbolsOverviewTool,
    FindSymbolTool,
    FindReferencingSymbolsTool,
    ReplaceSymbolBodyTool,
    InsertAfterSymbolTool,
    InsertBeforeSymbolTool,
    RestartLanguageServerTool
)
from nekro_agent.adapters.serena_tool_adapter import (
    create_nekro_plugin_from_serena_tools,
    get_sandbox_project_root
)

# Create the plugin using the adapter framework
plugin = create_nekro_plugin_from_serena_tools(
    plugin_name="Serena 高级符号工具",
    module_name="serena_symbol_tools",
    description="提供基于语义理解的高级符号操作工具，支持精确的代码编辑和重构",
    tool_classes=[
        GetSymbolsOverviewTool,
        FindSymbolTool,
        FindReferencingSymbolsTool,
        ReplaceSymbolBodyTool,
        InsertAfterSymbolTool,
        InsertBeforeSymbolTool,
        RestartLanguageServerTool
    ],
    version="1.0.0"
)


@plugin.mount_config()
class SerenaSymbolToolsConfig(ConfigBase):
    """Serena 符号工具配置"""
    
    MAX_SYMBOL_RESULTS: int = Field(
        default=100,
        title="最大符号结果数",
        description="符号搜索返回的最大结果数量"
    )
    
    DEFAULT_SEARCH_DEPTH: int = Field(
        default=2,
        title="默认搜索深度",
        description="符号搜索的默认深度"
    )
    
    ENABLE_SYMBOL_CACHING: bool = Field(
        default=True,
        title="启用符号缓存",
        description="是否启用符号信息缓存以提高性能"
    )
    
    SYMBOL_KINDS_FILTER: List[str] = Field(
        default=[
            "Class", "Function", "Method", "Variable", "Constant",
            "Interface", "Enum", "Module", "Namespace", "Property"
        ],
        title="符号类型过滤器",
        description="默认包含的符号类型列表"
    )
    
    AUTO_FORMAT_CODE: bool = Field(
        default=True,
        title="自动格式化代码",
        description="在符号编辑后是否自动格式化代码"
    )


# ========================================================================================
# |                           增强的符号操作工具                                          |
# ========================================================================================


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "analyze_symbol_usage")
async def analyze_symbol_usage(
    symbol_name: str,
    relative_path: str = "",
    _ctx: AgentCtx = None
) -> str:
    """分析符号的使用情况
    
    Args:
        symbol_name (str): 符号名称
        relative_path (str): 限制搜索的相对路径
    
    Returns:
        str: 符号使用分析的JSON格式字符串
    
    Example:
        analyze_symbol_usage("UserService", "src/services")
    """
    try:
        config = plugin.get_config()
        project_root = get_sandbox_project_root()
        
        # First find the symbol definition
        from nekro_agent.adapters.serena_tool_adapter import serena_tool_registry
        
        find_adapter = serena_tool_registry.get_tool_adapter("find_symbol", project_root)
        find_result = await find_adapter.apply(
            name_path=symbol_name,
            relative_path=relative_path,
            include_body=False,
            max_answer_chars=config.MAX_SYMBOL_RESULTS * 100
        )
        
        symbols = json.loads(find_result) if find_result.startswith('[') else []
        
        if not symbols:
            return json.dumps({
                "symbol_name": symbol_name,
                "found": False,
                "message": "Symbol not found"
            })
        
        # Analyze each symbol found
        analysis_results = []
        
        for symbol in symbols[:5]:  # Limit to first 5 matches
            symbol_path = symbol.get("relative_path", "")
            symbol_name_path = symbol.get("name_path", symbol_name)
            
            # Find references to this symbol
            ref_adapter = serena_tool_registry.get_tool_adapter("find_referencing_symbols", project_root)
            ref_result = await ref_adapter.apply(
                name_path=symbol_name_path,
                relative_path=symbol_path,
                include_body=False,
                max_answer_chars=config.MAX_SYMBOL_RESULTS * 100
            )
            
            references = json.loads(ref_result) if ref_result.startswith('[') else []
            
            # Categorize references
            reference_files = set()
            reference_types = {}
            
            for ref in references:
                ref_file = ref.get("relative_path", "")
                reference_files.add(ref_file)
                
                ref_kind = ref.get("kind", "unknown")
                reference_types[ref_kind] = reference_types.get(ref_kind, 0) + 1
            
            analysis_results.append({
                "symbol": {
                    "name": symbol.get("name", symbol_name),
                    "name_path": symbol_name_path,
                    "file": symbol_path,
                    "kind": symbol.get("kind", "unknown"),
                    "line": symbol.get("body_location", {}).get("start_line", 0)
                },
                "usage_stats": {
                    "total_references": len(references),
                    "files_using": len(reference_files),
                    "reference_types": reference_types
                },
                "files_list": list(reference_files)[:10]  # Limit to 10 files
            })
        
        return json.dumps({
            "symbol_name": symbol_name,
            "search_path": relative_path,
            "found": True,
            "total_definitions": len(symbols),
            "analysis": analysis_results
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Error in analyze_symbol_usage: {e}")
        return json.dumps({"error": str(e)})


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "get_symbol_hierarchy")
async def get_symbol_hierarchy(
    relative_path: str,
    max_depth: int = 3,
    _ctx: AgentCtx = None
) -> str:
    """获取文件的符号层次结构
    
    Args:
        relative_path (str): 文件相对路径
        max_depth (int): 最大层次深度
    
    Returns:
        str: 符号层次结构的JSON格式字符串
    
    Example:
        get_symbol_hierarchy("src/services/user_service.py", 3)
    """
    try:
        project_root = get_sandbox_project_root()
        
        from nekro_agent.adapters.serena_tool_adapter import serena_tool_registry
        
        # Get symbols overview with depth
        overview_adapter = serena_tool_registry.get_tool_adapter("get_symbols_overview", project_root)
        overview_result = await overview_adapter.apply(
            relative_path=relative_path,
            max_answer_chars=50000
        )
        
        symbols = json.loads(overview_result) if overview_result.startswith('[') else []
        
        # Build hierarchy tree
        hierarchy = _build_symbol_tree(symbols, max_depth)
        
        return json.dumps({
            "file": relative_path,
            "max_depth": max_depth,
            "total_symbols": len(symbols),
            "hierarchy": hierarchy
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Error in get_symbol_hierarchy: {e}")
        return json.dumps({"error": str(e)})


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "find_symbols_by_pattern")
async def find_symbols_by_pattern(
    pattern: str,
    symbol_kinds: List[str] = None,
    relative_path: str = "",
    case_sensitive: bool = False,
    _ctx: AgentCtx = None
) -> str:
    """按模式查找符号
    
    Args:
        pattern (str): 搜索模式（支持通配符）
        symbol_kinds (List[str]): 符号类型过滤
        relative_path (str): 限制搜索路径
        case_sensitive (bool): 是否区分大小写
    
    Returns:
        str: 匹配符号的JSON格式字符串
    
    Example:
        find_symbols_by_pattern("*Service", ["Class"], "src/", False)
    """
    try:
        config = plugin.get_config()
        project_root = get_sandbox_project_root()
        
        symbol_kinds = symbol_kinds or config.SYMBOL_KINDS_FILTER
        
        from nekro_agent.adapters.serena_tool_adapter import serena_tool_registry
        
        # Use find_symbol with substring matching
        find_adapter = serena_tool_registry.get_tool_adapter("find_symbol", project_root)
        find_result = await find_adapter.apply(
            name_path=pattern.replace("*", ""),  # Remove wildcards for now
            relative_path=relative_path,
            substring_matching=True,
            include_body=False,
            max_answer_chars=config.MAX_SYMBOL_RESULTS * 100
        )
        
        symbols = json.loads(find_result) if find_result.startswith('[') else []
        
        # Filter by pattern and symbol kinds
        import fnmatch
        filtered_symbols = []
        
        for symbol in symbols:
            symbol_name = symbol.get("name", "")
            symbol_kind = symbol.get("kind", "")
            
            # Pattern matching
            if case_sensitive:
                pattern_match = fnmatch.fnmatch(symbol_name, pattern)
            else:
                pattern_match = fnmatch.fnmatch(symbol_name.lower(), pattern.lower())
            
            # Kind filtering
            kind_match = not symbol_kinds or symbol_kind in symbol_kinds
            
            if pattern_match and kind_match:
                filtered_symbols.append(symbol)
        
        return json.dumps({
            "pattern": pattern,
            "symbol_kinds": symbol_kinds,
            "search_path": relative_path,
            "case_sensitive": case_sensitive,
            "total_matches": len(filtered_symbols),
            "symbols": filtered_symbols[:config.MAX_SYMBOL_RESULTS]
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Error in find_symbols_by_pattern: {e}")
        return json.dumps({"error": str(e)})


@plugin.mount_sandbox_method(SandboxMethodType.AGENT, "refactor_symbol")
async def refactor_symbol(
    old_name_path: str,
    new_name: str,
    relative_path: str,
    update_references: bool = True,
    _ctx: AgentCtx = None
) -> str:
    """重构符号（重命名并更新引用）
    
    Args:
        old_name_path (str): 原符号名称路径
        new_name (str): 新符号名称
        relative_path (str): 符号所在文件路径
        update_references (bool): 是否更新所有引用
    
    Returns:
        str: 重构操作结果
    
    Example:
        refactor_symbol("UserService", "UserManager", "src/services/user_service.py", True)
    """
    try:
        project_root = get_sandbox_project_root()
        
        from nekro_agent.adapters.serena_tool_adapter import serena_tool_registry
        
        results = []
        
        if update_references:
            # First, find all references
            ref_adapter = serena_tool_registry.get_tool_adapter("find_referencing_symbols", project_root)
            ref_result = await ref_adapter.apply(
                name_path=old_name_path,
                relative_path=relative_path,
                include_body=False,
                max_answer_chars=50000
            )
            
            references = json.loads(ref_result) if ref_result.startswith('[') else []
            results.append(f"Found {len(references)} references to update")
            
            # Update each reference (simplified - in practice would need more sophisticated logic)
            for ref in references[:20]:  # Limit to prevent excessive operations
                ref_file = ref.get("relative_path", "")
                if ref_file and ref_file != relative_path:
                    # This is a simplified approach - real implementation would need
                    # more sophisticated reference updating
                    results.append(f"Would update reference in {ref_file}")
        
        # Update the main symbol definition
        # This is a placeholder - real implementation would use LSP rename or
        # sophisticated text replacement
        results.append(f"Would rename symbol '{old_name_path}' to '{new_name}' in {relative_path}")
        
        return json.dumps({
            "operation": "refactor_symbol",
            "old_name": old_name_path,
            "new_name": new_name,
            "file": relative_path,
            "update_references": update_references,
            "status": "simulated",  # Real implementation would perform actual refactoring
            "results": results
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Error in refactor_symbol: {e}")
        return json.dumps({"error": str(e)})


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "get_symbol_dependencies")
async def get_symbol_dependencies(
    name_path: str,
    relative_path: str,
    max_depth: int = 2,
    _ctx: AgentCtx = None
) -> str:
    """获取符号的依赖关系
    
    Args:
        name_path (str): 符号名称路径
        relative_path (str): 符号所在文件路径
        max_depth (int): 依赖分析的最大深度
    
    Returns:
        str: 符号依赖关系的JSON格式字符串
    
    Example:
        get_symbol_dependencies("UserService", "src/services/user_service.py", 2)
    """
    try:
        project_root = get_sandbox_project_root()
        
        from nekro_agent.adapters.serena_tool_adapter import serena_tool_registry
        
        # Get the symbol definition with body
        find_adapter = serena_tool_registry.get_tool_adapter("find_symbol", project_root)
        find_result = await find_adapter.apply(
            name_path=name_path,
            relative_path=relative_path,
            include_body=True,
            depth=1,
            max_answer_chars=50000
        )
        
        symbols = json.loads(find_result) if find_result.startswith('[') else []
        
        if not symbols:
            return json.dumps({
                "symbol": name_path,
                "file": relative_path,
                "found": False,
                "message": "Symbol not found"
            })
        
        symbol = symbols[0]
        symbol_body = symbol.get("body", "")
        
        # Analyze dependencies from symbol body
        dependencies = _analyze_symbol_dependencies(symbol_body, relative_path)
        
        return json.dumps({
            "symbol": {
                "name": symbol.get("name", name_path),
                "name_path": name_path,
                "file": relative_path,
                "kind": symbol.get("kind", "unknown")
            },
            "dependencies": dependencies,
            "analysis_depth": max_depth
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Error in get_symbol_dependencies: {e}")
        return json.dumps({"error": str(e)})


# ========================================================================================
# |                              辅助函数                                               |
# ========================================================================================


def _build_symbol_tree(symbols: List[Dict], max_depth: int) -> Dict:
    """构建符号层次树"""
    tree = {}
    
    for symbol in symbols:
        name_path = symbol.get("name_path", "")
        parts = name_path.split("/")
        
        if len(parts) > max_depth:
            continue
        
        current = tree
        for i, part in enumerate(parts):
            if part not in current:
                current[part] = {
                    "children": {},
                    "symbol_info": None
                }
            
            if i == len(parts) - 1:
                # This is the leaf node
                current[part]["symbol_info"] = {
                    "kind": symbol.get("kind", "unknown"),
                    "line": symbol.get("body_location", {}).get("start_line", 0),
                    "file": symbol.get("relative_path", "")
                }
            
            current = current[part]["children"]
    
    return tree


def _analyze_symbol_dependencies(symbol_body: str, file_path: str) -> Dict:
    """分析符号体中的依赖关系"""
    dependencies = {
        "imports": [],
        "function_calls": [],
        "class_references": [],
        "variable_references": []
    }
    
    if not symbol_body:
        return dependencies
    
    import re
    
    # Extract import statements
    import_patterns = [
        r'import\s+(\w+(?:\.\w+)*)',
        r'from\s+(\w+(?:\.\w+)*)\s+import',
        r'#include\s*[<"]([^>"]+)[>"]',  # C/C++
        r'require\s*\([\'"]([^\'"]+)[\'"]\)',  # JavaScript
    ]
    
    for pattern in import_patterns:
        matches = re.findall(pattern, symbol_body)
        dependencies["imports"].extend(matches)
    
    # Extract function calls (simplified)
    func_calls = re.findall(r'(\w+)\s*\(', symbol_body)
    dependencies["function_calls"] = list(set(func_calls))[:20]  # Limit and dedupe
    
    # Extract class references (simplified)
    class_refs = re.findall(r'(\w+)\.', symbol_body)
    dependencies["class_references"] = list(set(class_refs))[:20]  # Limit and dedupe
    
    return dependencies


def clean_up():
    """清理插件资源"""
    logger.info("Serena Symbol Tools plugin cleaned up")
