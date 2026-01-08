import os
try:
    from neo4j import GraphDatabase
except ImportError:
    GraphDatabase = None
from src.config import Config

class Neo4jService:
    """
    Neo4j 图谱服务
    负责管理数据库连接、执行 Cypher 查询与写入。
    """
    
    def __init__(self):
        self.uri = Config.NEO4J_URI
        self.user = Config.NEO4J_USER
        self.password = Config.NEO4J_PASSWORD
        self.driver = None
        
        self._connect()
            
    def _connect(self):
        if GraphDatabase is None:
            print("Warning: neo4j package not found. Neo4j features disabled.")
            self.driver = None
            return
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            self.driver.verify_connectivity()
        except Exception as e:
            print(f"Neo4j Connection Failed: {e}")
            self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()
            
    def execute_query(self, query: str, parameters: dict = None):
        """执行 Cypher 查询"""
        if not self.driver:
            print(f"⚠️ [Neo4j-Disconnected] Cannot execute: {query[:50]}...")
            return []
            
        with self.driver.session() as session:
            result = session.run(query, parameters)
            return [record.data() for record in result]

    def clear_database(self):
        """清空数据库"""
        if not self.driver: return
        print("🧹 [Neo4j] Clearing database...")
        self.execute_query("MATCH (n) DETACH DELETE n")

    def create_graph_data(self, nodes: list, relationships: list):
        """
        基于简单的 Ontology Schema 写入数据
        Nodes: [{id, type, properties}]
        Relationships: [{source, target, type, properties}]
        """
        if not self.driver: return
        
        # 1. Create Nodes
        for node in nodes:
            props = node.get("properties", {})
            # 简单处理：只支持 name 属性，其他忽略或作为额外属性
            # 实际生产中应动态构建 SET 子句
            cypher = f"MERGE (n:{node['type']} {{name: $name}})"
            self.execute_query(cypher, {"name": props.get("name", "Unknown")})
            
        # 2. Create Relationships
        for rel in relationships:
            # 使用 MERGE 确保节点存在，防止因名称不匹配导致关系丢失
            cypher = f"""
            MERGE (a:{rel['source_type']} {{name: $source_name}})
            MERGE (b:{rel['target_type']} {{name: $target_name}})
            MERGE (a)-[:{rel['type']}]->(b)
            """
            self.execute_query(cypher, {
                "source_name": rel["source"],
                "target_name": rel["target"]
            })
            
    def merge_note(self, note_data: dict):
        """
        将笔记数据 Merge 到图谱中
        """
        cypher = """
        MERGE (n:Note {id: $id})
        SET n.title = $title,
            n.url = $url,
            n.author = $author,
            n.timestamp = timestamp()
        """
        # 确保传入的 dict 包含所有必要的 key
        params = {
            "id": note_data.get("id", "unknown"),
            "title": note_data.get("title", "No Title"),
            "url": note_data.get("url", ""),
            "author": note_data.get("author", "unknown")
        }
        self.execute_query(cypher, params)
        
    def merge_poi(self, poi_name: str, city: str, note_id: str):
        """
        建立 POI 与 Note 的关联
        
        Schema:
        (:POI {name}) -[:LOCATED_IN]-> (:Destination {name})
        (:Note) -[:MENTIONS]-> (:POI)
        """
        cypher = """
        MERGE (d:Destination {name: $city})
        MERGE (p:POI {name: $poi_name})
        MERGE (p)-[:LOCATED_IN]->(d)
        
        WITH p
        MATCH (n:Note {id: $note_id})
        MERGE (n)-[:MENTIONS]->(p)
        """
        self.execute_query(cypher, {"city": city, "poi_name": poi_name, "note_id": note_id})
