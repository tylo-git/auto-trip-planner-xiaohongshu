from typing import Dict, Any
from src.services.mcp_client import MCPClient
from src.services.neo4j_service import Neo4jService

class SearchAgent:
    """
    Search Agent (检索智能体)
    职责：
    1. 解析用户需求（目的地、天数）
    2. 调用 MCPClient 抓取数据
    3. 调用 Neo4jService 存档
    """
    
    def __init__(self):
        self.mcp = MCPClient()
        self.neo4j = Neo4jService()
        
    def run(self, query: str) -> Dict[str, Any]:
        """
        执行检索任务
        
        Args:
            query: 用户输入 (e.g., "西安 3天")
            
        Returns:
            执行结果摘要
        """
        print(f"🤖 [SearchAgent] 收到任务: {query}")
        
        # 1. 简单解析 (后续可用 LLM)
        parts = query.split(" ")
        destination = parts[0]
        
        # 2. 检索
        print(f"🔍 [SearchAgent] 正在检索 '{destination}' 相关笔记...")
        notes = self.mcp.search_notes(destination, limit=5)
        
        if not notes:
            return {"status": "failed", "message": "未找到相关内容"}
            
        # 3. 存档 (Markdown)
        saved_files = self.mcp.save_to_markdown(notes, destination)
        print(f"💾 [SearchAgent] 已保存 {len(saved_files)} 个 Markdown 文件")
        
        # 4. 入图 (Mock 抽取)
        # 真实场景下这里会有一个 LLM 提取步骤，这里简化为直接将 Note 入库
        print(f"🕸️ [SearchAgent] 正在构建知识图谱...")
        for note in notes:
            # 基础信息入库
            self.neo4j.merge_note({
                "id": note.get("id"),
                "title": note.get("title"),
                "url": note.get("url"),
                "author": note.get("author")
            })
            
            # 假设提取到了 POI (Mock)
            # 在真实逻辑中，这里会调用 KGBuilder
            if "西安" in destination:
                self.neo4j.merge_poi("兵马俑", destination, note.get("id"))
                
        return {
            "status": "success", 
            "note_count": len(notes), 
            "files": saved_files
        }
