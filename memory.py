from sqlalchemy import func, or_
from backend.db_setup import Memory, SessionLocal
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from backend.semantic_search import SemanticSearchManager

load_dotenv()

# 使用统一的 Session 工厂
Session = SessionLocal


class MemoryManager:
    def __init__(self, enable_vector_search=True):  # 默认启用语义搜索
        self.enable_vector_search = enable_vector_search

        # 初始化语义搜索管理器
        if self.enable_vector_search:
            try:
                self.semantic_search = SemanticSearchManager()
                print("✅ 语义搜索已启用")
            except Exception as e:
                print(f"⚠️ 语义搜索初始化失败: {e}，降级到关键词搜索")
                self.enable_vector_search = False
                self.semantic_search = None
        else:
            self.semantic_search = None

    def remember(
        self,
        content,
        tag="general",
        initial_importance=0.5,
        image_path=None
    ):
        """
        Store memory with importance score.

        Args:
            content: memory content
            tag: tag/category
            initial_importance: importance score (0-1) - 暂时未使用，等待数据库迁移
            image_path: 可选，关联的图片相对路径（例如 /uploads/images/xxx.jpg）
        """
        session = Session()
        try:
            # 去重检查：如果是 facts 标签，检查是否已存在相同内容
            if tag == "facts":
                existing = session.query(Memory).filter(
                    Memory.tag == "facts",
                    Memory.content == content
                ).first()

                if existing:
                    print(f"⚠️ 跳过重复 facts: {content[:50]}")
                    return existing.id

            # 如提供了 image_path，但 Memory 模型暂无该列，则将其内嵌到内容中
            final_content = content
            if image_path:
                prefix = f"[image_path:{image_path}]\n"
                final_content = f"{prefix}{content}" if content else prefix

            memory = Memory(
                content=final_content,
                tag=tag
                # importance_score 字段需要数据库迁移后才能使用
            )
            session.add(memory)
            session.commit()

            # 添加到语义搜索索引
            if self.enable_vector_search and self.semantic_search:
                try:
                    self.semantic_search.add_memory(memory.id, content, tag)
                except Exception as e:
                    print(f"添加语义索引失败: {e}")

            return memory.id
        finally:
            session.close()

    def recall(self, tag="general", keyword=None, limit=None):
        """Recall memories by tag and keyword"""
        session = Session()
        try:
            # Support prefix matching for tags (case-insensitive)
            if tag:
                tag_lower = tag.lower()
                query = session.query(Memory).filter(
                    or_(
                        func.lower(Memory.tag) == tag_lower,
                        func.lower(Memory.tag).like(f"{tag_lower}:%")
                    )
                )
            else:
                query = session.query(Memory)

            # 如果有关键词，进行模糊搜索
            if keyword:
                query = query.filter(Memory.content.contains(keyword))

            # 按时间倒序
            query = query.order_by(Memory.created_at.desc())

            # 限制数量
            if limit:
                query = query.limit(limit)

            memories = query.all()
            return [m.content for m in memories]
        finally:
            session.close()

    def recall_recent(self, hours=24, tag=None, limit=10):
        """Recall recent memories within specified hours"""
        session = Session()
        try:
            time_threshold = datetime.now() - timedelta(hours=hours)

            query = session.query(Memory).filter(
                Memory.created_at >= time_threshold
            )

            if tag:
                # Support prefix matching for tags (case-insensitive)
                tag_lower = tag.lower()
                print(f"DEBUG: Filtering tag with prefix: {tag_lower}")

                # Case-insensitive matching via lower() and prefix match
                # Try both exact match and prefix match
                query = query.filter(
                    or_(
                        func.lower(Memory.tag) == tag_lower,
                        func.lower(Memory.tag).like(f"{tag_lower}:%")
                    )
                )

                # Debug: Print generated SQL (best-effort)
                try:
                    compiled = query.statement.compile(
                        compile_kwargs={'literal_binds': True}
                    )
                    print(f"DEBUG SQL: {compiled}")
                except Exception:
                    pass

            query = query.order_by(Memory.created_at.desc()).limit(limit)
            memories = query.all()

            # 返回完整对象信息，供前端显示
            return [{
                'id': m.id,
                'content': m.content,
                'tag': m.tag,
                'timestamp': m.created_at.strftime('%Y-%m-%d %H:%M:%S')
            } for m in memories]
        finally:
            session.close()

    def recall_by_keywords(self, keywords, tag=None, limit=10):
        """Search memories by multiple keywords with OR logic"""
        if not keywords:
            return []

        session = Session()
        try:
            # 构建关键词过滤条件
            keyword_filters = [
                Memory.content.contains(kw) for kw in keywords
            ]

            query = session.query(Memory).filter(or_(*keyword_filters))

            if tag:
                # Support prefix matching for tags (case-insensitive)
                tag_lower = tag.lower()
                query = query.filter(
                    or_(
                        func.lower(Memory.tag) == tag_lower,
                        func.lower(Memory.tag).like(f"{tag_lower}:%")
                    )
                )

            query = query.order_by(Memory.created_at.desc()).limit(limit)
            memories = query.all()

            # 返回完整的记忆信息
            return [{
                'id': m.id,
                'content': m.content,
                'tag': m.tag,
                'timestamp': m.created_at.strftime('%Y-%m-%d %H:%M:%S')
            } for m in memories]
        finally:
            session.close()

    def get_stats(self):
        """Get memory statistics"""
        session = Session()
        try:
            # 总记忆数
            total = session.query(func.count(Memory.id)).scalar()

            # 按标签统计
            tag_stats = session.query(
                Memory.tag,
                func.count(Memory.id)
            ).group_by(Memory.tag).all()

            return {
                "total": total,
                "by_tag": {tag: count for tag, count in tag_stats}
            }
        finally:
            session.close()

    def semantic_recall(self, query, tag=None, limit=10, min_score=0.15):
        """Semantic search using TF-IDF and cosine similarity"""
        if not self.enable_vector_search or not self.semantic_search:
            # 降级到关键词搜索
            print("⚠️ 语义搜索不可用，使用关键词搜索")
            keywords = query.split()
            return self.recall_by_keywords(keywords, tag=tag, limit=limit)

        session = Session()
        try:
            # 查询所有记忆
            query_obj = session.query(Memory)
            if tag:
                # Support prefix matching for tags (case-insensitive)
                tag_lower = tag.lower()
                query_obj = query_obj.filter(
                    or_(
                        func.lower(Memory.tag) == tag_lower,
                        func.lower(Memory.tag).like(f"{tag_lower}:%")
                    )
                )

            all_memories = query_obj.all()

            if not all_memories:
                return []

            # 构建文档列表：(id, content)
            documents = [(m.id, m.content) for m in all_memories]

            # 执行语义搜索
            results = self.semantic_search.search(
                query=query,
                documents=documents,
                top_k=limit,
                min_score=min_score
            )

            if not results:
                return []

            # 获取匹配的记忆详情
            result_ids = [mem_id for mem_id, _ in results]
            id_to_score = {mem_id: score for mem_id, score in results}

            matched_memories = session.query(Memory).filter(
                Memory.id.in_(result_ids)
            ).all()

            # v0.6.0: 更新访问记录 (需要数据库迁移后启用)
            # for mem in matched_memories:
            #     self._update_access(mem.id)

            # 按相似度排序并返回
            memories_with_scores = [
                {
                    'id': m.id,
                    'content': m.content,
                    'tag': m.tag,
                    'timestamp': m.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'score': id_to_score.get(m.id, 0)
                }
                for m in matched_memories
            ]

            # 按分数降序排序
            memories_with_scores.sort(key=lambda x: x['score'], reverse=True)

            return memories_with_scores

        except Exception as e:
            print(f"⚠️ 语义搜索失败: {e}，降级到关键词搜索")
            keywords = query.split()
            return self.recall_by_keywords(keywords, tag=tag, limit=limit)
        finally:
            session.close()

    # v0.6.0 Phase 3方法: 需要数据库迁移后启用
    # def _update_access(self, memory_id):
    #     """更新记忆访问记录"""
    #     mem = self.session.query(Memory).filter(
    #         Memory.id == memory_id
    #     ).first()
    #     if mem:
    #         mem.access_count = (mem.access_count or 0) + 1
    #         mem.last_accessed_at = datetime.now()
    #         self.session.commit()
    #
    # def calculate_importance(self, memory_id):
    #     """计算记忆的重要性分数"""
    #     ...
    #
    # def update_all_importance_scores(self):
    #     """批量更新所有记忆的重要性分数"""
    #     ...
    #
    # def get_top_memories(self, limit=20, tag=None):
    #     """获取最重要的记忆"""
    #     ...
    #
    # def auto_archive_low_importance(self, threshold=0.1, min_age_days=30):
    #     """自动归档低重要性记忆"""
    #     ...

    def calculate_importance(self, memory_id):
        """
        v0.6.0: 计算记忆的重要性分数

        考虑因素:
        1. 访问频率 (40 %)
        2. 时间衰减 (30 %)
        3. 标签类型 (30 %)

        Returns:
            float: 重要性分数(0-1)
        """
        session = Session()
        try:
            mem = session.query(Memory).filter(
                Memory.id == memory_id
            ).first()

            if not mem:
                return 0.0

            # 1. 访问频率分数 (0-1)
            # 访问次数越多越重要，使用对数函数避免线性增长
            import math
            access_score = min(
                math.log(mem.access_count + 1) / math.log(100),
                1.0
            )

            # 2. 时间衰减分数 (0-1)
            # 最近的记忆更重要，使用指数衰减
            days_ago = (datetime.now() - mem.created_at).days
            time_score = math.exp(-days_ago / 30.0)  # 30天半衰期

            # 3. 标签权重 (0-1)
            tag_weights = {
                'facts': 1.0,      # 用户明确告知的事实最重要
                'task': 0.8,       # 任务记录次重要
                'general': 0.5,    # 普通对话中等重要
                'system': 0.3      # 系统日志较不重要
            }
            tag_score = tag_weights.get(mem.tag, 0.5)

            # Weighted average calculation
            importance = (
                access_score * 0.4 +
                time_score * 0.3 +
                tag_score * 0.3
            )

            # 更新数据库
            mem.importance_score = importance
            session.commit()

            return importance
        finally:
            session.close()

    def update_all_importance_scores(self):
        """
        v0.6.0: 批量更新所有记忆的重要性分数

        Returns:
            int: 更新的记忆数量
        """
        session = Session()
        try:
            all_memories = session.query(Memory).filter(
                Memory.is_archived == False  # noqa: E712
            ).all()

            updated_count = 0
            # 注意：这里调用了 self.calculate_importance，它内部也会创建 Session
            # 为了避免嵌套 Session 问题，我们应该重构 calculate_importance 或者在这里直接计算
            # 但为了简单起见，我们先获取 ID 列表，然后逐个调用
            memory_ids = [m.id for m in all_memories]
        finally:
            session.close()

        for mem_id in memory_ids:
            self.calculate_importance(mem_id)
            updated_count += 1

        print(f"✅ 已更新 {updated_count} 条记忆的重要性分数")
        return updated_count

    def get_top_memories(self, limit=20, tag=None):
        """
        v0.6.0: 获取最重要的记忆

        Args:
            limit: 返回数量
            tag: 可选标签过滤

        Returns:
            [{content, tag, importance_score, access_count}]
        """
        session = Session()
        try:
            query = session.query(Memory).filter(
                Memory.is_archived == False  # noqa: E712
            )

            if tag:
                query = query.filter(Memory.tag == tag)

            query = query.order_by(
                Memory.importance_score.desc()
            ).limit(limit)

            memories = query.all()

            return [{
                'content': m.content,
                'tag': m.tag,
                'importance_score': m.importance_score,
                'access_count': m.access_count,
                'created_at': m.created_at.strftime('%Y-%m-%d %H:%M:%S')
            } for m in memories]
        finally:
            session.close()

    def auto_archive_low_importance(self, threshold=0.1, min_age_days=30):
        """
        v0.6.0: 自动归档低重要性记忆

        归档策略:
        - 重要性分数 < threshold
        - 创建时间 > min_age_days 天
        - 访问次数 <= 1

        Args:
            threshold: importance threshold (0-1)
            min_age_days: minimum age in days

        Returns:
            int: archived count
        """
        from datetime import timedelta
        session = Session()
        try:
            cutoff_date = datetime.now() - timedelta(days=min_age_days)

            # 查找需要归档的记忆
            low_importance_memories = session.query(Memory).filter(
                Memory.is_archived == False,  # noqa: E712
                Memory.importance_score < threshold,
                Memory.created_at < cutoff_date,
                Memory.access_count <= 1
            ).all()

            archived_count = 0
            for mem in low_importance_memories:
                mem.is_archived = True
                archived_count += 1

            session.commit()

            if archived_count > 0:
                print(f"✅ 已归档 {archived_count} 条低重要性记忆")

            return archived_count
        finally:
            session.close()

    def get_memory_stats(self):
        """Get memory statistics with importance analysis"""
        session = Session()
        try:
            # 基础统计
            total = session.query(func.count(Memory.id)).scalar()
            archived = session.query(func.count(Memory.id)).filter(
                Memory.is_archived == True  # noqa: E712
            ).scalar()
            active = total - archived

            # 按标签统计
            tag_stats = session.query(
                Memory.tag,
                func.count(Memory.id)
            ).filter(
                Memory.is_archived == False  # noqa: E712
            ).group_by(Memory.tag).all()

            # 重要性分布
            high_importance = session.query(func.count(Memory.id)).filter(
                Memory.is_archived == False,  # noqa: E712
                Memory.importance_score >= 0.7
            ).scalar()

            medium_importance = session.query(func.count(Memory.id)).filter(
                Memory.is_archived == False,  # noqa: E712
                Memory.importance_score >= 0.3,
                Memory.importance_score < 0.7
            ).scalar()

            low_importance = session.query(func.count(Memory.id)).filter(
                Memory.is_archived == False,  # noqa: E712
                Memory.importance_score < 0.3
            ).scalar()

            return {
                "total": total,
                "active": active,
                "archived": archived,
                "by_tag": {tag: count for tag, count in tag_stats},
                "importance_distribution": {
                    "high (≥0.7)": high_importance,
                    "medium (0.3-0.7)": medium_importance,
                    "low (<0.3)": low_importance
                }
            }
        finally:
            session.close()

    def cleanup_old_conversations(self, days=7):
        """
        清理超过指定天数的 conversation 记忆

        Args:
            days: 保留天数，默认7天

        Returns:
            删除的记忆数量
        """
        session = Session()
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            old_conversations = session.query(Memory).filter(
                Memory.tag.like('conversation:%'),
                Memory.created_at < cutoff_date
            ).all()

            count = len(old_conversations)
            for mem in old_conversations:
                session.delete(mem)

            session.commit()
            print(f"🗑️ 清理了 {count} 条超过{days}天的conversation记忆")
            return count
        finally:
            session.close()
