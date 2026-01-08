import os
import json
import time
import requests
from typing import List, Dict, Optional
from src.config import Config

class MCPClient:
    """
    小红书 MCP 客户端
    负责调用 MCP Server 获取笔记数据，或在 Mock 模式下读取本地模拟数据。
    """
    
    def __init__(self):
        self.endpoint = Config.MCP_XHS_ENDPOINT
        
    def search_notes(self, keyword: str, limit: int = 5) -> List[Dict]:
        """
        根据关键词搜索笔记
        
        Args:
            keyword: 搜索关键词
            limit: 返回数量限制
            
        Returns:
            笔记列表 (List[Dict])
        """
        return self._search_api(keyword, limit)
            
    def _search_api(self, keyword: str, limit: int) -> List[Dict]:
        """调用真实 API (如果失败则回退到 DDGS 真实搜索)"""
        try:
            print(f"Connecting to MCP Server at {self.endpoint}...")
            payload = {"keyword": keyword, "count": limit}
            # 缩短超时时间，以便快速回退
            response = requests.post(f"{self.endpoint}/search", json=payload, timeout=2)
            response.raise_for_status()
            data = response.json().get("data", [])
            if data:
                return data
        except Exception as e:
            print(f"⚠️ MCP API Call Failed ({e}). Falling back to DDGS.")
            
        return self._generate_fallback_notes(keyword, limit)

    def _generate_fallback_notes(self, keyword: str, limit: int) -> List[Dict]:
        """生成笔记数据 (Fallback: DDGS 真实搜索)"""
        results = []
        
        # 1. 尝试使用 DuckDuckGo 搜索小红书
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                # 搜索 site:xiaohongshu.com
                ddgs_gen = ddgs.text(f"site:xiaohongshu.com {keyword}", max_results=limit)
                for r in ddgs_gen:
                    results.append({
                        "id": f"ddg_{hash(r['href'])}",
                        "title": r.get("title"),
                        "content": r.get("body"),
                        "author": "XHS_User",
                        "url": r.get("href"),
                        "tags": [keyword, "DDGS"]
                    })
        except Exception as e:
            print(f"XHS-DDGS Fallback Error: {e}")

        return results[:limit]

    def save_to_markdown(self, notes: List[Dict], query: str) -> List[str]:
        """
        将笔记保存为 Markdown 文件
        
        Returns:
            保存的文件路径列表
        """
        saved_paths = []
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        date_dir = time.strftime("%Y%m%d")
        save_dir = os.path.join(Config.XHS_MD_DIR, date_dir)
        os.makedirs(save_dir, exist_ok=True)
        
        for i, note in enumerate(notes):
            note_id = note.get("id", f"unknown_{i}")
            filename = f"{query}_{timestamp}_{note_id}.md"
            filepath = os.path.join(save_dir, filename)
            
            content = f"""---
source_id: "{note_id}"
source_url: "{note.get('url', '')}"
author: "{note.get('author', 'unknown')}"
publish_date: "{note.get('time', '')}"
tags: {json.dumps(note.get('tags', []))}
crawled_at: "{timestamp}"
---

# {note.get('title', 'No Title')}

{note.get('content', '')}
"""
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            saved_paths.append(filepath)
            
        return saved_paths
