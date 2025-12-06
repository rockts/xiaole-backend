"""
记忆冲突检测器 - v0.3.0 Learning层
功能：自动识别矛盾的记忆信息，帮助维护记忆库的一致性
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import re
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# 数据库连接
if os.getenv('DATABASE_URL'):
    DB_URL = os.getenv('DATABASE_URL')
else:
    DB_URL = (
        f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}"
        f"/{os.getenv('DB_NAME')}"
    )

engine = create_engine(
    DB_URL,
    connect_args={'client_encoding': 'utf8'},
    pool_pre_ping=True
)
SessionLocal = sessionmaker(bind=engine)


class ConflictDetector:
    """记忆冲突检测器"""

    def __init__(self):
        # 不在init中创建长期session，避免并发问题
        # 定义关键信息的模式匹配规则
        self.patterns = {
            'name': [
                r'(?:我叫|我是|名字是|名字叫)(.{2,10})',
                r'(?:叫我|称呼我)(.{2,10})',
            ],
            'age': [
                r'(?:今年|我)(\d{1,3})岁',
                r'年龄[是:]?(\d{1,3})',
            ],
            'birthday': [
                r'生日[是:]?(\d{1,2})月(\d{1,2})[日号]',
                r'(\d{1,2})/(\d{1,2}).*生日',
            ],
            'gender': [
                r'我是(男|女)(?:生|孩|的)',
                r'性别[是:]?(男|女)',
            ],
            'location': [
                r'(?:我在|住在|来自)(.{2,20}?)(?:[，。！]|$)',
                r'(?:家在|老家是)(.{2,20}?)(?:[，。！]|$)',
            ],
            # 家庭成员扩展：女儿/儿子姓名
            'daughter_name': [
                r'(?:女儿|姑娘)[，：: ]*(?:叫|姓名[是为]|名字[是叫为])(.{1,10})',
                r'女儿姓名[是为:]?(.{1,10})',
            ],
            'son_name': [
                r'儿子[，：: ]*(?:叫|姓名[是为]|名字[是叫为])(.{1,10})',
                r'儿子姓名[是为:]?(.{1,10})',
            ],
        }

    def extract_key_info(self, text):
        """
        从文本中提取关键信息

        Args:
            text: 待分析的文本

        Returns:
            dict: {info_type: value}
        """
        extracted = {}

        def _normalize_value(v: str) -> str:
            # 去掉前导标点与空白
            v = re.sub(r'^[：:，,\s]+', '', v)
            # 若出现括号起始但未被完整捕获，直接从括号起截断
            v = re.split(r'[（(]', v)[0]
            # 去掉括号内英文别名或补充说明（中/英括号）
            v = re.sub(r'[（(][^）)]*[）)]', '', v)
            # 再次清理尾随空白
            v = v.strip()
            return v

        for info_type, pattern_list in self.patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, text)
                if match:
                    if info_type == 'birthday':
                        # 生日特殊处理：月/日
                        month, day = match.groups()
                        extracted[info_type] = f"{month}月{day}日"
                    else:
                        extracted[info_type] = _normalize_value(
                            match.group(1).strip()
                        )
                    break  # 找到第一个匹配就停止

        return extracted

    def detect_conflicts(self, tag='facts', limit=100):
        """
        检测记忆库中的冲突信息

        Args:
            tag: 记忆标签
            limit: 检查最近N条记忆

        Returns:
            list: 冲突列表 [{type, old_value, new_value, old_memory,
                            new_memory, conflict_time}]
        """
        from backend.db_setup import Memory

        # 每次创建新session
        session = SessionLocal()
        try:
            # 获取指定标签的记忆
            memories = session.query(Memory).filter(
                Memory.tag == tag
            ).order_by(Memory.created_at.desc()).limit(limit).all()

            if not memories:
                return []

            # 提取每条记忆的关键信息
            memory_info = []
            for mem in memories:
                info = self.extract_key_info(mem.content)
                if info:
                    memory_info.append({
                        'memory': mem,
                        'info': info,
                        'content': mem.content,
                        'created_at': mem.created_at
                    })

            # 检测冲突
            conflicts = []
            seen_info = {}  # {info_type: [(value, memory, created_at)]}

            for item in reversed(memory_info):  # 从旧到新检查
                for info_type, value in item['info'].items():
                    if info_type not in seen_info:
                        seen_info[info_type] = []

                    # 检查是否与之前的值冲突
                    for old_value, old_mem, old_time in seen_info[info_type]:
                        if self._is_conflict(info_type, old_value, value):
                            conflicts.append({
                                'type': info_type,
                                'type_cn': self._get_type_name(info_type),
                                'old_value': old_value,
                                'new_value': value,
                                'old_memory': old_mem.content,
                                'new_memory': item['content'],
                                'old_time': old_time,
                                'new_time': item['created_at'],
                                'conflict_detected_at': (
                                    datetime.now().isoformat()
                                )
                            })

                    # 记录当前值
                    seen_info[info_type].append(
                        (value, item['memory'], item['created_at'])
                    )

            return conflicts
        finally:
            session.close()

    def _is_conflict(self, info_type, value1, value2):
        """
        判断两个值是否冲突

        Args:
            info_type: 信息类型
            value1: 值1
            value2: 值2

        Returns:
            bool: 是否冲突
        """
        # 完全相同不算冲突
        if value1 == value2:
            return False

        # 名字冲突：完全不同才算冲突（允许昵称/全名差异）
        if info_type == 'name':
            # 如果一个是另一个的子串，可能是昵称，不算冲突
            if value1 in value2 or value2 in value1:
                return False
            return True

        # 年龄冲突：差距超过2岁才算冲突（允许生日前后差异）
        if info_type == 'age':
            try:
                age1 = int(value1)
                age2 = int(value2)
                return abs(age1 - age2) > 2
            except ValueError:
                return True

        # 其他类型：不同即冲突
        return True

    def _get_type_name(self, info_type):
        """获取信息类型的中文名称"""
        names = {
            'name': '姓名',
            'age': '年龄',
            'birthday': '生日',
            'gender': '性别',
            'location': '地址',
            'daughter_name': '女儿姓名',
            'son_name': '儿子姓名',
        }
        return names.get(info_type, info_type)

    def get_conflict_summary(self):
        """
        获取冲突摘要报告

        Returns:
            dict: 冲突摘要
        """
        conflicts = self.detect_conflicts()

        if not conflicts:
            return {
                'has_conflicts': False,
                'total_conflicts': 0,
                'message': '✅ 记忆库无冲突'
            }

        # 按类型统计
        by_type = {}
        for c in conflicts:
            type_cn = c['type_cn']
            if type_cn not in by_type:
                by_type[type_cn] = []
            by_type[type_cn].append(c)

        return {
            'has_conflicts': True,
            'total_conflicts': len(conflicts),
            'conflicts_by_type': by_type,
            'conflicts': conflicts,
            'message': f'⚠️  发现 {len(conflicts)} 个记忆冲突'
        }

    def generate_conflict_report(self):
        """
        生成友好的冲突报告文本

        Returns:
            str: 格式化的冲突报告
        """
        summary = self.get_conflict_summary()

        if not summary['has_conflicts']:
            return summary['message']

        report = [
            "="*60,
            "⚠️  记忆冲突检测报告",
            "="*60,
            f"\n发现 {summary['total_conflicts']} 个冲突：\n"
        ]

        def _fmt_time(t):
            if not t:
                return '未知'
            try:
                return t.strftime('%Y-%m-%d')
            except Exception:
                return str(t)

        for i, conflict in enumerate(summary['conflicts'], 1):
            report.append(f"\n【冲突 {i}】{conflict['type_cn']}")
            report.append(f"  旧值: {conflict['old_value']}")
            report.append(f"  新值: {conflict['new_value']}")
            report.append(f"  旧记忆: {conflict['old_memory'][:50]}...")
            report.append(f"  新记忆: {conflict['new_memory'][:50]}...")
            report.append(
                "  时间: "
                + _fmt_time(conflict['old_time'])
                + " → "
                + _fmt_time(conflict['new_time'])
            )

        report.append("\n" + "="*60)
        report.append("建议：请检查并更新正确的信息")
        report.append("="*60)

        return "\n".join(report)

    def auto_resolve_conflicts(self, strategy='keep_latest'):
        """
        自动解决冲突（谨慎使用）

        Args:
            strategy: 解决策略
                - 'keep_latest': 保留最新的信息
                - 'keep_oldest': 保留最旧的信息
                - 'mark_only': 仅标记，不删除

        Returns:
            dict: 处理结果
        """
        conflicts = self.detect_conflicts()

        if not conflicts:
            return {'resolved': 0, 'message': '无需处理'}

        # 暂时只支持标记
        if strategy == 'mark_only':
            return {
                'resolved': 0,
                'marked': len(conflicts),
                'message': f'已标记 {len(conflicts)} 个冲突待人工处理'
            }

        # TODO: 实现自动删除策略（需要更多测试）
        return {
            'resolved': 0,
            'message': '自动解决功能开发中，请使用 mark_only 策略'
        }


if __name__ == '__main__':
    detector = ConflictDetector()
    print(detector.generate_conflict_report())
