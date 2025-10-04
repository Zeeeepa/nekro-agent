# aipyapp Orchestrator Plugin

## Overview

The aipyapp Orchestrator plugin integrates Python execution capabilities into nekro-agent through sandboxed environments powered by [aipyapp](https://github.com/yourusername/aipyapp).

### Architecture

```
User Request → nekro-agent (orchestrator)
                    ↓
              [Decompose & Plan]
                    ↓
              [Generate Prompts]
                    ↓
              aipyapp (sandboxed executor) ← Atomic Task
                    ↓
              [Execute Python]
                    ↓
              Results → nekro-agent
                    ↓
              [Validate & Decide]
                    ↓
         Next Task or Complete
```

## Installation

### Option 1: Install with aipyapp support (Recommended)

```bash
# Using Poetry
poetry install --extras aipyapp

# Using pip
pip install -e ".[aipyapp]"
```

### Option 2: Install without aipyapp

The plugin will gracefully disable itself if aipyapp is not installed:

```bash
poetry install
# or
pip install -e .
```

## Configuration

Edit your configuration file to customize aipyapp behavior:

```python
# Enable/disable the plugin
ENABLE_AIPYAPP = True

# Execution limits
TASK_TIMEOUT = 300  # seconds (5 minutes)
MAX_TASKS_PER_SESSION = 50
SESSION_TIMEOUT = 3600  # seconds (1 hour)

# Security settings
ALLOW_NETWORK = False  # Network access in sandbox
ALLOW_FILE_IO = True  # File system access (restricted to workdir)
MAX_MEMORY_MB = 512  # Memory limit per task

# Working directory
AIPYAPP_WORKDIR = "./data/aipyapp_workdir"
```

## Available Sandbox Methods

### 1. execute_python_task

Execute a single atomic Python task with optional context.

**Type:** `AGENT` (AI analyzes results)

**Parameters:**
- `instruction` (str): Natural language description of the Python task
- `context` (str, optional): JSON string with variables and prior state

**Returns:** JSON with execution results

**Example usage in chat:**
```
AI可以写python代码？
> 是的！我可以执行 Python 代码。

请帮我计算斐波那契数列的前10项
> [AI calls execute_python_task]
> 结果：[0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
```

### 2. execute_python_workflow

Execute multi-step Python workflow with shared state between steps.

**Type:** `AGENT` (AI analyzes combined results)

**Parameters:**
- `instructions` (str): JSON array of step instructions

**Returns:** JSON with results from all steps

**Example usage in chat:**
```
请帮我：
1. 读取data.csv文件
2. 计算每列的平均值
3. 生成柱状图
> [AI calls execute_python_workflow with 3 steps]
> 已完成！生成了分析图表。
```

## Security & Isolation

### Sandbox Features

- **Process Isolation**: Each chat session gets isolated environment
- **Resource Limits**: Configurable CPU, memory, and time limits
- **Network Control**: Network access disabled by default
- **File System Isolation**: Restricted to session-specific directory
- **Automatic Cleanup**: Sessions cleaned up after idle timeout

### Security Considerations

1. **Code Injection Prevention**: Sandboxed execution prevents system access
2. **Resource Exhaustion Protection**: Timeout and memory limits enforced
3. **Network Exfiltration Prevention**: Network disabled by default
4. **File System Protection**: Access restricted to sandbox workdir

## Architecture Details

### Components

#### AipyappBridge
Translation layer between nekro-agent and aipyapp contexts.

**Responsibilities:**
- Convert nekro AgentCtx to aipyapp format
- Format execution results for nekro consumption
- Map errors with recovery suggestions

#### AipyappSandboxExecutor
Main execution interface managing aipyapp instances.

**Responsibilities:**
- Async task execution with timeout enforcement
- Session-based TaskManager management
- Resource limit enforcement
- Exception handling and error mapping

#### AipyappTaskManager
Pool management for isolated aipyapp environments.

**Responsibilities:**
- Session-to-executor mapping
- Idle session cleanup
- Resource statistics and monitoring
- Maximum session limits

### Data Flow

1. User sends request to nekro-agent
2. AI determines Python execution needed
3. AI calls `execute_python_task` or `execute_python_workflow`
4. Bridge translates nekro context to aipyapp format
5. SandboxExecutor creates/retrieves session TaskManager
6. aipyapp executes code in isolated environment
7. Results collected (output, artifacts, variables)
8. Bridge formats results for nekro
9. AI analyzes results and continues conversation

## Troubleshooting

### Plugin Not Loading

**Problem:** Plugin doesn't appear in loaded plugins list

**Solutions:**
1. Ensure aipyapp is installed: `pip install aipyapp>=0.1.22`
2. Check plugin is enabled in config: `ENABLE_AIPYAPP = True`
3. Restart nekro-agent to reload plugins
4. Check logs for initialization errors

### Execution Timeouts

**Problem:** Tasks consistently timeout

**Solutions:**
1. Increase `TASK_TIMEOUT` in configuration
2. Break complex tasks into smaller atomic tasks
3. Optimize Python code for performance
4. Check if task requires network (disabled by default)

### Memory Errors

**Problem:** Tasks fail with memory errors

**Solutions:**
1. Increase `MAX_MEMORY_MB` in configuration
2. Optimize data processing (use generators, process in chunks)
3. Clear unnecessary variables in code
4. Use more memory-efficient algorithms

### Import Errors

**Problem:** Python modules not available in sandbox

**Solutions:**
1. Check if module is installed in nekro-agent environment
2. Some modules may be restricted in sandbox for security
3. Use built-in Python modules when possible
4. Contact maintainers for module whitelist requests

## Development

### Running Tests

```bash
# Run all aipyapp tests
pytest tests/services/aipyapp_executor/ -v

# Run specific test file
pytest tests/services/aipyapp_executor/test_bridge.py -v

# Run with coverage
pytest tests/services/aipyapp_executor/ --cov=nekro_agent.services.aipyapp_executor
```

### Test Coverage

- **test_bridge.py**: 11 tests for context translation
- **test_task_manager.py**: 15 tests for session management
- **test_integration.py**: 9 integration tests

Total: 35 comprehensive tests

## Future Enhancements

### Phase 2: Orchestration Layer (Planned)
- Task decomposition engine
- Result validation with feedback loops
- Prompt templates for task generation
- Advanced error recovery

### Phase 3: Production Hardening (Planned)
- Performance benchmarking
- Monitoring and telemetry
- CI/CD integration
- Production documentation

## References

- [aipyapp Documentation](https://github.com/yourusername/aipyapp)
- [XML Specification](../docs/aipyapp-integration-spec.xml)
- [Plugin Development Guide](./Extension_Development.md)

## License

Same as nekro-agent main license.

## Credits

Developed by the nekro-agent team with contributions from the community.

