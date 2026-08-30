"""Manual test script for Qwen streaming.

This script tests the streaming functionality without starting the full server.
Run with: python -m pytest manual_test_qwen.py -v -s
"""
from __future__ import annotations

import asyncio
import os

import pytest

from app.services.qwen import stream_qwen_chat, QwenAuthError, QwenServiceError


@pytest.mark.asyncio
async def test_qwen_stream_connection():
    """Test actual connection to DashScope API.
    
    This test requires DASHSCOPE_API_KEY to be set in environment.
    It will be skipped if the key is not configured.
    """
    api_key = os.getenv("DASHSCOPE_API_KEY", "")
    
    if not api_key:
        pytest.skip("DASHSCOPE_API_KEY not configured")
    
    print("\n开始测试 Qwen 流式连接...")
    print(f"API Key 状态: 已配置 (长度 {len(api_key)})")
    
    try:
        chunks_received = 0
        full_response = ""
        
        async for chunk in stream_qwen_chat(
            api_key=api_key,
            message="请用一句话介绍你自己",
            model="qwen3.8-flash",
        ):
            chunks_received += 1
            full_response += chunk
            print(f"收到块 {chunks_received}: {chunk}", end="", flush=True)
        
        print(f"\n\n✓ 测试成功")
        print(f"  - 共收到 {chunks_received} 个数据块")
        print(f"  - 完整响应长度: {len(full_response)} 字符")
        print(f"  - 响应内容: {full_response[:100]}...")
        
        assert chunks_received > 0, "应该至少收到一个数据块"
        assert len(full_response) > 0, "响应不应为空"
        
    except QwenAuthError as e:
        print(f"\n✗ 认证失败: {e}")
        pytest.fail(f"API Key 认证失败: {e}")
    except QwenServiceError as e:
        print(f"\n✗ 服务错误: {e}")
        pytest.fail(f"DashScope 服务错误: {e}")


if __name__ == "__main__":
    asyncio.run(test_qwen_stream_connection())
