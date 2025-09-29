#!/usr/bin/env python3
"""
Test script for ZAI integration with Nekro Agent
"""
import asyncio
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from nekro_agent.services.agent.zai import gen_zai_chat_response
from nekro_agent.services.agent.creator import OpenAIChatMessage


async def test_zai_basic():
    """Test basic ZAI functionality"""
    print("🧪 Testing ZAI basic functionality...")
    
    try:
        # Create test messages
        messages = [
            OpenAIChatMessage.from_text("user", "Hello! Please respond with a simple greeting.")
        ]
        
        # Test ZAI response
        response = await gen_zai_chat_response(
            model="glm-4.5v",
            messages=messages,
            base_url="https://chat.z.ai",
            api_key=None,  # Use auto_auth
            stream_mode=False,
            enable_thinking=False,
            max_wait_time=60,
        )
        
        print("✅ ZAI Response received!")
        print(f"📝 Response content: {response.response_content}")
        print(f"🤔 Thinking chain: {response.thought_chain}")
        print(f"📊 Token consumption: {response.token_consumption}")
        print(f"⚡ Generation time: {response.generation_time_ms}ms")
        print(f"🚀 Speed: {response.speed_tokens_per_second:.2f} tokens/s")
        
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
        # Create test messages
        messages = [
            OpenAIChatMessage.from_text("user", "Count from 1 to 10 with explanations for each number.")
        ]
        
        # Test streaming response
        print("📡 Starting streaming response...")
        response_chunks = []
        chunk_count = 0
        
        async def chunk_callback(chunk):
            nonlocal chunk_count
            chunk_count += 1
            if chunk.chunk_text:
                response_chunks.append(chunk.chunk_text)
                print(f"📤 Chunk {chunk_count}: {chunk.chunk_text}", end="", flush=True)
            return False  # Don't stop streaming
        
        response = await gen_zai_chat_response(
            model="glm-4.5v",
            messages=messages,
            base_url="https://chat.z.ai",
            api_key=None,  # Use auto_auth
            stream_mode=True,
            enable_thinking=False,
            max_wait_time=60,
            chunk_callback=chunk_callback,
        )
        
        print(f"\n✅ ZAI Streaming completed!")
        print(f"📊 Total chunks: {chunk_count}")
        print(f"📝 Final content length: {len(response.response_content)}")
        print(f"⚡ Generation time: {response.generation_time_ms}ms")
        
        return True
    
    except Exception as e:
        print(f"❌ ZAI streaming test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function"""
    print("🚀 Starting ZAI Integration Tests")
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
        print("🎉 All tests passed! ZAI integration is working correctly.")
        return 0
    else:
        print("💥 Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)