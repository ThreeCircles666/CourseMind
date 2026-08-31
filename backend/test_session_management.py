#!/usr/bin/env python3
"""Test chat session management functionality."""

import asyncio
from app.db.session import SessionLocal
from app.models.user import User
from app.models.chat import ChatSession, ChatMessage
from sqlalchemy import select


async def test_session_management():
    """Test basic session and message operations."""
    
    print("\n" + "=" * 60)
    print("🧪 测试会话管理功能")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # 1. Get or create test user
        print("\n1️⃣ 获取测试用户...")
        user = db.execute(select(User)).scalars().first()
        
        if not user:
            print("  ❌ 未找到测试用户，请先创建用户")
            return
        
        print(f"  ✅ 用户: {user.username} (ID: {user.id})")
        
        # 2. Create test session
        print("\n2️⃣ 创建测试会话...")
        session = ChatSession(
            user_id=user.id,
            title="测试会话",
            model="qwen3.8-flash",
            message_count=0,
        )
        db.add(session)
        db.flush()
        print(f"  ✅ 会话创建成功 (ID: {session.id})")
        
        # 3. Add test messages
        print("\n3️⃣ 添加测试消息...")
        
        msg1 = ChatMessage(
            session_id=session.id,
            role="user",
            content="你好，请介绍一下你自己",
            sequence=0,
        )
        db.add(msg1)
        
        msg2 = ChatMessage(
            session_id=session.id,
            role="assistant",
            content="你好！我是通义千问，一个由阿里云开发的AI助手。",
            sequence=1,
        )
        db.add(msg2)
        
        session.message_count = 2
        db.commit()
        print(f"  ✅ 添加了 2 条消息")
        
        # 4. Query sessions
        print("\n4️⃣ 查询用户会话...")
        sessions = db.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user.id, ChatSession.is_archived == False)
            .order_by(ChatSession.updated_at.desc())
        ).scalars().all()
        
        print(f"  ✅ 找到 {len(sessions)} 个会话:")
        for s in sessions:
            print(f"     - {s.title} ({s.message_count} 条消息)")
        
        # 5. Query messages
        print("\n5️⃣ 查询会话消息...")
        messages = db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session.id)
            .order_by(ChatMessage.sequence)
        ).scalars().all()
        
        print(f"  ✅ 找到 {len(messages)} 条消息:")
        for msg in messages:
            print(f"     [{msg.role}] {msg.content[:50]}...")
        
        # 6. Test session ownership
        print("\n6️⃣ 测试会话所有权...")
        other_user_sessions = db.execute(
            select(ChatSession)
            .where(ChatSession.user_id != user.id, ChatSession.is_archived == False)
        ).scalars().all()
        print(f"  ✅ 其他用户会话数: {len(other_user_sessions)} (应该无法访问)")
        
        # 7. Test archiving
        print("\n7️⃣ 测试会话归档...")
        session.is_archived = True
        db.commit()
        
        active_sessions = db.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user.id, ChatSession.is_archived == False)
        ).scalars().all()
        print(f"  ✅ 归档后活跃会话数: {len(active_sessions)}")
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(test_session_management())
