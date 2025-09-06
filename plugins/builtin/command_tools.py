"""
# Command Execution Tools Plugin

Provides secure command execution capabilities for AI agents, adapted from Serena's command tools.
These tools enable safe execution of shell commands within the sandbox environment.

## 主要功能

- **安全命令执行**: 在沙盒环境中安全执行shell命令
- **输出捕获**: 捕获命令的标准输出和错误输出
- **工作目录控制**: 指定命令执行的工作目录
- **超时保护**: 防止命令执行时间过长
- **命令历史**: 记录执行的命令历史
- **安全过滤**: 过滤危险命令防止系统损坏

## Agent 可用工具 (Sandbox Methods)

### 命令执行工具
- **execute_shell_command**: 执行shell命令
- **execute_command_with_timeout**: 带超时的命令执行
- **execute_batch_commands**: 批量执行命令
- **get_command_history**: 获取命令执行历史

### 系统信息工具
- **get_system_info**: 获取系统信息
- **check_command_availability**: 检查命令是否可用
- **get_environment_variables**: 获取环境变量
"""

import asyncio
import json
import os
import shlex
import subprocess

# Import Serena command tools
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from pydantic import Field

from nekro_agent.api.plugin import ConfigBase, NekroPlugin, SandboxMethodType
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.core.logger import logger

sys.path.append("serena/src")

from nekro_agent.adapters.serena_tool_adapter import (
    create_nekro_plugin_from_serena_tools,
    get_sandbox_project_root,
)
from serena.tools.cmd_tools import ExecuteShellCommandTool

# Create the plugin using the adapter framework
plugin = create_nekro_plugin_from_serena_tools(
    plugin_name="安全命令执行工具",
    module_name="command_tools",
    description="提供安全的shell命令执行功能，支持输出捕获、超时控制和安全过滤",
    tool_classes=[
        ExecuteShellCommandTool,
    ],
    version="1.0.0",
)


@plugin.mount_config()
class CommandToolsConfig(ConfigBase):
    """命令工具配置"""

    DEFAULT_TIMEOUT: int = Field(
        default=30,
        title="默认超时时间",
        description="命令执行的默认超时时间（秒）",
    )

    MAX_OUTPUT_SIZE: int = Field(
        default=1048576,  # 1MB
        title="最大输出大小",
        description="命令输出的最大字节数",
    )

    DANGEROUS_COMMANDS: List[str] = Field(
        default=[
            "rm -rf",
            "format",
            "del /f",
            "shutdown",
            "reboot",
            "dd if=",
            "mkfs",
            "fdisk",
            "parted",
            "kill -9",
            "killall",
            "pkill",
            "sudo rm",
            "chmod 777",
        ],
        title="危险命令列表",
        description="被禁止执行的危险命令模式",
    )

    ALLOWED_COMMANDS: List[str] = Field(
        default=[
            "ls",
            "cat",
            "grep",
            "find",
            "head",
            "tail",
            "wc",
            "sort",
            "git",
            "npm",
            "pip",
            "python",
            "node",
            "java",
            "go",
            "make",
            "cmake",
            "cargo",
            "mvn",
            "gradle",
            "docker",
            "kubectl",
            "curl",
            "wget",
            "ping",
            "nslookup",
        ],
        title="允许的命令列表",
        description="明确允许执行的命令列表",
    )

    ENABLE_COMMAND_HISTORY: bool = Field(
        default=True,
        title="启用命令历史",
        description="是否记录命令执行历史",
    )

    MAX_HISTORY_SIZE: int = Field(
        default=1000,
        title="最大历史记录数",
        description="保存的最大命令历史记录数",
    )


# Global command history storage
_command_history: List[Dict[str, Any]] = []


# ========================================================================================
# |                           增强的命令执行工具                                          |
# ========================================================================================


