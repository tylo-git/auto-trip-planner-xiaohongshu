import os
from dotenv import load_dotenv

# 强制加载 .env (使用绝对路径)
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(env_path, override=True)

class Config:
    # API Keys
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    DEEPSEARCH_API_KEY = os.getenv("DEEPSEARCH_API_KEY")
    
    # Neo4j
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
    
    # MCP
    MCP_XHS_ENDPOINT = os.getenv("MCP_XHS_ENDPOINT", "http://localhost:8000")
    
    # System
    MOCK_MODE = False
    
    print(f"--- CONFIG DEBUG ---")
    print(f"Env Path: {env_path}")
    print(f"MOCK_MODE FORCED: {MOCK_MODE}")
    print(f"--------------------")
    
    # Paths
    DATA_DIR = os.path.join(os.getcwd(), "data")
    MOCK_DIR = os.path.join(DATA_DIR, "mock")
    XHS_MD_DIR = os.path.join(DATA_DIR, "xhs_md")
    EXPORTS_DIR = os.path.join(DATA_DIR, "exports")
    
    @classmethod
    def validate(cls):
        """检查必要的配置是否存在"""
        if not cls.MOCK_MODE:
            if not cls.OPENAI_API_KEY:
                print("Warning: OPENAI_API_KEY not found. LLM features may fail.")
