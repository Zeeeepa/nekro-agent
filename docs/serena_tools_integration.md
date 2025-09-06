# Serena Tools Integration for NekroAgent

This document provides comprehensive documentation for the Serena tools integration in NekroAgent, which transforms it into a complete agentic coding environment.

## 🚀 Overview

The Serena tools integration brings **25+ advanced development tools** to NekroAgent, enabling AI agents to perform sophisticated code analysis, manipulation, and project management tasks. These tools are adapted from the [Serena](https://github.com/hcengineering/serena) project and provide semantic understanding of code rather than simple text-based operations.

## 📋 Available Tool Categories

### 📁 File System Operations (6 tools)
Advanced file manipulation with intelligent filtering and content analysis.

| Tool | Description | Type | Example |
|------|-------------|------|---------|
| `read_file` | Read file content with line range support | TOOL | `read_file("src/main.py", 0, 50)` |
| `create_text_file` | Create or overwrite text files safely | AGENT | `create_text_file("config.json", "{}")` |
| `list_dir` | List directory contents with recursion | TOOL | `list_dir("src", True)` |
| `find_file` | Find files by name patterns | TOOL | `find_file("*.py", "src")` |
| `replace_regex` | Replace content using regex patterns | AGENT | `replace_regex("main.py", r"old_func", "new_func")` |
| `search_files` | Search text content across files | TOOL | `search_files("TODO", "src", "*.py")` |

**Additional Enhanced Tools:**
- `search_files_for_pattern` - Regex pattern search across files
- `delete_file` - Safe file deletion with confirmation
- `get_file_info` - Detailed file/directory information

### 🎯 Advanced Symbol Operations (7 tools)
Semantic code understanding and manipulation using LSP.

| Tool | Description | Type | Example |
|------|-------------|------|---------|
| `get_symbols_overview` | Get file symbol overview | TOOL | `get_symbols_overview("src/service.py")` |
| `find_symbol` | Search symbols with filtering | TOOL | `find_symbol("UserService", "", True)` |
| `find_referencing_symbols` | Find symbols referencing target | TOOL | `find_referencing_symbols("UserService", "src/service.py")` |
| `replace_symbol_body` | Replace symbol definition | AGENT | `replace_symbol_body("method", "file.py", "new_body")` |
| `insert_after_symbol` | Insert content after symbol | AGENT | `insert_after_symbol("class", "file.py", "new_method")` |
| `insert_before_symbol` | Insert content before symbol | AGENT | `insert_before_symbol("method", "file.py", "comment")` |
| `restart_language_server` | Restart LSP server | TOOL | `restart_language_server()` |

**Additional Enhanced Tools:**
- `analyze_symbol_usage` - Analyze symbol usage patterns
- `get_symbol_hierarchy` - Get file symbol hierarchy
- `find_symbols_by_pattern` - Pattern-based symbol search
- `refactor_symbol` - Rename symbols with reference updates
- `get_symbol_dependencies` - Analyze symbol dependencies

### 🧠 Memory & Knowledge Management (4 tools)
Persistent project-specific knowledge storage.

| Tool | Description | Type | Example |
|------|-------------|------|---------|
| `write_memory` | Save project memory | AGENT | `write_memory("api_design", "# API Guidelines...")` |
| `read_memory` | Load project memory | TOOL | `read_memory("api_design")` |
| `list_memories` | List available memories | TOOL | `list_memories()` |
| `delete_memory` | Delete project memory | AGENT | `delete_memory("old_notes")` |

**Additional Enhanced Tools:**
- `write_memory_enhanced` - Enhanced memory with auto-tagging
- `search_memories` - Full-text memory search
- `get_memory_stats` - Memory usage statistics
- `get_memories_by_type` - Filter memories by type
- `get_memories_by_tags` - Filter memories by tags
- `get_memory_content` - Get full memory content
- `list_memory_types` - List available memory types

### ⚙️ Command Execution (1 tool + enhancements)
Secure shell command execution with safety controls.

| Tool | Description | Type | Example |
|------|-------------|------|---------|
| `execute_shell_command` | Execute shell commands safely | AGENT | `execute_shell_command("ls -la", "src")` |

**Additional Enhanced Tools:**
- `execute_command_with_timeout` - Command execution with timeout control
- `execute_batch_commands` - Batch command execution
- `get_command_history` - Command execution history
- `get_system_info` - System information
- `check_command_availability` - Check if commands are available

### 🔧 Tool Discovery & Documentation (1 plugin)
Comprehensive tool discovery and documentation system.

| Tool | Description | Type | Example |
|------|-------------|------|---------|
| `list_all_tools` | List all available tools | TOOL | `list_all_tools(False, "文件操作")` |
| `get_tool_info` | Get detailed tool information | TOOL | `get_tool_info("read_file", True)` |
| `search_tools` | Search tools by functionality | TOOL | `search_tools("文件读取")` |
| `recommend_tools` | Recommend tools for tasks | TOOL | `recommend_tools("读取Python文件")` |
| `get_tool_usage_stats` | Get tool usage statistics | TOOL | `get_tool_usage_stats()` |

## 🏗️ Architecture

### Adapter Framework
The integration uses a sophisticated adapter framework that bridges Serena's tool architecture with NekroAgent's plugin system:

```python
# Core adapter components
SerenaToolAdapter       # Bridges individual tools
SerenaToolRegistry     # Manages tool instances
create_nekro_plugin_from_serena_tools()  # Auto-generates plugins
```

### Plugin Structure
Each tool category is implemented as a separate plugin:

```
plugins/builtin/
├── serena_file_tools.py      # File system operations
├── serena_symbol_tools.py    # Symbol manipulation
├── memory_tools.py           # Memory management
├── command_tools.py          # Command execution
└── tool_discovery.py         # Tool discovery system
```

### Database Integration
The memory system uses Tortoise ORM with comprehensive models:

```python
# Memory system models
DBProjectMemory    # Core memory storage
DBMemoryTag       # Memory categorization
DBMemoryLink      # Memory relationships
DBMemorySearch    # Full-text search index
```

## 🛠️ Usage Examples

### File Operations
```python
# Read a Python file with line range
content = await read_file("src/main.py", 10, 50)

# Search for TODO comments in Python files
results = await search_files("TODO", "src", "*.py", False, 20)

# Create a new configuration file
await create_text_file("config/settings.json", '{"debug": true}')
```

### Symbol Operations
```python
# Get overview of symbols in a file
symbols = await get_symbols_overview("src/service.py")

# Find all references to a class
refs = await find_referencing_symbols("UserService", "src/service.py")

# Analyze symbol usage patterns
usage = await analyze_symbol_usage("UserService", "src/")
```

### Memory Management
```python
# Save architectural decisions
await write_memory_enhanced(
    "api_architecture", 
    "# API Architecture\n\n## Design Principles...",
    "architecture",
    ["api", "design", "rest"],
    priority=5
)

# Search memories for API-related content
results = await search_memories("API设计", "architecture", ["api"])

# Get memory statistics
stats = await get_memory_stats()
```

### Command Execution
```python
# Execute commands with timeout and safety checks
result = await execute_command_with_timeout(
    "npm test", 
    timeout=60, 
    cwd="frontend/",
    env_vars={"NODE_ENV": "test"}
)

# Batch execute multiple commands
results = await execute_batch_commands([
    "git status",
    "npm install", 
    "npm run build"
], stop_on_error=True)
```

### Tool Discovery
```python
# Find tools for file operations
tools = await list_all_tools(category_filter="文件操作")

# Get recommendations for a specific task
recommendations = await recommend_tools(
    "我需要分析Python代码中的函数定义",
    "代码分析任务"
)

# Search for tools related to memory
search_results = await search_tools("记忆管理")
```

## 🔧 Configuration

### Plugin Configuration
Each plugin has comprehensive configuration options:

```python
# File tools configuration
MAX_FILE_SIZE = 1048576  # 1MB
MAX_SEARCH_RESULTS = 100
IGNORED_PATTERNS = [".git", "__pycache__", "node_modules"]

# Memory tools configuration  
MAX_MEMORY_SIZE = 100000  # 100KB
MAX_MEMORIES_PER_PROJECT = 1000
ENABLE_AUTO_TAGGING = True

# Command tools configuration
DEFAULT_TIMEOUT = 30
DANGEROUS_COMMANDS = ["rm -rf", "format", "shutdown"]
ALLOWED_COMMANDS = ["ls", "git", "npm", "python"]
```

### Memory Types
The system supports various memory types:

- `general` - General project information
- `onboarding` - Project setup and initialization
- `task` - Task-specific information
- `code_analysis` - Code analysis results
- `architecture` - Architectural decisions
- `bug_fix` - Bug fix documentation
- `feature` - Feature development notes
- `documentation` - Documentation and guides

## 🚀 Benefits for Agentic Coders

### 1. **Semantic Code Understanding**
- Move beyond text-based operations to semantic understanding
- LSP-powered symbol analysis and manipulation
- Intelligent code refactoring and navigation

### 2. **Persistent Knowledge**
- Project-specific memory system
- Automatic knowledge extraction and tagging
- Cross-session information persistence

### 3. **Enhanced Productivity**
- Comprehensive tool discovery system
- Smart tool recommendations based on context
- Batch operations and workflow automation

### 4. **Safety and Security**
- Command execution with safety filters
- Sandbox environment protection
- Comprehensive error handling and logging

### 5. **Intelligent Assistance**
- Context-aware tool suggestions
- Usage statistics and optimization
- Best practices and examples integration

## 📊 Tool Usage Analytics

The system tracks comprehensive usage statistics:

```json
{
  "tool_name": "read_file",
  "usage_count": 150,
  "success_count": 147,
  "error_count": 3,
  "success_rate": 0.98,
  "average_execution_time": 0.05,
  "last_used": "2024-01-15T10:30:00Z"
}
```

## 🔮 Future Enhancements

### Planned Features
1. **Advanced Code Analysis**
   - Dependency graph analysis
   - Code quality metrics
   - Security vulnerability detection

2. **Workflow Automation**
   - Custom workflow definitions
   - Task automation templates
   - Integration with CI/CD systems

3. **Enhanced Memory System**
   - Vector-based semantic search
   - Automatic knowledge graph construction
   - Cross-project knowledge sharing

4. **IDE Integration**
   - JetBrains plugin support
   - VS Code extension
   - Real-time collaboration features

## 🤝 Contributing

To extend the Serena tools integration:

1. **Adding New Tools**
   ```python
   # Create new tool class inheriting from Serena's Tool
   class MyCustomTool(Tool):
       def apply(self, param: str) -> str:
           # Tool implementation
           return "result"
   
   # Register with adapter framework
   serena_tool_registry.register_tool(MyCustomTool)
   ```

2. **Creating New Plugins**
   ```python
   # Use the adapter framework
   plugin = create_nekro_plugin_from_serena_tools(
       plugin_name="My Custom Tools",
       module_name="my_custom_tools", 
       description="Custom tool functionality",
       tool_classes=[MyCustomTool]
   )
   ```

3. **Extending Memory System**
   - Add new memory types
   - Implement custom search algorithms
   - Create specialized memory analyzers

## 📚 References

- [Serena Project](https://github.com/hcengineering/serena) - Original tool framework
- [Language Server Protocol](https://microsoft.github.io/language-server-protocol/) - LSP specification
- [NekroAgent Documentation](../README.md) - Main project documentation

---

**Note**: This integration represents a significant enhancement to NekroAgent's capabilities, transforming it from a basic agent framework into a comprehensive agentic coding environment. The tools are designed to work together seamlessly, providing AI agents with the sophisticated capabilities needed for complex software development tasks.
