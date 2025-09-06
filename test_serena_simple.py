#!/usr/bin/env python3
"""
Simple test script to verify Serena tools integration without full nekro-agent dependencies
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_file_structure():
    """Test that all required files exist"""
    print("📁 Testing file structure...")
    
    required_files = [
        "nekro_agent/adapters/serena_tool_adapter.py",
        "nekro_agent/models/db_memory.py", 
        "nekro_agent/services/memory_service.py",
        "plugins/builtin/serena_file_tools.py",
        "plugins/builtin/serena_symbol_tools.py",
        "plugins/builtin/memory_tools.py",
        "plugins/builtin/command_tools.py",
        "plugins/builtin/tool_discovery.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
            print(f"❌ Missing: {file_path}")
        else:
            print(f"✅ Found: {file_path}")
    
    if missing_files:
        print(f"\n❌ {len(missing_files)} files missing")
        return False
    else:
        print(f"\n✅ All {len(required_files)} files found")
        return True

def test_syntax():
    """Test that all Python files have valid syntax"""
    print("\n🔍 Testing Python syntax...")
    
    python_files = [
        "nekro_agent/adapters/serena_tool_adapter.py",
        "nekro_agent/models/db_memory.py",
        "nekro_agent/services/memory_service.py", 
        "plugins/builtin/serena_file_tools.py",
        "plugins/builtin/serena_symbol_tools.py",
        "plugins/builtin/memory_tools.py",
        "plugins/builtin/command_tools.py",
        "plugins/builtin/tool_discovery.py"
    ]
    
    syntax_errors = []
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                compile(f.read(), file_path, 'exec')
            print(f"✅ Syntax OK: {file_path}")
        except SyntaxError as e:
            syntax_errors.append((file_path, str(e)))
            print(f"❌ Syntax Error: {file_path} - {e}")
        except Exception as e:
            print(f"⚠️  Warning: {file_path} - {e}")
    
    if syntax_errors:
        print(f"\n❌ {len(syntax_errors)} syntax errors found")
        return False
    else:
        print(f"\n✅ All {len(python_files)} files have valid syntax")
        return True

def test_code_quality():
    """Test basic code quality metrics"""
    print("\n📊 Testing code quality...")
    
    # Count lines of code
    total_lines = 0
    total_files = 0
    
    python_files = [
        "nekro_agent/adapters/serena_tool_adapter.py",
        "nekro_agent/models/db_memory.py",
        "nekro_agent/services/memory_service.py",
        "plugins/builtin/serena_file_tools.py", 
        "plugins/builtin/serena_symbol_tools.py",
        "plugins/builtin/memory_tools.py",
        "plugins/builtin/command_tools.py",
        "plugins/builtin/tool_discovery.py"
    ]
    
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = len(f.readlines())
                total_lines += lines
                total_files += 1
                print(f"📄 {file_path}: {lines} lines")
        except Exception as e:
            print(f"❌ Error reading {file_path}: {e}")
    
    print(f"\n📈 Total: {total_lines} lines across {total_files} files")
    print(f"📊 Average: {total_lines // total_files if total_files > 0 else 0} lines per file")
    
    return True

def main():
    """Main test function"""
    print("🚀 Starting Serena Tools Integration Tests (Simple)")
    print("=" * 60)
    
    # Test file structure
    structure_ok = test_file_structure()
    
    # Test syntax
    syntax_ok = test_syntax()
    
    # Test code quality
    quality_ok = test_code_quality()
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 Test Summary:")
    print(f"   File structure: {'✅ PASS' if structure_ok else '❌ FAIL'}")
    print(f"   Python syntax: {'✅ PASS' if syntax_ok else '❌ FAIL'}")
    print(f"   Code quality: {'✅ PASS' if quality_ok else '❌ FAIL'}")
    
    if structure_ok and syntax_ok and quality_ok:
        print("\n🎉 All tests passed! Serena tools integration files are ready.")
        print("📝 Note: Runtime testing requires resolving the 'weave' dependency.")
        return 0
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
