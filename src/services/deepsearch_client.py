import requests
from src.config import Config

class DeepSearchClient:
    """
    DeepSearch 搜索服务 (模拟或真实)
    """
    
    def __init__(self):
        self.api_key = Config.DEEPSEARCH_API_KEY
        # 假设使用 Tavily 或类似服务作为 DeepSearch
        self.endpoint = "https://api.tavily.com/search" 
        
    def search(self, query: str, max_results: int = 5):
        """
        执行搜索并返回 (摘要文本, 原始结果列表)
        """
        print(f"🔍 [DeepSearch] Searching for: {query} (Limit: {max_results})")
        
        results = []
        
        # 1. 优先尝试真实 Key (Tavily/DeepSearch)
        if self.api_key and "sk-" not in self.api_key:
             try:
                payload = {"query": query, "api_key": self.api_key, "search_depth": "basic", "max_results": max_results}
                response = requests.post(self.endpoint, json=payload, timeout=5)
                if response.status_code == 200:
                    data = response.json().get("results", [])
                    for r in data:
                        results.append({
                            "title": r.get("title"),
                            "content": r.get("content"),
                            "url": r.get("url")
                        })
             except Exception as e:
                 print(f"DeepSearch API Error: {e}")
        
        # 2. Fallback: 使用 DuckDuckGo (真实网络搜索)
        if not results:
            try:
                from duckduckgo_search import DDGS
                with DDGS() as ddgs:
                    # DDGS 返回 generator
                    ddgs_gen = ddgs.text(query, max_results=max_results)
                    for r in ddgs_gen:
                        results.append({
                            "title": r.get("title"),
                            "content": r.get("body"),
                            "url": r.get("href")
                        })
            except Exception as e:
                print(f"DDGS Error: {e}")

        # 3. 如果还是没有，使用 Mock
        if not results:
            print("DeepSearch Error: No results returned from API/DDGS.")
            return "", []
             
        # 格式化输出
        formatted = "\n".join([f"- [{r['title']}]({r['url']}): {r['content']}" for r in results])
        return formatted, results

    def _fallback_search(self, query):
        return f"""
        [DeepSearch 模拟结果] 关于 {query} 的网络搜索：
        1. 携程攻略: {query} 建议游玩时间为3-4天，必去景点包括...
        2. 马蜂窝: {query} 当地特色美食推荐...
        3. 维基百科: {query} 的历史文化背景...
        """
