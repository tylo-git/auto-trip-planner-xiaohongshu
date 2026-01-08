import streamlit as st
import time
import json
import os
import sys

# 添加 src 目录到路径，以便导入模块
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config import Config
from src.utils.prompts import PROMPT_SPECIAL_FORCES, PROMPT_FOODIE
from src.agents.manager import manager  # 引入 AgentManager

# 设置页面配置
st.set_page_config(
    page_title="TRLP - 懒人旅行规划师",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 初始化 Session State
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "我是 TRLP，您的懒人旅行规划师。请输入目的地（如：'西安 3天'）开始规划。"}
    ]
if "plan_generated" not in st.session_state:
    st.session_state.plan_generated = False

# 侧边栏
with st.sidebar:
    st.title("🛠️ 设置 & 历史")
    
    st.markdown("### 模式选择")
    mode = st.radio(
        "选择您的旅行风格:",
        ("特种兵模式 (高强度)", "吃货模式 (美食优先)"),
        index=0
    )
    
    st.markdown("### 系统状态")
    st.success("✅ 实时模式 (API 已连接)")
        
    st.divider()
    
    if st.button("🗑️ 清空对话"):
        st.session_state.messages = [
            {"role": "assistant", "content": "我是 TRLP，您的懒人旅行规划师。请输入目的地（如：'西安 3天'）开始规划。"}
        ]
        st.session_state.plan_generated = False
        st.rerun()

    st.markdown("---")
    st.caption(f"v1.0.0 | Env: {os.getenv('CONDA_DEFAULT_ENV', 'unknown')}")

# 主聊天区
st.title("✈️ The Real Lazy Person")
st.caption("基于 AutoGen + 小红书 MCP + Neo4j 的智能旅行规划系统")

# 渲染历史消息
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 处理用户输入
if prompt := st.chat_input("输入目的地和天数..."):
    # 1. 添加用户消息
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. 系统响应 (模拟 Agent 思考过程)
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        # 模拟中间状态
        with st.status("正在召唤智能体集群 (Real Flow)...", expanded=True) as status:
            import io
            from contextlib import redirect_stdout
            
            # 捕获 AutoGen 的控制台输出
            f = io.StringIO()
            with redirect_stdout(f):
                try:
                    # 调用 Agent Manager
                    st.write("🚀 初始化 Agent Manager...")
                    plan_json = manager.run_flow(prompt, mode)
                except Exception as e:
                    st.error(f"Execution Error: {e}")
                    plan_json = {}
            
            # 显示捕获的日志
            logs = f.getvalue()
            st.code(logs, language="text")
            
            if not plan_json:
                st.error("生成失败，请检查上方日志。")
                st.stop()
                
            st.write("✅ 规划完成!")
            status.update(label="✅ 规划完成!", state="complete", expanded=False)
        
        # 解析 JSON 并生成 Markdown 回复
        dest = plan_json.get("destination", "未知")
        
        # --- 新增: 展示原始检索数据 ---
        if "_raw_notes" in plan_json:
            with st.expander("📚 查看原始检索数据 (小红书/DeepSearch)", expanded=False):
                for note in plan_json["_raw_notes"]:
                    st.markdown(f"**[{note.get('author', 'Unknown')}]** {note.get('title')}")
                    st.caption(note.get('content')[:100] + "...")
                    st.markdown("---")
        
        # 动态生成回复
        itinerary_md = ""
        total_cost = plan_json.get("total_budget_estimate", 0)
        detailed_guide = plan_json.get("detailed_guide", "")
        
        for day in plan_json.get("itinerary", []):
            itinerary_md += f"#### 📅 第{day.get('day')}天：{day.get('date', '')}\n"
            
            # 显示住宿
            acc = day.get("accommodation", {})
            if acc:
                itinerary_md += f"> 🏨 **住宿**: {acc.get('name')} (💰{acc.get('cost', 0)}) - _{acc.get('reason')}_\n\n"
                
            for act in day.get("activities", []):
                cost = act.get("cost", 0)
                itinerary_md += f"*   **{act.get('time')}** {act.get('name')} ({act.get('type')}) - 💰{cost}\n    *   _{act.get('description')}_\n"
            itinerary_md += "\n"

        response_content = f"""
### 🗺️ {dest} 旅行计划 ({mode.split(' ')[0]})

{itinerary_md}

---
**💰 预估总预算**: {total_cost} 元
"""
        message_placeholder.markdown(response_content)
        
        # 添加到历史
        st.session_state.messages.append({"role": "assistant", "content": response_content})
        st.session_state.plan_generated = True
        st.session_state.current_plan = plan_json # 保存到 Session 以便绘图使用

