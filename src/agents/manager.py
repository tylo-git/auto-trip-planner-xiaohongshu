import os
import json
from src.config import Config
from src.utils.prompts import PROMPT_SPECIAL_FORCES, PROMPT_FOODIE, PLAN_OUTPUT_SCHEMA, PROMPT_WRITER
import requests
import re

class AgentManager:
    """
    智能体编排管理器
    """
    
    def __init__(self):
        self.model = "gpt-5.2-chat-latest"
        self.temperature = 0.7

    def _call_chat_completions(self, system_message: str, user_message: str, temperature: float = None) -> str:
        if not Config.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY not found in environment.")

        base_url = (Config.OPENAI_BASE_URL or "https://api.openai.com/v1").rstrip("/")
        url = f"{base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_message or ""},
                {"role": "user", "content": user_message or ""},
            ],
            "temperature": self.temperature if temperature is None else temperature,
        }
        headers = {
            "Authorization": f"Bearer {Config.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }

        resp = requests.post(url, json=payload, headers=headers, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        return (data.get("choices") or [{}])[0].get("message", {}).get("content", "") or ""

    def _extract_first_json_object(self, text: str) -> dict:
        if not text:
            return {}
        match = re.search(r"(\{.*\})", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                return {}
        try:
            return json.loads(text)
        except Exception:
            return {}

    def run_flow(self, user_input: str, mode: str):
        """
        运行多智能体流程 (Pipeline 模式：检索 -> 注入 -> 规划)
        """
        try:
            print(f"[Manager] Starting Pipeline Flow for: {user_input}")
            
            # --- Step 1: 主动数据检索 ---
            print("[Manager] Step 1: Collecting Data...")
            
            # 1.1 小红书检索
            from src.services.mcp_client import MCPClient
            xhs_client = MCPClient()
            # 提取目的地作为关键词
            destination = user_input.split(" ")[0]
            notes = xhs_client.search_notes(destination, limit=30)
            
            # 存档 Markdown
            saved_md_files = xhs_client.save_to_markdown(notes, destination)
            print(f"[Manager] Saved {len(saved_md_files)} XHS notes to markdown.")
            
            xhs_context = "\n".join([f"- [小红书] {n.get('title')}: {n.get('content')[:100]}... (Source: {n.get('url')})" for n in notes])
            
            # 1.2 DeepSearch 检索
            from src.services.deepsearch_client import DeepSearchClient
            ds_client = DeepSearchClient()
            ds_context, ds_results = ds_client.search(f"{user_input} 旅游攻略 {mode}", max_results=5)
            
            # --- Step 1.5: 知识图谱构建 (Enhanced & Batch Processing) ---
            try:
                from src.services.neo4j_service import Neo4jService
                neo4j = Neo4jService()
                
                # 1. 清空旧数据
                neo4j.clear_database()
                
                # 2. 准备所有待处理文档
                all_docs = []
                for n in notes:
                    all_docs.append({"text": f"Title: {n.get('title')}\nContent: {n.get('content')}", "source": "XHS"})
                for r in ds_results:
                    all_docs.append({"text": f"Title: {r.get('title')}\nContent: {r.get('content')}", "source": "Web"})
                
                print(f"[Manager] Extracting KG from {len(all_docs)} documents...")
                
                # 3. 分批提取 (防止 Context Overflow)
                batch_size = 5
                total_nodes = 0
                
                for i in range(0, len(all_docs), batch_size):
                    batch = all_docs[i:i+batch_size]
                    batch_text = "\n---\n".join([d["text"] for d in batch])
                    
                    extraction_prompt = f"""
                    You are an expert Knowledge Graph Builder. Your task is to extract structured knowledge from the provided travel notes.
                    
                    ### Ontology Schema
                    - **Nodes**:
                        - `Place` (name, type=spot/restaurant/hotel/transport)
                        - `Food` (name, cuisine_type)
                        - `Activity` (name, duration)
                        - `Price` (value, currency)
                        - `Tag` (name)
                    - **Relationships**:
                        - `(:Place)-[:LOCATED_IN]->(:Place)` (e.g., Spot in City)
                        - `(:Place)-[:HAS_COST]->(:Price)`
                        - `(:Place)-[:OFFERS]->(:Food)`
                        - `(:Place)-[:SUITABLE_FOR]->(:Activity)`
                        - `(:Place)-[:HAS_TAG]->(:Tag)`
                        - `(:Place)-[:NEARBY]->(:Place)` (Implicit distance)
                    
                    ### Input Text
                    {batch_text[:3000]} 
                    
                    ### Output Format
                    Return a SINGLE JSON object with "nodes" and "relationships".
                    {{
                      "nodes": [{{"id": "...", "type": "...", "properties": {{"name": "...", ...}}}}],
                      "relationships": [{{"source": "...", "source_type": "...", "target": "...", "target_type": "...", "type": "..."}}]
                    }}
                    """
                    kg_response = self._call_chat_completions(
                        system_message="You are an expert Knowledge Graph Builder.",
                        user_message=extraction_prompt,
                        temperature=0.2
                    )
                    
                    # 解析并写入
                    import re
                    kg_match = re.search(r"(\{.*\})", kg_response, re.DOTALL)
                    if kg_match:
                        try:
                            kg_data = json.loads(kg_match.group(1))
                            nodes_list = kg_data.get("nodes", [])
                            rels_list = kg_data.get("relationships", [])
                            if nodes_list:
                                neo4j.create_graph_data(nodes_list, rels_list)
                                total_nodes += len(nodes_list)
                                print(f"[Manager] Batch {i//batch_size + 1}: Added {len(nodes_list)} nodes.")
                        except json.JSONDecodeError:
                            print(f"[Warning] Batch {i//batch_size + 1} JSON decode failed.")
                            
                print(f"[Manager] Knowledge Graph built with {total_nodes} nodes total.")
                
            except Exception as e:
                print(f"[Warning] KG Update failed: {e}")
                import traceback
                traceback.print_exc()
            
            full_context = f"【小红书热点 (10篇)】\n{xhs_context}\n\n【全网搜索 (5篇)】\n{ds_context}"
            print(f"[Manager] Data Collected:\n{full_context[:200]}...")
            
            # --- Step 2: 构造 Prompt 并规划 ---
            print("[Manager] Step 2: Planning with LLM...")
            
            mode_prompt = PROMPT_SPECIAL_FORCES if "特种兵" in mode else PROMPT_FOODIE
            
            # 动态注入 Schema
            schema_str = json.dumps(PLAN_OUTPUT_SCHEMA, indent=2, ensure_ascii=False)
            
            prompt = f"""
            你是一个专业的旅行规划师。请根据以下检索到的实时信息，为用户生成一份详细的旅行计划。
            
            用户需求: {user_input}
            旅行模式: {mode}
            
            参考信息:
            {full_context}
            
            模式要求:
            {mode_prompt}
            
            输出格式:
            请直接输出一个合法的 JSON 对象，不要包含 Markdown 代码块标记（如 ```json），也不要包含其他废话。
            JSON 结构必须严格符合以下 Schema：
            {schema_str}
            """
            
            # 直接调用 user_proxy (它实际上是一个 wrapper，我们可以借用它的 client 或者直接用 openai)
            # 为了保持 AutoGen 风格，我们还是用 initiate_chat，但只跟 Planner 聊一轮
            content = self._call_chat_completions(
                system_message="你是一个专业的旅行规划师。",
                user_message=prompt,
                temperature=0.7
            )
            
            print(f"[Manager] Planner Output: {content[:100]}...")
            
            # --- Step 3: 解析结果 ---
            plan_data = self._extract_first_json_object(content)
            
            # --- Step 4: 预算计算 (Post-Processing) ---
            from src.agents.budget_agent import BudgetAgent
            budget_agent = BudgetAgent()
            budget_res = budget_agent.calculate(plan_data)
            
            # 更新 Plan JSON 中的总价，并附带 CSV 路径
            plan_data["total_budget_estimate"] = budget_res["total"]
            plan_data["budget_csv"] = budget_res["csv_path"]
            
            # 附加原始检索数据供前端展示
            plan_data["_raw_notes"] = notes 
            
            # --- Step 5: 深度指南写作 (Writer Agent) ---
            print("[Manager] Step 5: Writing Guide...")
            writer_msg = f"""
            {PROMPT_WRITER}
            
            以下是已经生成的【旅行计划 JSON】和【原始检索数据】，请基于此写作：
            
            【旅行计划】:
            {json.dumps(plan_data, ensure_ascii=False, indent=2)}
            
            【原始数据】:
            {full_context}
            
            请直接输出 Markdown 内容，不要包含 JSON 代码块。
            """
            guide_content = self._call_chat_completions(
                system_message="你是旅行专栏作家。负责撰写深度游玩指南。",
                user_message=writer_msg,
                temperature=0.7
            )
            
            # 保存为文件
            guide_filename = f"guide_{destination}_{mode[:2]}.md"
            guide_path = os.path.join(Config.EXPORTS_DIR, guide_filename)
            with open(guide_path, "w", encoding="utf-8") as f:
                f.write(guide_content)
                
            plan_data["detailed_guide"] = guide_content
            plan_data["guide_file"] = guide_path
            
            return plan_data

        except Exception as e:
            print(f"[Error] Pipeline flow failed: {e}")
            import traceback
            traceback.print_exc()
            return {}


# 单例
manager = AgentManager()