@plugin.mount_sandbox_method(SandboxMethodType.AGENT, "execute_command_with_timeout")
async def execute_command_with_timeout(
    command: str,
    timeout: Optional[int] = None,
    cwd: Optional[str] = None,
    capture_stderr: bool = True,
    env_vars: Optional[Dict[str, str]] = None,
    _ctx: Optional[AgentCtx] = None,
) -> str:
    """执行带超时控制的shell命令

    Args:
        command (str): 要执行的shell命令
        timeout (int): 超时时间（秒），默认使用配置值
        cwd (str): 工作目录，默认为项目根目录
        capture_stderr (bool): 是否捕获错误输出
        env_vars (Dict[str, str]): 额外的环境变量

    Returns:
        str: 命令执行结果的JSON格式字符串

    Example:
        execute_command_with_timeout("ls -la", 10, "src/", True, {"DEBUG": "1"})
    """
    try:
        config = plugin.get_config()
        timeout = timeout or config.DEFAULT_TIMEOUT

        # Security check
        if not _is_command_safe(command, config):
            return json.dumps(
                {
                    "success": False,
                    "error": "Command blocked for security reasons",
                    "command": command,
                    "blocked": True,
                },
            )

        # Set working directory
        if not cwd:
            cwd = get_sandbox_project_root()
        else:
            # Resolve relative path
            if not os.path.isabs(cwd):
                cwd = os.path.join(get_sandbox_project_root(), cwd)

        # Prepare environment
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)

        # Record start time
        start_time = time.time()

        try:
            # Execute command with timeout
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE if capture_stderr else None,
                cwd=cwd,
                env=env,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()

                execution_time = time.time() - start_time
                result = {
                    "success": False,
                    "error": f"Command timed out after {timeout} seconds",
                    "command": command,
                    "cwd": cwd,
                    "timeout": timeout,
                    "execution_time": execution_time,
                    "timed_out": True,
                }

                _record_command_history(command, result, _ctx)
                return json.dumps(result)

            # Process results
            execution_time = time.time() - start_time

            stdout_text = stdout.decode("utf-8", errors="replace") if stdout else ""
            stderr_text = stderr.decode("utf-8", errors="replace") if stderr else ""

            # Limit output size
            if len(stdout_text) > config.MAX_OUTPUT_SIZE:
                stdout_text = (
                    stdout_text[: config.MAX_OUTPUT_SIZE] + "\n... (output truncated)"
                )

            if len(stderr_text) > config.MAX_OUTPUT_SIZE:
                stderr_text = (
                    stderr_text[: config.MAX_OUTPUT_SIZE] + "\n... (output truncated)"
                )

            result = {
                "success": process.returncode == 0,
                "return_code": process.returncode,
                "command": command,
                "cwd": cwd,
                "stdout": stdout_text,
                "stderr": stderr_text if capture_stderr else None,
                "execution_time": execution_time,
                "timeout": timeout,
                "env_vars": env_vars or {},
            }

            _record_command_history(command, result, _ctx)
            return json.dumps(result, indent=2)

        except Exception as e:
            execution_time = time.time() - start_time
            result = {
                "success": False,
                "error": str(e),
                "command": command,
                "cwd": cwd,
                "execution_time": execution_time,
            }

            _record_command_history(command, result, _ctx)
            return json.dumps(result)

    except Exception as e:
        logger.error(f"Error in execute_command_with_timeout: {e}")
        return json.dumps(
            {
                "success": False,
                "error": str(e),
                "command": command,
            },
        )


