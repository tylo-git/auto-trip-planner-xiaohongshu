import os
import shutil
from src.config import Config
from src.utils.prompts import PROMPT_FIGURE_GEN

class FigureAgent:
    """
    Figure Agent (绘图智能体)
    职责：根据 Plan 生成 Prompt，调用 Gemini 绘图（或返回 Mock 图片）。
    """
    
    def generate_map(self, plan_json: dict) -> str:
        """
        生成旅行地图
        
        Returns:
            image_path (str)
        """
        dest = plan_json.get("destination", "trip")
        print(f"🎨 [FigureAgent] 正在为 {dest} 绘制地图...")
        
        # 1. 构造 Prompt
        prompt = self._construct_prompt(plan_json)
        print(f"🎨 [FigureAgent] Prompt: {prompt[:50]}...")
        
        # 2. 调用 API (或 Mock)
        return self._call_gemini(prompt, dest)
            
    def _construct_prompt(self, plan_json):
        # 提取地标
        landmarks = []
        for day in plan_json.get("itinerary", []):
            for act in day.get("activities", []):
                if act.get("type") == "spot":
                    landmarks.append(act.get("name"))
        
        return PROMPT_FIGURE_GEN.format(
            destination=plan_json.get("destination"),
            key_landmarks_list=", ".join(landmarks[:5]),
            start_point=landmarks[0] if landmarks else "Start",
            end_point=landmarks[-1] if landmarks else "End",
            mode_atmosphere="Energetic" if "special" in plan_json.get("mode", "") else "Relaxing"
        )

    def _call_gemini(self, prompt, dest):
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=Config.GEMINI_API_KEY)
            # 切换回文本生成模型来生成 Graphviz 代码
            model = genai.GenerativeModel('gemini-2.0-flash-exp') 
            
            # 尝试调用文生图能力
            # 切换为 Graphviz DOT 语言，因为 Streamlit 原生支持 st.graphviz_chart
            graphviz_prompt = f"""
            Create a simple Graphviz DOT code (digraph) to visualize the plan structure.
            
            Requirements:
            1.  **Structure**: Use `subgraph cluster_dayX` to group activities by day.
            2.  **Nodes**: Only include activity names (no descriptions).
            3.  **Edges**: Connect activities sequentially within each day.
            4.  **Style**: Minimalist. Use `rankdir=TB`.
            5.  **Output**: Return ONLY the raw DOT code.
            """
            
            response = model.generate_content(graphviz_prompt)
            return response.text
        except Exception as e:
            print(f"Gemini API Error: {e}")
            return None
