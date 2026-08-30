#!/usr/bin/env python3
"""Environment check script for CourseMind Qwen integration.

Run this script before starting the backend to verify all prerequisites.
"""
import os
import sys


def check_python_version():
    """Check Python version."""
    version = sys.version_info
    if version.major == 3 and version.minor >= 11:
        print(f"✓ Python 版本: {version.major}.{version.minor}.{version.micro} (满足要求 >= 3.11)")
        return True
    else:
        print(f"✗ Python 版本: {version.major}.{version.minor}.{version.micro} (要求 >= 3.11)")
        return False


def check_api_key():
    """Check if DASHSCOPE_API_KEY is configured."""
    key = os.getenv("DASHSCOPE_API_KEY", "")
    if key:
        print(f"✓ DASHSCOPE_API_KEY: 已配置 (长度 {len(key)})")
        return True
    else:
        print("✗ DASHSCOPE_API_KEY: 未配置")
        print("  请设置环境变量: export DASHSCOPE_API_KEY=your_key")
        return False


def check_dependencies():
    """Check if required dependencies are installed."""
    required = ["fastapi", "uvicorn", "httpx", "pydantic", "pydantic_settings"]
    missing = []
    
    for pkg in required:
        try:
            __import__(pkg.replace("-", "_"))
            print(f"✓ {pkg}: 已安装")
        except ImportError:
            print(f"✗ {pkg}: 未安装")
            missing.append(pkg)
    
    if missing:
        print(f"\n缺少依赖: {', '.join(missing)}")
        print("运行: pip install -e \".[dev]\"")
        return False
    return True


def check_project_structure():
    """Check if project structure is correct."""
    expected_files = [
        "app/main.py",
        "app/core/config.py",
        "app/services/qwen.py",
        "app/api/routes/chat.py",
        "app/schemas/chat.py",
    ]
    
    all_exist = True
    for filepath in expected_files:
        if os.path.exists(filepath):
            print(f"✓ {filepath}: 存在")
        else:
            print(f"✗ {filepath}: 不存在")
            all_exist = False
    
    return all_exist


def main():
    """Run all checks."""
    print("=" * 60)
    print("CourseMind Qwen 集成环境检查")
    print("=" * 60)
    print()
    
    checks = [
        ("Python 版本", check_python_version),
        ("API Key", check_api_key),
        ("依赖包", check_dependencies),
        ("项目结构", check_project_structure),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n检查 {name}:")
        print("-" * 60)
        result = check_func()
        results.append(result)
    
    print("\n" + "=" * 60)
    if all(results):
        print("✓ 所有检查通过！可以启动后端服务器。")
        print("\n启动命令:")
        print("  uvicorn app.main:app --reload --port 8000")
        return 0
    else:
        print("✗ 部分检查未通过，请先解决上述问题。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