# 额外展示区 (图表/图片)
if st.session_state.plan_generated and "current_plan" in st.session_state:
    plan = st.session_state.current_plan
    st.divider()
    
    st.divider()
    st.subheader("📖 深度游玩指南")
    
    guide_content = plan.get("detailed_guide", "")
    guide_file = plan.get("guide_file")
    
    if guide_file and os.path.exists(guide_file):
        # 读取文件内容到内存，避免 rerun 时文件句柄问题
        with open(guide_file, "r", encoding="utf-8") as f:
            file_content = f.read()
            
        st.download_button(
            label="📥 下载完整指南 (Markdown)",
            data=file_content,
            file_name=os.path.basename(guide_file),
            mime="text/markdown"
        )
            
    with st.expander("预览指南内容", expanded=True):
        st.markdown(guide_content)

    # --- Section 1: 预算分析 (全宽) ---
    st.subheader("📊 预算构成 (AI + Python)")
    
    # 动态计算预算 (用于绘图)
    categories = {"spot": 0, "food": 0, "hotel": 0, "transport": 0, "other": 0}
    for day in plan.get("itinerary", []):
        for act in day.get("activities", []):
            ctype = act.get("type", "other")
            cost = act.get("cost", 0)
            if "spot" in ctype: categories["spot"] += cost
            elif "food" in ctype: categories["food"] += cost
            elif "hotel" in ctype: categories["hotel"] += cost
            elif "trans" in ctype: categories["transport"] += cost
            else: categories["other"] += cost
            
    # 如果有 accommodation 字段 (新 Schema)
    for day in plan.get("itinerary", []):
        acc = day.get("accommodation", {})
        if acc:
            categories["hotel"] += acc.get("cost", 0)

    # 左右布局：左边是表格，右边是图表
    b_col1, b_col2 = st.columns([1, 1])
    
    with b_col1:
        st.caption("预算明细表")
        csv_path = plan.get("budget_csv")
        if csv_path and os.path.exists(csv_path):
            import pandas as pd
            df = pd.read_csv(csv_path)
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("预算表生成失败")

    with b_col2:
        st.caption("费用分布图")
        budget_data = {"类别": list(categories.keys()), "金额": list(categories.values())}
        st.bar_chart(budget_data, x="类别", y="金额")

    # --- Section 2: 路线导览 (全宽) ---
    st.divider()
    st.subheader("🗺️ 路线导览 (Graphviz)")
    
    # 调用 Figure Agent
    if "map_code" not in st.session_state:
        from src.agents.figure_agent import FigureAgent
        fig_agent = FigureAgent()
        with st.spinner("正在绘制路线图..."):
            map_res = fig_agent.generate_map(plan)
            st.session_state.map_code = map_res
        
    if st.session_state.map_code:
         # 清理 markdown 标记
         code = st.session_state.map_code.replace("```graphviz", "").replace("```dot", "").replace("```", "").strip()
         try:
             st.graphviz_chart(code)
         except Exception as e:
             st.error(f"渲染失败: {e}")
             with st.expander("查看原始 DOT 代码"):
                 st.code(code)
    else:
         st.info("地图生成中或失败...")
