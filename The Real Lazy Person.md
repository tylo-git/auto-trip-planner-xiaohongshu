# The Real Lazy Person (TRLP) - 技术架构白皮书

> **Project Mission**: "Input Once, Plan Everything."  
> 打造基于 Multi-Agent 与知识图谱的下一代智能旅行规划系统。

---

## 1. 技术栈概览 (Tech Stack)

本项目采用 **Python 全栈** 开发，融合了当下最前沿的 LLM 应用框架与数据处理技术。

| 领域 | 核心技术/库 | 用途 |
| :--- | :--- | :--- |
| **Agent Framework** | **Microsoft AutoGen** | 多智能体编排、角色扮演、任务分发 |
| **Frontend** | **Streamlit** | 极速构建交互式 Web UI |
| **LLM** | **OpenAI GPT-4o / Gemini-2.0-Flash** | 核心推理引擎、代码生成、创意写作 |
| **Knowledge Graph** | **Neo4j** + Cypher | 结构化存储地点、价格、关系，支持多跳推理 |
| **Search Engine** | **DuckDuckGo (DDGS)** / Tavily | 实时联网检索，获取最新旅行资讯 |
| **Data Protocol** | **MCP (Model Context Protocol)** | 标准化数据接口（模拟小红书 API） |
| **Visualization** | **Graphviz** (DOT) | 动态生成行程拓扑图 |
| **Data Science** | **Pandas** | 预算清洗、聚合计算 |

---

## 2. 系统架构图 (System Architecture)

```mermaid
graph TD
    User[用户 (Streamlit UI)] -->|1. 输入需求| Manager[Manager Agent (编排器)]
    
    subgraph "Data Acquisition Layer (数据层)"
        Manager -->|2. 检索| SearchClient
        SearchClient -->|API| XHS[小红书 (MCP/Mock)]
        SearchClient -->|Search| Web[DeepSearch (DuckDuckGo)]
    end
    
    subgraph "Knowledge Layer (知识层)"
        Manager -->|3. 提取| KGBuilder[KG Extraction (LLM)]
        KGBuilder -->|Write| Neo4j[(Neo4j 知识图谱)]
        Neo4j -->|Query| Planner
    end
    
    subgraph "Reasoning Layer (推理层)"
        Manager -->|4. 规划| Planner[Planner Agent]
        Planner -->|Generate| PlanJSON[结构化计划 JSON]
        
        Manager -->|5. 写作| Writer[Writer Agent]
        Writer -->|Read| PlanJSON
        Writer -->|Output| GuideMD[深度指南 Markdown]
    end
    
    subgraph "Presentation Layer (展示层)"
        PlanJSON -->|Compute| Budget[Budget Agent (Python)]
        PlanJSON -->|Visualize| Figure[Figure Agent (Gemini)]
        
        Budget -->|CSV| User
        Figure -->|Graphviz| User
        GuideMD -->|Download| User
    end
```

---

## 3. 核心技术路线详解

### 3.1 多智能体协同 (Multi-Agent Orchestration)
我们摒弃了单一 Prompt 的脆弱模式，采用 **AutoGen** 构建了一个包含多个专家的“虚拟团队”：
*   **Manager**: 也就是项目经理，负责整个 Pipeline 的调度（检索 -> 建图 -> 规划 -> 写作）。
*   **Planner**: 专注于逻辑严密的行程安排（JSON 格式），受 `PROMPT_SPECIAL_FORCES` 等严格指令约束。
*   **Writer**: 专注于感性、深度的长文写作（Markdown 格式），模拟《Condé Nast Traveler》风格。
*   **FigureAgent**: 专注于可视化，将 JSON 转化为 Graphviz 代码。

### 3.2 动态知识图谱 (RAG + KG)
为了解决 LLM 的幻觉问题，我们引入了 **GraphRAG** 的思想：
1.  **动态提取**: 每次检索到非结构化文本（笔记/网页）后，利用 LLM 实时提取实体（Place, Food, Price）和关系（LOCATED_IN, HAS_COST）。
2.  **图谱存储**: 将提取的知识存入 **Neo4j**。
3.  **优势**: 相比纯 Vector RAG，知识图谱能更好地处理“多跳查询”（如：找一家在夜市旁边且人均低于50元的店）。

### 3.3 混合检索增强 (Hybrid Search)
*   **MCP Client**: 模拟了 Model Context Protocol 协议，标准化了“小红书”数据的获取方式。支持 Fallback 机制，当 API 不可用时自动切换到 DuckDuckGo 或 Mock 数据。
*   **DeepSearch**: 利用 `duckduckgo-search` 获取全网实时信息（如门票价格、开放时间），弥补社交媒体数据的片面性。

### 3.4 结构化输出与可视化
*   **JSON Schema Enforcement**: 通过 Prompt 强约束，确保 Planner 输出严格符合 JSON Schema，使得下游的预算计算和绘图成为可能。
*   **Code-based Visualization**: 不依赖不稳定的 AI 画图，而是让 LLM 生成 **Graphviz DOT 代码**。这种“代码即图表”的方式保证了逻辑图的绝对准确和清晰。

---

## 4. 关键流程 (Workflow)

1.  **Initialization**: 用户输入目的地，系统自动清空 Neo4j 数据库，准备全新的上下文。
2.  **Data Mining**: 并行抓取 30+ 条相关笔记与网页。
3.  **Knowledge Extraction**: LLM 分批阅读文档，构建“地点-价格-活动”图谱。
4.  **Planning**: Planner Agent 基于图谱和约束（特种兵/吃货）生成详细的时间表。
5.  **Refinement**: 
    *   **Budget Agent** 用 Python 计算每一笔开销。
    *   **Writer Agent** 撰写 2000 字深度指南。
    *   **Figure Agent** 绘制行程拓扑图。
6.  **Delivery**: Streamlit 渲染所有产物，提供文件下载。

---

> **Summary**: TRLP 不仅仅是一个简单的包装器，它展示了如何通过 **Agentic Workflow** 将非结构化数据转化为高价值的、可执行的结构化知识。
