"""
网络搜索工具 (v0.6.2 优化版)
使用 DuckDuckGo 进行网络搜索
新增功能：错误重试、结果缓存、搜索历史、多策略搜索、代理支持
v0.6.1: 升级到ddgs包,改进搜索稳定性
v0.6.2: 添加代理支持和超时优化
"""
from backend.tool_manager import Tool, ToolParameter
try:
    from duckduckgo_search import DDGS
except ImportError:
    try:
        from ddgs import DDGS
    except ImportError:
        DDGS = None
import asyncio
import time
import os
import requests  # v0.6.4: Bing Search fallback
from typing import List, Dict, Optional


class SearchTool(Tool):
    """网络搜索工具"""

    def __init__(self):
        super().__init__()
        self.name = "search"
        self.description = (
            "网络搜索工具 - 使用DuckDuckGo获取实时信息。"
            "必须使用的场景："
            "1.用户明确要求搜索(搜索/查一下/帮我找)；"
            "2.询问最新产品信息(iPhone17/16等2024年后产品)；"
            "3.询问实时新闻、价格、发布时间；"
            "4.涉及2024年9月后的信息；"
            "5.AI知识可能过时的内容。"
            "返回搜索结果的标题、摘要和链接。"
        )
        self.parameters = [
            ToolParameter(
                name="query",
                param_type="string",
                description="搜索关键词或问题",
                required=True
            ),
            ToolParameter(
                name="max_results",
                param_type="integer",
                description="最大返回结果数量，默认5条",
                required=False,
                default=5
            ),
            ToolParameter(
                name="timelimit",
                param_type="string",
                description="时间限制 (d:一天内, w:一周内, m:一月内, y:一年内)",
                required=False,
                default=None,
                enum=["d", "w", "m", "y"]
            )
        ]

        # === v0.6.0 新增：结果缓存 ===
        self.cache = {}  # {query: (result, timestamp)}
        self.cache_ttl = 300  # 5分钟缓存

        # === v0.6.0 新增：搜索历史 ===
        self.search_history = []  # [(query, timestamp, success)]
        self.max_history = 50

        # === v0.6.0 新增：重试配置 ===
        self.max_retries = 3
        self.retry_delay = 1  # 秒

        # === v0.6.2 新增：代理和超时配置 ===
        # 从环境变量读取代理
        self.proxy = os.getenv('HTTP_PROXY') or os.getenv('HTTPS_PROXY')
        self.timeout = 15  # 每次搜索超时时间（秒）

        # === v0.6.4 新增：Bing Search 备用源 ===
        self.bing_api_key = os.getenv('BING_SEARCH_API_KEY')

        if self.proxy:
            print(f"✅ 搜索工具已启用代理: {self.proxy}")
        if self.bing_api_key:
            print("✅ 搜索工具已启用 Bing Search 备用源")

    async def execute(self, **kwargs) -> Dict:
        """
        执行搜索 (v0.6.0 优化版：带缓存和重试)

        Args:
            query: 搜索关键词
            max_results: 最大结果数，默认5
            timelimit: 时间限制 (d/w/m/y)

        Returns:
            Dict: 包含搜索结果的字典
        """
        query = kwargs.get("query")
        max_results = kwargs.get("max_results", 5)
        timelimit = kwargs.get("timelimit")

        if not query:
            return {
                "success": False,
                "error": "搜索关键词不能为空"
            }

        # 自动推断时间限制
        if not timelimit:
            import datetime
            current_year = datetime.datetime.now().year
            next_year = current_year + 1

            lower_query = query.lower()
            if any(k in lower_query for k in ["最新", "最近", "news", "latest", "today", "今天"]):
                timelimit = "w"  # 默认一周内
                print(f"ℹ️ 自动设置时间限制: {timelimit} (检测到最新/新闻关键词)")
            elif any(k in lower_query for k in ["本月", "this month"]):
                timelimit = "m"
            elif any(k in lower_query for k in ["今年", "this year", str(current_year), str(next_year)]):
                timelimit = "y"

        # === v0.6.0 新增：检查缓存 ===
        # 缓存键包含 timelimit
        cache_key = f"{query}_{timelimit}" if timelimit else query
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            print(f"✅ 使用缓存结果: {cache_key}")
            return cached_result

        # === v0.6.0 新增：带重试的搜索 ===
        for attempt in range(self.max_retries):
            try:
                # 使用 DuckDuckGo 搜索
                results = await self._search_ddg(query, max_results, timelimit)

                if not results:
                    # 搜索失败或无结果
                    result = {
                        "success": False,
                        "data": (
                            f"搜索'{query}'未找到结果。\n"
                            "可能原因:\n"
                            "1. DuckDuckGo搜索API暂时不可用\n"
                            "2. 查询关键词过于具体或罕见\n"
                            "3. 网络连接问题\n\n"
                            "建议: 基于已有知识回答,并说明信息可能不是最新的。"
                        ),
                        "results": [],
                        "count": 0,
                        "error": "搜索无结果"
                    }
                else:
                    # 格式化结果
                    formatted_results = self._format_results(results)
                    result = {
                        "success": True,
                        "data": formatted_results,
                        "results": results,
                        "count": len(results)
                    }

                # === v0.6.0 新增：缓存结果 ===
                self._cache_result(cache_key, result)

                # === v0.6.0 新增：记录历史 ===
                self._add_to_history(query, len(results) > 0)

                return result

            except Exception as e:
                error_msg = str(e)

                # 最后一次尝试失败
                if attempt == self.max_retries - 1:
                    print(f"❌ 搜索失败（已重试{self.max_retries}次）: {error_msg}")

                    # === v0.6.0 新增：记录失败历史 ===
                    self._add_to_history(query, False)

                    return {
                        "success": False,
                        "error": f"搜索服务暂时不可用: {error_msg[:100]}",
                        "data": (
                            "网络搜索暂时失败,无法获取最新信息。\n"
                            "建议: 使用已有知识回答,并明确告知用户信息可能过时,建议自行验证。"
                        ),
                        "suggestion": "基于训练数据回答,并说明可能不准确"
                    }

                # 还有重试机会
                retry_msg = (
                    f"⚠️  搜索失败，{self.retry_delay}秒后重试 "
                    f"({attempt + 1}/{self.max_retries}): {error_msg}"
                )
                print(retry_msg)
                await asyncio.sleep(self.retry_delay)

    def _get_cached_result(self, query: str) -> Dict:
        """
        获取缓存的搜索结果

        Args:
            query: 搜索关键词

        Returns:
            Dict: 缓存的结果，如果无效则返回None
        """
        if query in self.cache:
            result, timestamp = self.cache[query]
            # 检查是否过期
            if time.time() - timestamp < self.cache_ttl:
                return result
            else:
                # 清除过期缓存
                del self.cache[query]
        return None

    def _cache_result(self, query: str, result: Dict):
        """
        缓存搜索结果

        Args:
            query: 搜索关键词
            result: 搜索结果
        """
        self.cache[query] = (result, time.time())

        # 限制缓存大小（最多100条）
        if len(self.cache) > 100:
            # 删除最旧的缓存
            oldest_query = min(
                self.cache.keys(),
                key=lambda k: self.cache[k][1]
            )
            del self.cache[oldest_query]

    def _add_to_history(self, query: str, success: bool):
        """
        添加搜索历史

        Args:
            query: 搜索关键词
            success: 是否成功
        """
        self.search_history.append({
            'query': query,
            'timestamp': time.time(),
            'success': success
        })

        # 限制历史记录数量
        if len(self.search_history) > self.max_history:
            self.search_history.pop(0)

    def get_search_stats(self) -> Dict:
        """
        获取搜索统计信息

        Returns:
            Dict: 统计信息
        """
        total = len(self.search_history)
        if total == 0:
            return {
                'total_searches': 0,
                'success_rate': 0,
                'cache_size': len(self.cache)
            }

        success_count = sum(
            1 for h in self.search_history if h['success']
        )

        return {
            'total_searches': total,
            'successful': success_count,
            'failed': total - success_count,
            'success_rate': f"{success_count / total * 100:.1f}%",
            'cache_size': len(self.cache),
            'recent_searches': [
                h['query'] for h in self.search_history[-5:]
            ]
        }

    async def _search_ddg(
        self,
        query: str,
        max_results: int = 5,
        timelimit: str = None
    ) -> List[Dict]:
        """
        使用 DuckDuckGo 搜索（带超时控制）

        Args:
            query: 搜索关键词
            max_results: 最大结果数
            timelimit: 时间限制

        Returns:
            List[Dict]: 搜索结果列表
        """
        try:
            # 在线程池中执行同步的搜索操作，带超时控制
            loop = asyncio.get_event_loop()
            results = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    self._do_search,
                    query,
                    max_results,
                    timelimit
                ),
                timeout=self.timeout
            )
            return results
        except asyncio.TimeoutError:
            print(f"⚠️  搜索超时（{self.timeout}秒）: {query}")
            return []
        except Exception as e:
            print(f"搜索出错: {e}")
            return []

    def _do_search(
        self,
        query: str,
        max_results: int,
        timelimit: str = None
    ) -> List[Dict]:
        """
        执行实际的搜索（同步方法）

        v0.6.1: 使用新的ddgs包API,改进搜索稳定性
        v0.6.2: 添加代理支持
        v0.6.3: 添加时间限制支持

        Args:
            query: 搜索关键词
            max_results: 最大结果数
            timelimit: 时间限制 (d/w/m/y)

        Returns:
            List[Dict]: 搜索结果
        """
        import time

        # 准备代理参数（如果配置了代理）
        ddgs_kwargs = {}
        if self.proxy:
            ddgs_kwargs['proxies'] = {
                'http': self.proxy,
                'https': self.proxy
            }

        # 策略1: 直接搜索
        try:
            print(f"🔍 尝试搜索: {query} (timelimit={timelimit})")
            ddgs = DDGS(**ddgs_kwargs)
            results = list(ddgs.text(
                query,
                max_results=max_results,
                timelimit=timelimit
            ))
            if results:
                print(f"✅ 找到 {len(results)} 条结果")
                return results
            print("⚠️  策略1返回空结果")
        except Exception as e:
            print(f"⚠️  策略1失败: {str(e)[:100]}")

        # 策略2: 简化查询后重试 (不带timelimit，作为fallback)
        time.sleep(1)
        try:
            simplified_query = query.replace(
                '什么时候', '').replace('发布', ' 发布时间').strip()
            print(f"🔍 尝试简化查询: {simplified_query}")

            ddgs = DDGS(**ddgs_kwargs)
            # 简化查询时，如果之前有timelimit但失败了，这里尝试去掉timelimit或者放宽
            # 这里选择保留timelimit，如果还是失败，策略3会尝试英文
            results = list(ddgs.text(
                simplified_query,
                max_results=max_results,
                timelimit=timelimit
            ))
            if results:
                print(f"✅ 简化查询找到 {len(results)} 条结果")
                return results
            print("⚠️  策略2返回空结果")
        except Exception as e:
            print(f"⚠️  策略2失败: {str(e)[:100]}")

        # 策略3: 使用英文关键词(如果是产品查询)
        time.sleep(1)
        try:
            if 'iphone' in query.lower():
                import re
                match = re.search(r'iphone\s*\d+', query.lower())
                if match:
                    product = match.group()
                    en_query = f"{product} release date 2025"
                    print(f"🔍 尝试英文查询: {en_query}")

                    ddgs = DDGS(**ddgs_kwargs)
                    results = list(ddgs.text(
                        en_query,
                        max_results=max_results,
                        timelimit=timelimit
                    ))
                    if results:
                        print(f"✅ 英文查询找到 {len(results)} 条结果")
                        return results
                    print("⚠️  策略3返回空结果")
        except Exception as e:
            print(f"⚠️  策略3失败: {str(e)[:100]}")

        # 策略4: Bing Search (备用源)
        if self.bing_api_key:
            time.sleep(1)
            bing_results = self._search_bing(query, max_results)
            if bing_results:
                return bing_results

        print("❌ 所有搜索策略均失败")
        return []

    def _search_bing(self, query: str, max_results: int = 5) -> List[Dict]:
        """
        使用 Bing Search API 进行搜索 (备用源)

        Args:
            query: 搜索关键词
            max_results: 最大结果数

        Returns:
            List[Dict]: 搜索结果列表
        """
        if not self.bing_api_key:
            return []

        try:
            print(f"🔍 尝试 Bing Search: {query}")
            endpoint = "https://api.bing.microsoft.com/v7.0/search"
            headers = {"Ocp-Apim-Subscription-Key": self.bing_api_key}
            params = {
                "q": query,
                "count": max_results,
                "mkt": "zh-CN"
            }

            # 如果配置了代理，Bing API 请求也应该走代理吗？
            # 通常 Bing API 是 HTTPS，如果网络环境受限，可能需要代理。
            # 但如果是国内直连 Bing API 可能没问题。
            # 这里为了稳妥，如果配置了代理，尝试使用代理。
            proxies = None
            if self.proxy:
                proxies = {
                    'http': self.proxy,
                    'https': self.proxy
                }

            response = requests.get(
                endpoint,
                headers=headers,
                params=params,
                proxies=proxies,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            results = []
            if "webPages" in data and "value" in data["webPages"]:
                for item in data["webPages"]["value"]:
                    results.append({
                        "title": item.get("name"),
                        "body": item.get("snippet"),
                        "href": item.get("url")
                    })

            if results:
                print(f"✅ Bing Search 找到 {len(results)} 条结果")
                return results
            else:
                print("⚠️ Bing Search 返回空结果")
                return []

        except Exception as e:
            print(f"⚠️ Bing Search 失败: {e}")
            return []

    def _format_results(self, results: List[Dict]) -> str:
        """
        格式化搜索结果为可读文本

        Args:
            results: 搜索结果列表

        Returns:
            str: 格式化后的文本
        """
        if not results:
            return "未找到相关结果"

        formatted = f"找到 {len(results)} 条相关结果：\n\n"

        for i, result in enumerate(results, 1):
            title = result.get('title', '无标题')
            body = result.get('body', '无摘要')
            href = result.get('href', '无链接')

            formatted += f"{i}. **{title}**\n"
            formatted += f"   {body}\n"
            formatted += f"   🔗 {href}\n\n"

        return formatted.strip()


# 创建搜索工具实例
search_tool = SearchTool()