@plugin.mount_sandbox_method(SandboxMethodType.AGENT, "execute_batch_commands")
async def execute_batch_commands(
    commands: List[str],
    stop_on_error: bool = True,
    timeout_per_command: Optional[int] = None,
    cwd: Optional[str] = None,
    _ctx: Optional[AgentCtx] = None,
) -> str:
    """批量执行shell命令

    Args:
        commands (List[str]): 要执行的命令列表
        stop_on_error (bool): 遇到错误时是否停止执行
        timeout_per_command (int): 每个命令的超时时间
        cwd (str): 工作目录

    Returns:
        str: 批量执行结果的JSON格式字符串

    Example:
        execute_batch_commands(["ls -la", "pwd", "git status"], True, 10)
    """
    try:
        config = plugin.get_config()
        timeout_per_command = timeout_per_command or config.DEFAULT_TIMEOUT

        results = []
        total_start_time = time.time()

        for i, command in enumerate(commands):
            logger.info(f"Executing batch command {i + 1}/{len(commands)}: {command}")

            # Execute individual command
            result_json = await execute_command_with_timeout(
                command=command,
                timeout=timeout_per_command,
                cwd=cwd,
                capture_stderr=True,
                _ctx=_ctx,
            )

            result = json.loads(result_json)
            results.append(
                {
                    "index": i,
                    "command": command,
                    "result": result,
                },
            )

            # Stop on error if configured
            if stop_on_error and not result.get("success", False):
                logger.warning(
                    f"Stopping batch execution due to error in command {i + 1}",
                )
                break

        total_execution_time = time.time() - total_start_time

        # Calculate summary statistics
        successful_commands = sum(
            1 for r in results if r["result"].get("success", False)
        )
        failed_commands = len(results) - successful_commands

        return json.dumps(
            {
                "batch_execution": True,
                "total_commands": len(commands),
                "executed_commands": len(results),
                "successful_commands": successful_commands,
                "failed_commands": failed_commands,
                "stop_on_error": stop_on_error,
                "total_execution_time": total_execution_time,
                "results": results,
            },
            indent=2,
        )

    except Exception as e:
        logger.error(f"Error in execute_batch_commands: {e}")
        return json.dumps(
            {
                "success": False,
                "error": str(e),
                "commands": commands,
            },
        )


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "get_command_history")
async def get_command_history(
    limit: int = 50,
    filter_successful: Optional[bool] = None,
    _ctx: Optional[AgentCtx] = None,
) -> str:
    """获取命令执行历史

    Args:
        limit (int): 返回的最大记录数
        filter_successful (bool): 过滤成功/失败的命令，None表示不过滤

    Returns:
        str: 命令历史的JSON格式字符串

    Example:
        get_command_history(20, True)
    """
    try:
        config = plugin.get_config()

        if not config.ENABLE_COMMAND_HISTORY:
            return json.dumps(
                {
                    "history_enabled": False,
                    "message": "Command history is disabled",
                },
            )

        # Filter history
        filtered_history = _command_history

        if filter_successful is not None:
            filtered_history = [
                entry
                for entry in _command_history
                if entry.get("result", {}).get("success", False) == filter_successful
            ]

        # Limit results
        limited_history = filtered_history[-limit:] if limit > 0 else filtered_history

        return json.dumps(
            {
                "history_enabled": True,
                "total_entries": len(_command_history),
                "filtered_entries": len(filtered_history),
                "returned_entries": len(limited_history),
                "filter_successful": filter_successful,
                "history": limited_history,
            },
            indent=2,
        )

    except Exception as e:
        logger.error(f"Error in get_command_history: {e}")
        return json.dumps({"error": str(e)})


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "get_system_info")
async def get_system_info(_ctx: Optional[AgentCtx] = None) -> str:
    """获取系统信息

    Returns:
        str: 系统信息的JSON格式字符串

    Example:
        get_system_info()
    """
    try:
        import platform

        import psutil

        # Get basic system info
        system_info = {
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "architecture": platform.architecture(),
                "python_version": platform.python_version(),
            },
            "resources": {
                "cpu_count": psutil.cpu_count(),
                "memory_total": psutil.virtual_memory().total,
                "memory_available": psutil.virtual_memory().available,
                "disk_usage": {
                    "total": psutil.disk_usage("/").total,
                    "used": psutil.disk_usage("/").used,
                    "free": psutil.disk_usage("/").free,
                },
            },
            "environment": {
                "cwd": os.getcwd(),
                "user": os.environ.get("USER", "unknown"),
                "home": os.environ.get("HOME", "unknown"),
                "path": os.environ.get("PATH", "").split(os.pathsep)[
                    :10
                ],  # Limit PATH entries
            },
        }

        return json.dumps(system_info, indent=2)

    except Exception as e:
        logger.error(f"Error in get_system_info: {e}")
        return json.dumps({"error": str(e)})


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "check_command_availability")
async def check_command_availability(
    commands: List[str],
    _ctx: Optional[AgentCtx] = None,
) -> str:
    """检查命令是否可用

    Args:
        commands (List[str]): 要检查的命令列表

    Returns:
        str: 命令可用性检查结果的JSON格式字符串

    Example:
        check_command_availability(["git", "python", "node", "docker"])
    """
    try:
        results = {}

        for command in commands:
            try:
                # Use 'which' command to check availability
                result = subprocess.run(
                    ["which", command],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                if result.returncode == 0:
                    path = result.stdout.strip()

                    # Try to get version info
                    version_commands = [
                        f"{command} --version",
                        f"{command} -v",
                        f"{command} version",
                    ]

                    version_info = "unknown"
                    for version_cmd in version_commands:
                        try:
                            version_result = subprocess.run(
                                version_cmd.split(),
                                capture_output=True,
                                text=True,
                                timeout=5,
                            )
                            if version_result.returncode == 0:
                                version_info = version_result.stdout.strip().split(
                                    "\n",
                                )[0]
                                break
                        except:
                            continue

                    results[command] = {
                        "available": True,
                        "path": path,
                        "version": version_info,
                    }
                else:
                    results[command] = {
                        "available": False,
                        "path": None,
                        "version": None,
                    }

            except Exception as e:
                results[command] = {
                    "available": False,
                    "path": None,
                    "version": None,
                    "error": str(e),
                }

        # Summary statistics
        available_count = sum(1 for r in results.values() if r["available"])

        return json.dumps(
            {
                "checked_commands": len(commands),
                "available_commands": available_count,
                "unavailable_commands": len(commands) - available_count,
                "results": results,
            },
            indent=2,
        )

    except Exception as e:
        logger.error(f"Error in check_command_availability: {e}")
        return json.dumps({"error": str(e)})


# ========================================================================================
# |                              辅助函数                                               |
# ========================================================================================


def _is_command_safe(command: str, config: CommandToolsConfig) -> bool:
    """检查命令是否安全"""
    command_lower = command.lower().strip()

    # Check for dangerous patterns
    for dangerous_pattern in config.DANGEROUS_COMMANDS:
        if dangerous_pattern.lower() in command_lower:
            logger.warning(f"Blocked dangerous command pattern: {dangerous_pattern}")
            return False

    # Extract the main command (first word)
    main_command = shlex.split(command)[0] if command.strip() else ""

    # Check if main command is in allowed list
    if config.ALLOWED_COMMANDS and main_command not in config.ALLOWED_COMMANDS:
        logger.warning(f"Command not in allowed list: {main_command}")
        return False

    return True


def _record_command_history(command: str, result: Dict[str, Any], ctx: AgentCtx = None):
    """记录命令执行历史"""
    config = plugin.get_config()

    if not config.ENABLE_COMMAND_HISTORY:
        return

    history_entry = {
        "timestamp": datetime.now().isoformat(),
        "command": command,
        "result": result,
        "user_id": ctx.user_id if ctx else None,
        "success": result.get("success", False),
        "execution_time": result.get("execution_time", 0),
    }

    _command_history.append(history_entry)

    # Limit history size
    if len(_command_history) > config.MAX_HISTORY_SIZE:
        _command_history.pop(0)


def clean_up():
    """清理插件资源"""
    global _command_history
    _command_history.clear()
    logger.info("Command Tools plugin cleaned up")
