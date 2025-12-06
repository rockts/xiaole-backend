"""
轻量级语义搜索管理器
使用 TF-IDF + 余弦相似度实现语义搜索
无需深度学习模型，速度快，资源占用小，仅依赖 jieba 分词
"""

import jieba
import math
from collections import Counter
from typing import List, Tuple, Dict
from backend.logger import logger


class SemanticSearchManager:
    def __init__(self):
        """初始化分词器"""
        logger.info("✅ 初始化轻量级语义搜索")
        jieba.setLogLevel(jieba.logging.INFO)
        # 添加自定义词典（常见停用词）
        self.stopwords = set([
            '的', '了', '是', '在', '我', '有', '和', '就',
            '不', '人', '都', '一', '你', '他', '她', '它', '吗',
            '啊', '呢', '吧', '么', '什么', '这', '那', '这个'
        ])

    def add_memory(self, memory_id: int, content: str, tag: str):
        """添加记忆到索引 (轻量级版本无需持久化索引，此方法为空)"""
        pass

    def tokenize(self, text: str) -> List[str]:
        """分词并过滤停用词"""
        words = jieba.lcut(text.lower())
        return [w for w in words if w not in self.stopwords and len(w) > 1]

    def compute_tf(self, words: List[str]) -> Dict[str, float]:
        """计算词频TF"""
        word_count = Counter(words)
        total = len(words) if words else 1
        return {word: count / total for word, count in word_count.items()}

    def compute_idf(self, documents: List[List[str]]) -> Dict[str, float]:
        """计算逆文档频率IDF"""
        doc_count = len(documents)
        if doc_count == 0:
            return {}

        word_doc_count = Counter()
        for doc in documents:
            unique_words = set(doc)
            for word in unique_words:
                word_doc_count[word] += 1

        idf = {}
        for word, count in word_doc_count.items():
            idf[word] = math.log(doc_count / (count + 1))

        return idf

    def compute_tfidf(
        self,
        text: str,
        idf: Dict[str, float]
    ) -> Dict[str, float]:
        """计算TF-IDF向量"""
        words = self.tokenize(text)
        tf = self.compute_tf(words)

        tfidf = {}
        for word, tf_value in tf.items():
            idf_value = idf.get(word, 0)
            tfidf[word] = tf_value * idf_value

        return tfidf

    def cosine_similarity(
        self,
        vec1: Dict[str, float],
        vec2: Dict[str, float]
    ) -> float:
        """计算余弦相似度"""
        # 获取所有词
        all_words = set(vec1.keys()) | set(vec2.keys())

        if not all_words:
            return 0.0

        # 计算点积
        dot_product = sum(vec1.get(w, 0) * vec2.get(w, 0) for w in all_words)

        # 计算模
        norm1 = math.sqrt(sum(v ** 2 for v in vec1.values()))
        norm2 = math.sqrt(sum(v ** 2 for v in vec2.values()))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def search(
        self,
        query: str,
        documents: List[Tuple[int, str]],
        top_k: int = 5,
        min_score: float = 0.1
    ) -> List[Tuple[int, float]]:
        """
        搜索最相关的文档

        Args:
            query: 查询文本
            documents: [(id, text), ...] 文档列表
            top_k: 返回前K个
            min_score: 最小相似度阈值

        Returns:
            [(id, score), ...] 按相似度降序
        """
        if not documents:
            return []

        # 分词所有文档
        doc_words = [self.tokenize(text) for _, text in documents]
        query_words = self.tokenize(query)

        if not query_words:
            return []

        # 计算IDF
        all_docs = doc_words + [query_words]
        idf = self.compute_idf(all_docs)

        # 计算查询的TF-IDF
        query_tfidf = self.compute_tfidf(query, idf)

        # 计算每个文档的相似度
        results = []
        for (doc_id, doc_text), doc_word_list in zip(documents, doc_words):
            doc_tf = self.compute_tf(doc_word_list)
            # 计算文档的TF-IDF
            doc_tfidf = {
                w: doc_tf.get(w, 0) * idf.get(w, 0)
                for w in set(doc_word_list)
            }

            score = self.cosine_similarity(query_tfidf, doc_tfidf)

            if score >= min_score:
                results.append((doc_id, score))

        # 按分数降序排序
        results.sort(key=lambda x: x[1], reverse=True)

        return results[:top_k]


# 测试代码
if __name__ == "__main__":
    print("🧪 测试语义搜索管理器\n")

    sm = SemanticSearchManager()

    # 测试文档
    documents = [
        (1, "用户姓名：高鹏"),
        (2, "用户年龄：41岁"),
        (3, "用户生日：2月8日"),
        (4, "用户喜欢冰美式"),
        (5, "用户不喜欢体育运动"),
        (6, "用户喜欢喝咖啡")
    ]

    # 测试查询
    queries = [
        "高鹏",
        "多大",
        "41岁",
        "生日",
        "运动爱好",
        "咖啡"
    ]

    print("=" * 50)
    for query in queries:
        print(f"查询: '{query}'")
        results = sm.search(query, documents, top_k=3, min_score=0.05)

        if results:
            for doc_id, score in results:
                doc_text = next(text for id, text in documents if id == doc_id)
                print(f"  [{score:.3f}] {doc_text}")
        else:
            print("  无匹配结果")
        print()
