#!/usr/bin/env python3
"""
Simple test script for ZAI integration
"""
import asyncio
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Direct import of ZAI SDK
from zai_sdk.client import ZAIClient


async def test_zai_basic():
    """Test basic ZAI functionality"""
    print("🧪 Testing ZAI basic functionality...")
    
    try:
        # Initialize ZAI client with auto-auth
        client = ZAIClient(
            auto_auth=True,  # Use guest token
            verbose=True,  # Enable debug output
        )
        
        # Simple chat test
        response = client.simple_chat(
            message="Hello! Please respond with a brief greeting.",
            model="glm-4.5v",
            enable_thinking=False,
        )
        
        print("✅ ZAI Response received!")
        print(f"📝 Response content: {response.content}")
        print(f"🤔 Thinking: {response.thinking}")
        
        return True
    
    except Exception as e:
        print(f"❌ ZAI test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_zai_streaming():
    """Test ZAI streaming functionality"""
    print("\n🧪 Testing ZAI streaming functionality...")
    
    try:
        # Initialize ZAI client
        client = ZAIClient(
            auto_auth=True,  # Use guest token
            verbose=False,  # Reduce debug output for streaming
        )
        
        # Create a chat session
        chat = client.create_chat(
            title="Test Stream Chat",
            models=["glm-4.5v"],
            enable_thinking=False,
        )
        
        print("📡 Starting streaming response...")
        response_text = ""
        chunk_count = 0
        
        # Stream response
        for chunk in client.stream_completion(
            chat_id=chat.id,
            messages=[{"role": "user", "content": "Count from 1 to 5 briefly."}],
            model="glm-4.5v",
            enable_thinking=False,
        ):
            if chunk.phase == "answer" and chunk.delta_content:
                chunk_count += 1
                response_text += chunk.delta_content
                print(f"📤 Chunk {chunk_count}: {chunk.delta_content}", end="", flush=True)
        
        print(f"\n✅ ZAI Streaming completed!")
        print(f"📊 Total chunks: {chunk_count}")
        print(f"📝 Final response: {response_text}")
        
        return True
    
    except Exception as e:
        print(f"❌ ZAI streaming test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function"""
    print("🚀 Starting ZAI SDK Tests")
    print("=" * 50)
    
    # Test basic functionality
    basic_success = await test_zai_basic()
    
    # Test streaming functionality
    streaming_success = await test_zai_streaming()
    
    print("\n" + "=" * 50)
    print("📋 Test Results Summary:")
    print(f"   Basic functionality: {'✅ PASS' if basic_success else '❌ FAIL'}")
    print(f"   Streaming functionality: {'✅ PASS' if streaming_success else '❌ FAIL'}")
    
    if basic_success and streaming_success:
        print("🎉 All tests passed! ZAI SDK is working correctly.")
        return 0
    else:
        print("💥 Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)