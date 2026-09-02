#!/usr/bin/env python3
"""Verify refactoring maintains API compatibility."""

import sys


def test_imports():
    """Test that all imports work correctly."""
    print("\n" + "=" * 60)
    print("🧪 测试导入兼容性")
    print("=" * 60)
    
    # Test new AI control layer
    print("\n1️⃣ 测试 AI 控制层导入...")
    try:
        from app.ai import (
            execute_chat,
            ChatContext,
            ChatMessage,
            AIAuthError,
            AIModelError,
            AIRateLimitError,
            AIServiceError,
        )
        print("  ✅ AI 控制层导入成功")
    except Exception as e:
        print(f"  ❌ AI 控制层导入失败: {e}")
        return False
    
    # Test backward compatibility
    print("\n2️⃣ 测试向后兼容导入...")
    try:
        from app.services.qwen import (
            stream_qwen_chat,
            stream_qwen_chat_with_context,
            QwenAuthError,
            QwenModelError,
            QwenRateLimitError,
            QwenServiceError,
        )
        print("  ✅ 向后兼容导入成功")
    except Exception as e:
        print(f"  ❌ 向后兼容导入失败: {e}")
        return False
    
    # Test chat routes
    print("\n3️⃣ 测试聊天路由导入...")
    try:
        from app.api.routes.chat import router
        print("  ✅ 聊天路由导入成功")
    except Exception as e:
        print(f"  ❌ 聊天路由导入失败: {e}")
        return False
    
    return True


def test_api_structure():
    """Test that API structure is unchanged."""
    print("\n" + "=" * 60)
    print("🧪 测试 API 结构")
    print("=" * 60)
    
    from app.api.routes.chat import router
    
    print("\n1️⃣ 验证路由路径...")
    expected_routes = {
        "/chat/stream",
        "/chat/sessions",
        "/chat/sessions/{session_id}",
    }
    
    actual_routes = {route.path for route in router.routes}
    
    for expected in expected_routes:
        if expected in actual_routes:
            print(f"  ✅ {expected}")
        else:
            print(f"  ❌ 缺失路由: {expected}")
            return False
    
    return True


def test_schema_compatibility():
    """Test that schemas are unchanged."""
    print("\n" + "=" * 60)
    print("🧪 测试 Schema 兼容性")
    print("=" * 60)
    
    from app.schemas.chat import ChatRequest, ChatStreamEvent
    
    print("\n1️⃣ 测试 ChatRequest...")
    try:
        req = ChatRequest(message="test", session_id=None)
        assert req.message == "test"
        assert req.session_id is None
        print("  ✅ ChatRequest 结构正确")
    except Exception as e:
        print(f"  ❌ ChatRequest 失败: {e}")
        return False
    
    print("\n2️⃣ 测试 ChatStreamEvent...")
    try:
        events = [
            ChatStreamEvent(type="session", session_id=123),
            ChatStreamEvent(type="content", content="hello"),
            ChatStreamEvent(type="done"),
            ChatStreamEvent(type="error", error="test"),
        ]
        assert len(events) == 4
        print("  ✅ ChatStreamEvent 结构正确")
    except Exception as e:
        print(f"  ❌ ChatStreamEvent 失败: {e}")
        return False
    
    return True


def test_exception_hierarchy():
    """Test that exception hierarchy is correct."""
    print("\n" + "=" * 60)
    print("🧪 测试异常层次结构")
    print("=" * 60)
    
    # Test AI control layer exceptions
    print("\n1️⃣ 测试 AI 控制层异常...")
    from app.ai import AIAuthError, AIModelError, AIRateLimitError, AIServiceError
    
    for exc_type in [AIAuthError, AIModelError, AIRateLimitError, AIServiceError]:
        assert issubclass(exc_type, Exception)
        print(f"  ✅ {exc_type.__name__}")
    
    # Test backward compatible exceptions
    print("\n2️⃣ 测试向后兼容异常...")
    from app.services.qwen import QwenAuthError, QwenModelError, QwenRateLimitError, QwenServiceError
    
    for exc_type in [QwenAuthError, QwenModelError, QwenRateLimitError, QwenServiceError]:
        assert issubclass(exc_type, Exception)
        print(f"  ✅ {exc_type.__name__}")
    
    return True


def test_function_signatures():
    """Test that function signatures are correct."""
    print("\n" + "=" * 60)
    print("🧪 测试函数签名")
    print("=" * 60)
    
    import inspect
    
    # Test AI control layer
    print("\n1️⃣ 测试 execute_chat...")
    from app.ai import execute_chat
    sig = inspect.signature(execute_chat)
    params = list(sig.parameters.keys())
    assert "api_key" in params
    assert "context" in params
    print(f"  ✅ 参数: {params}")
    
    # Test backward compatible functions
    print("\n2️⃣ 测试 stream_qwen_chat...")
    from app.services.qwen import stream_qwen_chat
    sig = inspect.signature(stream_qwen_chat)
    params = list(sig.parameters.keys())
    assert "api_key" in params
    assert "message" in params
    assert "model" in params
    print(f"  ✅ 参数: {params}")
    
    print("\n3️⃣ 测试 stream_qwen_chat_with_context...")
    from app.services.qwen import stream_qwen_chat_with_context
    sig = inspect.signature(stream_qwen_chat_with_context)
    params = list(sig.parameters.keys())
    assert "api_key" in params
    assert "context" in params
    assert "user_nickname" in params
    print(f"  ✅ 参数: {params}")
    
    return True


def main():
    """Run all compatibility tests."""
    print("\n" + "=" * 60)
    print("🔍 AI 控制层重构 - 兼容性验证")
    print("=" * 60)
    
    tests = [
        ("导入兼容性", test_imports),
        ("API 结构", test_api_structure),
        ("Schema 兼容性", test_schema_compatibility),
        ("异常层次结构", test_exception_hierarchy),
        ("函数签名", test_function_signatures),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} 测试异常: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {status} - {name}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n" + "=" * 60)
        print("🎉 所有兼容性测试通过！")
        print("=" * 60 + "\n")
        return 0
    else:
        print("\n" + "=" * 60)
        print("❌ 部分测试失败")
        print("=" * 60 + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
