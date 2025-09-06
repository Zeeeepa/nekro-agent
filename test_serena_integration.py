#!/usr/bin/env python3
"""
Simple test script to verify Serena tools integration
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_core_imports():
    """Test core module imports"""
    print("🔍 Testing core imports...")
    
    try:
        from nekro_agent.adapters.serena_tool_adapter import SerenaToolAdapter, SerenaToolRegistry
        print("✅ SerenaToolAdapter imports successful")
        return True
    except ImportError as e:
        print(f"❌ Core import error: {e}")
        return False

def test_basic_functionality():
    """Test basic functionality of the integration"""
    print("\n🧪 Testing basic functionality...")
    
    try:
        from nekro_agent.adapters.serena_tool_adapter import SerenaToolAdapter, SerenaToolRegistry
        
        # Test SerenaToolAdapter
        adapter = SerenaToolAdapter("test_tool", lambda: "test result", "Test tool")
        print("✅ SerenaToolAdapter created successfully")
        
        # Test SerenaToolRegistry
        registry = SerenaToolRegistry()
        registry.register_tool("test_tool", adapter)
        print("✅ Tool registered successfully")
        
        tools = registry.get_all_tools()
        assert "test_tool" in tools
        print("✅ Tool retrieval successful")
        
        print("\n🎉 All basic tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_imports():
    """Test that all plugin modules can be imported"""
    print("\n📦 Testing plugin imports...")
    
    plugins = [
        "plugins.builtin.serena_file_tools",
        "plugins.builtin.serena_symbol_tools", 
        "plugins.builtin.memory_tools",
        "plugins.builtin.command_tools",
        "plugins.builtin.tool_discovery"
    ]
    
    success_count = 0
    for plugin in plugins:
        try:
            __import__(plugin)
            print(f"✅ {plugin}")
            success_count += 1
        except ImportError as e:
            print(f"❌ {plugin}: {e}")
    
    print(f"\n📊 Plugin import results: {success_count}/{len(plugins)} successful")
    return success_count == len(plugins)

def main():
    """Main test function"""
    print("🚀 Starting Serena Tools Integration Tests")
    print("=" * 50)
    
    # Test core imports
    core_ok = test_core_imports()
    
    # Test plugin imports
    imports_ok = test_imports()
    
    # Test basic functionality (only if core imports work)
    basic_ok = test_basic_functionality() if core_ok else False
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 Test Summary:")
    print(f"   Core imports: {'✅ PASS' if core_ok else '❌ FAIL'}")
    print(f"   Plugin imports: {'✅ PASS' if imports_ok else '❌ FAIL'}")
    print(f"   Basic functionality: {'✅ PASS' if basic_ok else '❌ FAIL'}")
    
    if core_ok and imports_ok and basic_ok:
        print("\n🎉 All tests passed! Serena tools integration is working correctly.")
        return 0
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
