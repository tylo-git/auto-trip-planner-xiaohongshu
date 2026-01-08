import pandas as pd
import os
from src.config import Config

class BudgetAgent:
    """
    Budget Agent (预算智能体)
    职责：接收 Plan JSON，计算总成本，生成 CSV 报表。
    """
    
    def calculate(self, plan_json: dict) -> dict:
        """
        计算预算
        
        Returns:
            {
                "total": float,
                "csv_path": str,
                "breakdown": dict
            }
        """
        print("💰 [BudgetAgent] 开始计算预算...")
        
        items = []
        total_cost = 0.0
        breakdown = {"spot": 0, "food": 0, "transport": 0, "hotel": 0, "other": 0}
        
        # 遍历行程
        for day in plan_json.get("itinerary", []):
            date = day.get("date", f"Day {day.get('day')}")
            for act in day.get("activities", []):
                cost = float(act.get("cost", 0))
                category = act.get("type", "other")
                
                # 累加
                total_cost += cost
                breakdown[category] = breakdown.get(category, 0) + cost
                
                # 记录明细
                items.append({
                    "Date": date,
                    "Category": category,
                    "Item": act.get("name"),
                    "Cost": cost,
                    "Note": act.get("description", "")
                })
                
        # 加上预估的机酒（如果 JSON 里没包含）
        # 这里为了演示，我们假设 JSON 里只有活动费用，额外加一点 buffer
        buffer_cost = total_cost * 0.1
        total_cost += buffer_cost
        items.append({
            "Date": "N/A",
            "Category": "buffer",
            "Item": "不可预见费用 (10%)",
            "Cost": buffer_cost,
            "Note": "Buffer"
        })
        
        # 生成 CSV
        df = pd.DataFrame(items)
        filename = f"budget_{plan_json.get('destination', 'trip')}.csv"
        csv_path = os.path.join(Config.EXPORTS_DIR, filename)
        os.makedirs(Config.EXPORTS_DIR, exist_ok=True)
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        
        print(f"💰 [BudgetAgent] 计算完成，总额: {total_cost}，已保存至 {csv_path}")
        
        return {
            "total": round(total_cost, 2),
            "csv_path": csv_path,
            "breakdown": breakdown,
            "dataframe": df # 方便 Streamlit 直接渲染
        }
