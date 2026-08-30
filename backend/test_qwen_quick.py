#!/usr/bin/env python3
"""Quick test script to verify backend streaming without pytest."""
from __future__ import annotations

import asyncio
import os
import sys


async def test_qwen_stream():
    """Test Qwen streaming service."""
    print("=" * 60)
    print("Qwen 流式连接测试")
    print("=" * 60)
    
    # Check API key
    api_key = os.getenv("DASHSCOPE_API_KEY", "")
    if not api_key:
        print("❌ DASHSCOPE_API_KEY 未配置")
        print("请先设置环境变量：export DASHSCOPE_API_KEY=your_key")
        return False
    
    print(f"✓ API Key 已配置 (长度: {len(api_key)})")
    print()
    
    # Import after checking key
    try:
        from app.services.qwen import stream_qwen_chat, QwenAuthError, QwenModelError, QwenServiceError
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        print("请确保在 backend 目录下运行，且已安装依赖")
        return False
    
    # Test streaming
    print("开始流式请求...")
    print("模型: qwen3.8-flash")
    print("消息: 请用一句话介绍你自己")
    print("-" * 60)
    
    try:
        chunks_received = 0
        full_response = ""
        
        async for chunk in stream_qwen_chat(
            api_key=api_key,
            message="请用一句话介绍你自己",
            model="qwen3.8-flash",
            timeout=30.0,
        ):
            chunks_received += 1
            full_response += chunk
            print(chunk, end="", flush=True)
        
        print("\n" + "-" * 60)
        print(f"✓ 测试成功！")
        print(f"  - 收到 {chunks_received} 个数据块")
        print(f"  - 响应长度: {len(full_response)} 字符")
        return True
        
    except QwenAuthError as e:
        print(f"\n❌ 认证失败: {e}")
        print("请检查 API Key 是否正确")
        return False
    except QwenModelError as e:
        print(f"\n❌ 模型错误: {e}")
        print("可能原因：")
        print("  1. 模型 ID 'qwen3.8-flash' 不存在")
        print("  2. 账号无权限访问此模型")
        print("  3. 模型名称格式错误")
        print("\n建议：")
        print("  - 访问 DashScope 控制台查看可用模型列表")
        print("  - 尝试其他模型如: qwen-turbo, qwen-plus, qwen-max")
        return False
    except QwenServiceError as e:
        print(f"\n❌ 服务错误: {e}")
        return False
    except Exception as e:
        print(f"\n❌ 未预期错误: {type(e).__name__}: {e}")
        return False


def main():
    """Run the test."""
    success = asyncio.run(test_qwen_stream())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
