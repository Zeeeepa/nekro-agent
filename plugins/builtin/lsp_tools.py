"""
# LSP Tools Plugin

Provides Language Server Protocol (LSP) integration for NekroAgent, enabling advanced code analysis, 
diagnostics, and manipulation capabilities for AI agents.

## 主要功能

- **代码分析**: 使用 LSP 进行语义级代码分析，支持 25+ 编程语言
- **诊断信息**: 实时获取代码错误、警告和提示信息
- **符号搜索**: 智能符号查找、定义跳转和引用查找
- **工作区管理**: 管理多个代码工作区和项目
- **代码操作**: 基于语义的代码重构和操作

## Agent 可用工具 (Sandbox Methods)

### 工作区管理工具
- **create_lsp_workspace**: 创建新的 LSP 工作区
- **get_lsp_workspaces**: 获取所有工作区信息
- **analyze_lsp_workspace**: 分析工作区代码质量

### 代码分析工具
- **get_lsp_diagnostics**: 获取代码诊断信息（错误、警告等）
- **find_lsp_symbol**: 查找代码符号（函数、类、变量等）
- **get_lsp_references**: 获取符号引用位置
- **get_lsp_definition**: 获取符号定义位置

### 代码操作工具
- **lsp_code_analysis**: 综合代码分析和建议
- **lsp_refactor_suggestions**: 获取重构建议
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

from pydantic import Field

from nekro_agent.api.plugin import ConfigBase, NekroPlugin, SandboxMethodType
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.services.lsp_service import lsp_service
from nekro_agent.models.db_lsp_workspace import DBLSPWorkspace
from nekro_agent.core.logger import logger

plugin = NekroPlugin(
    name="LSP 工具插件",
    module_name="lsp_tools",
    description="提供 Language Server Protocol 集成，支持高级代码分析、诊断和操作功能",
    version="1.0.0",
    author="NekroAgent Team",
    url="https://github.com/KroMiose/nekro-agent",
    support_adapter=["onebot_v11", "minecraft", "sse", "discord", "wechatpad"],
)


@plugin.mount_config()
class LSPConfig(ConfigBase):
    """LSP 配置"""
    
    ENABLE_AUTO_ANALYSIS: bool = Field(
        default=True,
        title="启用自动分析",
        description="是否在创建工作区时自动进行代码分析"
    )
    
    DEFAULT_LANGUAGE: str = Field(
        default="python",
        title="默认编程语言",
        description="创建工作区时的默认编程语言"
    )
    
    MAX_DIAGNOSTICS: int = Field(
        default=100,
        title="最大诊断数量",
        description="单次返回的最大诊断信息数量"
    )
    
    SUPPORTED_LANGUAGES: List[str] = Field(
        default=[
            "python", "typescript", "javascript", "go", "rust", "java", 
            "csharp", "cpp", "c", "php", "ruby", "swift", "kotlin"
        ],
        title="支持的编程语言",
        description="LSP 支持的编程语言列表"
    )


# ========================================================================================
# |                              LSP 工具集                                              |
# ========================================================================================


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "create_lsp_workspace")
async def create_lsp_workspace(
    workspace_id: str,
    workspace_path: str,
    name: str = None,
    language: str = "python",
    _ctx: AgentCtx = None
) -> str:
    """创建新的 LSP 工作区
    
    Args:
        workspace_id (str): 工作区唯一标识符
        workspace_path (str): 工作区目录路径
        name (str, optional): 工作区显示名称
        language (str, optional): 主要编程语言，默认为 python
    
    Returns:
        str: 创建结果信息
    
    Example:
        create_lsp_workspace("my_project", "/path/to/project", "My Project", "python")
    """
    try:
        # 验证路径存在
        if not os.path.exists(workspace_path):
            return f"错误：工作区路径不存在: {workspace_path}"
        
        # 检查是否已存在
        existing = await DBLSPWorkspace.filter(workspace_id=workspace_id).first()
        if existing:
            return f"错误：工作区 '{workspace_id}' 已存在"
        
        # 创建工作区
        success = await lsp_service.create_workspace(
            workspace_id=workspace_id,
            workspace_path=workspace_path,
            language=language
        )
        
        if not success:
            return f"错误：无法创建 LSP 工作区 '{workspace_id}'"
        
        # 创建数据库记录
        workspace = await DBLSPWorkspace.create(
            workspace_id=workspace_id,
            name=name or workspace_id,
            path=workspace_path,
            language=language,
            status="active"
        )
        
        # 自动分析（如果启用）
        config = plugin.get_config()
        if config.ENABLE_AUTO_ANALYSIS:
            try:
                diagnostics = await lsp_service.get_workspace_diagnostics(workspace_id)
                error_count = sum(1 for d in diagnostics if d.get("severity") == "error")
                warning_count = sum(1 for d in diagnostics if d.get("severity") == "warning")
                
                workspace.error_count = error_count
                workspace.warning_count = warning_count
                await workspace.save()
                
                return f"✅ 成功创建工作区 '{workspace_id}'\n路径: {workspace_path}\n语言: {language}\n发现 {error_count} 个错误，{warning_count} 个警告"
            except Exception as e:
                logger.warning(f"自动分析失败: {e}")
                return f"✅ 成功创建工作区 '{workspace_id}'\n路径: {workspace_path}\n语言: {language}\n注意：自动分析失败"
        
        return f"✅ 成功创建工作区 '{workspace_id}'\n路径: {workspace_path}\n语言: {language}"
        
    except Exception as e:
        logger.error(f"创建工作区失败: {e}")
        return f"❌ 创建工作区失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "get_lsp_workspaces")
async def get_lsp_workspaces(_ctx: AgentCtx = None) -> str:
    """获取所有 LSP 工作区信息
    
    Returns:
        str: 工作区列表信息
    
    Example:
        get_lsp_workspaces()
    """
    try:
        workspaces = await DBLSPWorkspace.all()
        
        if not workspaces:
            return "📁 当前没有 LSP 工作区"
        
        result = "📁 LSP 工作区列表:\n\n"
        for workspace in workspaces:
            status_emoji = "🟢" if workspace.status == "active" else "🔴"
            result += f"{status_emoji} **{workspace.name}** ({workspace.workspace_id})\n"
            result += f"   📂 路径: {workspace.path}\n"
            result += f"   🔤 语言: {workspace.language}\n"
            result += f"   📊 状态: {workspace.status}\n"
            result += f"   ❌ 错误: {workspace.error_count} | ⚠️ 警告: {workspace.warning_count}\n"
            if workspace.last_analyzed:
                result += f"   🕐 最后分析: {workspace.last_analyzed.strftime('%Y-%m-%d %H:%M:%S')}\n"
            result += "\n"
        
        return result
        
    except Exception as e:
        logger.error(f"获取工作区列表失败: {e}")
        return f"❌ 获取工作区列表失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "get_lsp_diagnostics")
async def get_lsp_diagnostics(
    workspace_id: str,
    severity_filter: str = None,
    max_results: int = None,
    _ctx: AgentCtx = None
) -> str:
    """获取工作区的代码诊断信息
    
    Args:
        workspace_id (str): 工作区标识符
        severity_filter (str, optional): 严重性过滤器 (error, warning, info, hint)
        max_results (int, optional): 最大返回结果数量
    
    Returns:
        str: 诊断信息列表
    
    Example:
        get_lsp_diagnostics("my_project", "error", 10)
    """
    try:
        # 验证工作区存在
        workspace = await DBLSPWorkspace.filter(workspace_id=workspace_id).first()
        if not workspace:
            return f"❌ 工作区 '{workspace_id}' 不存在"
        
        # 获取诊断信息
        diagnostics = await lsp_service.get_workspace_diagnostics(workspace_id)
        
        if not diagnostics:
            return f"✅ 工作区 '{workspace_id}' 没有发现问题"
        
        # 应用过滤器
        if severity_filter:
            diagnostics = [d for d in diagnostics if d.get("severity") == severity_filter.lower()]
        
        # 限制结果数量
        config = plugin.get_config()
        max_results = max_results or config.MAX_DIAGNOSTICS
        if len(diagnostics) > max_results:
            diagnostics = diagnostics[:max_results]
            truncated = True
        else:
            truncated = False
        
        # 格式化输出
        severity_icons = {
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️",
            "hint": "💡"
        }
        
        result = f"🔍 工作区 '{workspace_id}' 诊断信息:\n\n"
        
        # 按严重性分组统计
        severity_counts = {}
        for diag in diagnostics:
            severity = diag.get("severity", "unknown")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        result += "📊 **统计信息**:\n"
        for severity, count in severity_counts.items():
            icon = severity_icons.get(severity, "❓")
            result += f"   {icon} {severity.title()}: {count}\n"
        result += "\n"
        
        # 详细诊断信息
        result += "📋 **详细信息**:\n"
        for i, diag in enumerate(diagnostics, 1):
            severity = diag.get("severity", "unknown")
            icon = severity_icons.get(severity, "❓")
            file_path = diag.get("file", "unknown")
            message = diag.get("message", "No message")
            
            # 获取位置信息
            range_info = diag.get("range", {})
            start = range_info.get("start", {})
            line = start.get("line", 0) + 1  # 转换为 1-based
            char = start.get("character", 0)
            
            result += f"{i}. {icon} **{severity.title()}** in `{os.path.basename(file_path)}`\n"
            result += f"   📍 Line {line}, Column {char}\n"
            result += f"   💬 {message}\n"
            if diag.get("source"):
                result += f"   🔧 Source: {diag['source']}\n"
            result += "\n"
        
        if truncated:
            result += f"⚠️ 显示了前 {max_results} 个结果，总共有 {len(diagnostics)} 个问题\n"
        
        return result
        
    except Exception as e:
        logger.error(f"获取诊断信息失败: {e}")
        return f"❌ 获取诊断信息失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "find_lsp_symbol")
async def find_lsp_symbol(
    workspace_id: str,
    symbol_name: str,
    symbol_kind: str = None,
    _ctx: AgentCtx = None
) -> str:
    """在工作区中查找代码符号
    
    Args:
        workspace_id (str): 工作区标识符
        symbol_name (str): 要查找的符号名称
        symbol_kind (str, optional): 符号类型过滤器 (class, function, variable, etc.)
    
    Returns:
        str: 符号查找结果
    
    Example:
        find_lsp_symbol("my_project", "MyClass", "class")
    """
    try:
        # 验证工作区存在
        workspace = await DBLSPWorkspace.filter(workspace_id=workspace_id).first()
        if not workspace:
            return f"❌ 工作区 '{workspace_id}' 不存在"
        
        # 查找符号
        symbols = await lsp_service.find_symbol(workspace_id, symbol_name)
        
        if not symbols:
            return f"🔍 在工作区 '{workspace_id}' 中未找到符号 '{symbol_name}'"
        
        # 应用类型过滤器
        if symbol_kind:
            symbols = [s for s in symbols if s.get("kind", "").lower() == symbol_kind.lower()]
            if not symbols:
                return f"🔍 在工作区 '{workspace_id}' 中未找到类型为 '{symbol_kind}' 的符号 '{symbol_name}'"
        
        # 格式化输出
        kind_icons = {
            "class": "🏛️",
            "function": "⚙️",
            "method": "🔧",
            "variable": "📦",
            "constant": "🔒",
            "module": "📁",
            "interface": "🔌",
            "enum": "📋",
            "property": "🏷️",
            "field": "📝"
        }
        
        result = f"🔍 找到 {len(symbols)} 个符号 '{symbol_name}':\n\n"
        
        for i, symbol in enumerate(symbols, 1):
            name = symbol.get("name", "unknown")
            kind = symbol.get("kind", "unknown")
            icon = kind_icons.get(kind.lower(), "❓")
            
            location = symbol.get("location", {})
            file_path = location.get("path", "unknown")
            range_info = location.get("range", {})
            start = range_info.get("start", {})
            line = start.get("line", 0) + 1  # 转换为 1-based
            
            result += f"{i}. {icon} **{name}** ({kind})\n"
            result += f"   📂 File: `{os.path.basename(file_path)}`\n"
            result += f"   📍 Line: {line}\n"
            result += f"   🗂️ Path: {file_path}\n"
            
            if symbol.get("container_name"):
                result += f"   📦 Container: {symbol['container_name']}\n"
            
            result += "\n"
        
        return result
        
    except Exception as e:
        logger.error(f"查找符号失败: {e}")
        return f"❌ 查找符号失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "get_lsp_references")
async def get_lsp_references(
    workspace_id: str,
    file_path: str,
    line: int,
    character: int,
    _ctx: AgentCtx = None
) -> str:
    """获取符号的所有引用位置
    
    Args:
        workspace_id (str): 工作区标识符
        file_path (str): 文件路径
        line (int): 行号 (1-based)
        character (int): 字符位置 (0-based)
    
    Returns:
        str: 引用位置列表
    
    Example:
        get_lsp_references("my_project", "/path/to/file.py", 10, 5)
    """
    try:
        # 验证工作区存在
        workspace = await DBLSPWorkspace.filter(workspace_id=workspace_id).first()
        if not workspace:
            return f"❌ 工作区 '{workspace_id}' 不存在"
        
        # 获取引用 (转换为 0-based)
        references = await lsp_service.get_symbol_references(
            workspace_id=workspace_id,
            file_path=file_path,
            line=line - 1,
            character=character
        )
        
        if not references:
            return f"🔍 在位置 {os.path.basename(file_path)}:{line}:{character} 未找到符号引用"
        
        # 格式化输出
        result = f"🔗 找到 {len(references)} 个引用:\n\n"
        
        for i, ref in enumerate(references, 1):
            ref_path = ref.get("path", "unknown")
            range_info = ref.get("range", {})
            start = range_info.get("start", {})
            ref_line = start.get("line", 0) + 1  # 转换为 1-based
            ref_char = start.get("character", 0)
            
            result += f"{i}. 📂 `{os.path.basename(ref_path)}`\n"
            result += f"   📍 Line {ref_line}, Column {ref_char}\n"
            result += f"   🗂️ {ref_path}\n\n"
        
        return result
        
    except Exception as e:
        logger.error(f"获取引用失败: {e}")
        return f"❌ 获取引用失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "get_lsp_definition")
async def get_lsp_definition(
    workspace_id: str,
    file_path: str,
    line: int,
    character: int,
    _ctx: AgentCtx = None
) -> str:
    """获取符号的定义位置
    
    Args:
        workspace_id (str): 工作区标识符
        file_path (str): 文件路径
        line (int): 行号 (1-based)
        character (int): 字符位置 (0-based)
    
    Returns:
        str: 定义位置信息
    
    Example:
        get_lsp_definition("my_project", "/path/to/file.py", 10, 5)
    """
    try:
        # 验证工作区存在
        workspace = await DBLSPWorkspace.filter(workspace_id=workspace_id).first()
        if not workspace:
            return f"❌ 工作区 '{workspace_id}' 不存在"
        
        # 获取定义 (转换为 0-based)
        definition = await lsp_service.get_symbol_definition(
            workspace_id=workspace_id,
            file_path=file_path,
            line=line - 1,
            character=character
        )
        
        if not definition:
            return f"🔍 在位置 {os.path.basename(file_path)}:{line}:{character} 未找到符号定义"
        
        # 格式化输出
        def_path = definition.get("path", "unknown")
        range_info = definition.get("range", {})
        start = range_info.get("start", {})
        def_line = start.get("line", 0) + 1  # 转换为 1-based
        def_char = start.get("character", 0)
        
        result = f"🎯 符号定义位置:\n\n"
        result += f"📂 文件: `{os.path.basename(def_path)}`\n"
        result += f"📍 位置: Line {def_line}, Column {def_char}\n"
        result += f"🗂️ 完整路径: {def_path}\n"
        
        return result
        
    except Exception as e:
        logger.error(f"获取定义失败: {e}")
        return f"❌ 获取定义失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.AGENT, "lsp_code_analysis")
async def lsp_code_analysis(
    workspace_id: str,
    analysis_type: str = "comprehensive",
    _ctx: AgentCtx = None
) -> str:
    """对工作区进行综合代码分析
    
    Args:
        workspace_id (str): 工作区标识符
        analysis_type (str): 分析类型 (comprehensive, quick, errors_only)
    
    Returns:
        str: 综合分析结果和建议
    
    Example:
        lsp_code_analysis("my_project", "comprehensive")
    """
    try:
        # 验证工作区存在
        workspace = await DBLSPWorkspace.filter(workspace_id=workspace_id).first()
        if not workspace:
            return f"❌ 工作区 '{workspace_id}' 不存在"
        
        # 获取诊断信息
        diagnostics = await lsp_service.get_workspace_diagnostics(workspace_id)
        
        # 分析统计
        error_count = sum(1 for d in diagnostics if d.get("severity") == "error")
        warning_count = sum(1 for d in diagnostics if d.get("severity") == "warning")
        info_count = sum(1 for d in diagnostics if d.get("severity") == "info")
        hint_count = sum(1 for d in diagnostics if d.get("severity") == "hint")
        
        # 文件统计
        files_with_issues = set()
        for diag in diagnostics:
            files_with_issues.add(diag.get("file", ""))
        
        # 生成分析报告
        result = f"📊 **工作区 '{workspace_id}' 代码分析报告**\n\n"
        
        # 总体健康度评估
        total_issues = len(diagnostics)
        if total_issues == 0:
            health_score = "🟢 优秀"
            health_desc = "代码质量良好，未发现问题"
        elif error_count == 0 and warning_count <= 5:
            health_score = "🟡 良好"
            health_desc = "代码质量较好，有少量警告"
        elif error_count <= 3:
            health_score = "🟠 一般"
            health_desc = "存在一些问题需要修复"
        else:
            health_score = "🔴 需要改进"
            health_desc = "存在较多问题，建议优先修复错误"
        
        result += f"🏥 **健康度**: {health_score}\n"
        result += f"📝 **评估**: {health_desc}\n\n"
        
        # 统计信息
        result += "📈 **统计信息**:\n"
        result += f"   ❌ 错误: {error_count}\n"
        result += f"   ⚠️ 警告: {warning_count}\n"
        result += f"   ℹ️ 信息: {info_count}\n"
        result += f"   💡 提示: {hint_count}\n"
        result += f"   📁 涉及文件: {len(files_with_issues)}\n\n"
        
        # 优先级建议
        result += "🎯 **优先级建议**:\n"
        if error_count > 0:
            result += f"   1. 🚨 立即修复 {error_count} 个错误\n"
        if warning_count > 0:
            result += f"   2. ⚠️ 处理 {warning_count} 个警告\n"
        if info_count > 0:
            result += f"   3. ℹ️ 查看 {info_count} 个信息提示\n"
        if hint_count > 0:
            result += f"   4. 💡 考虑 {hint_count} 个改进建议\n"
        
        if total_issues == 0:
            result += "   ✅ 代码质量良好，继续保持！\n"
        
        result += "\n"
        
        # 详细问题（仅显示错误和重要警告）
        if analysis_type == "comprehensive" and (error_count > 0 or warning_count > 0):
            result += "🔍 **主要问题详情**:\n"
            
            # 显示前5个最重要的问题
            important_diagnostics = [d for d in diagnostics if d.get("severity") in ["error", "warning"]]
            for i, diag in enumerate(important_diagnostics[:5], 1):
                severity = diag.get("severity", "unknown")
                icon = "❌" if severity == "error" else "⚠️"
                file_path = diag.get("file", "unknown")
                message = diag.get("message", "No message")
                
                range_info = diag.get("range", {})
                start = range_info.get("start", {})
                line = start.get("line", 0) + 1
                
                result += f"{i}. {icon} `{os.path.basename(file_path)}:{line}`\n"
                result += f"   💬 {message}\n\n"
            
            if len(important_diagnostics) > 5:
                result += f"   ... 还有 {len(important_diagnostics) - 5} 个问题\n\n"
        
        # 更新数据库统计
        workspace.error_count = error_count
        workspace.warning_count = warning_count
        await workspace.save()
        
        return result
        
    except Exception as e:
        logger.error(f"代码分析失败: {e}")
        return f"❌ 代码分析失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.BEHAVIOR, "analyze_lsp_workspace")
async def analyze_lsp_workspace(
    workspace_id: str,
    _ctx: AgentCtx = None
) -> str:
    """分析 LSP 工作区（后台任务）
    
    Args:
        workspace_id (str): 工作区标识符
    
    Returns:
        str: 分析启动确认信息
    
    Example:
        analyze_lsp_workspace("my_project")
    """
    try:
        # 验证工作区存在
        workspace = await DBLSPWorkspace.filter(workspace_id=workspace_id).first()
        if not workspace:
            return f"❌ 工作区 '{workspace_id}' 不存在"
        
        # 启动分析
        workspace.status = "analyzing"
        await workspace.save()
        
        # 执行分析（这里可以作为后台任务）
        diagnostics = await lsp_service.get_workspace_diagnostics(workspace_id)
        
        # 更新统计
        error_count = sum(1 for d in diagnostics if d.get("severity") == "error")
        warning_count = sum(1 for d in diagnostics if d.get("severity") == "warning")
        
        workspace.error_count = error_count
        workspace.warning_count = warning_count
        workspace.status = "active"
        await workspace.save()
        
        return f"✅ 工作区 '{workspace_id}' 分析完成\n发现 {error_count} 个错误，{warning_count} 个警告"
        
    except Exception as e:
        logger.error(f"分析工作区失败: {e}")
        return f"❌ 分析工作区失败: {str(e)}"


def clean_up():
    """清理插件资源"""
    logger.info("LSP Tools plugin cleaned up")
