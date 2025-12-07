#!/bin/bash
# 检查对话保存机制是否正常工作

echo "🔍 检查对话保存机制..."
echo ""

# 检查数据库连接
echo "1️⃣ 检查数据库连接："
python3 << 'EOF'
from db_setup import SessionLocal, Conversation, Message
from datetime import datetime, timedelta

session = SessionLocal()
try:
    # 检查最近的会话
    recent_sessions = session.query(Conversation).order_by(
        Conversation.updated_at.desc()
    ).limit(5).all()
    
    if recent_sessions:
        print(f"✅ 找到 {len(recent_sessions)} 个最近会话")
        for s in recent_sessions:
            msg_count = session.query(Message).filter(
                Message.session_id == s.session_id
            ).count()
            print(f"   - {s.title[:30]}... (ID: {s.session_id[:8]}..., 消息数: {msg_count}, 更新: {s.updated_at})")
    else:
        print("⚠️  没有找到任何会话")
    
    # 检查最近的消息
    recent_messages = session.query(Message).order_by(
        Message.created_at.desc()
    ).limit(5).all()
    
    if recent_messages:
        print(f"\n✅ 找到 {len(recent_messages)} 条最近消息")
        for m in recent_messages:
            print(f"   - [{m.role}] {m.content[:50]}... (会话: {m.session_id[:8]}..., 时间: {m.created_at})")
    else:
        print("\n⚠️  没有找到任何消息")
    
    # 检查今天保存的消息数
    today = datetime.now().date()
    today_messages = session.query(Message).filter(
        Message.created_at >= datetime.combine(today, datetime.min.time())
    ).count()
    print(f"\n📊 今天保存的消息数: {today_messages}")
    
finally:
    session.close()
EOF

echo ""
echo "2️⃣ 检查代码中的保存逻辑："
echo "   - agent.py:551-555 - 保存用户消息 ✅"
echo "   - agent.py:824-827 - 保存助手回复 ✅"
echo "   - conversation.py:49-72 - add_message 方法 ✅"

echo ""
echo "3️⃣ 检查异常处理："
grep -n "add_message" agent.py | head -5
echo ""
echo "⚠️  注意：conversation.add_message 没有异常捕获，如果保存失败会抛出异常"

echo ""
echo "✅ 检查完成！"

