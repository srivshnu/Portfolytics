import json
import os
from google import genai
from config import settings

PROMPTS_FILE = os.path.join(os.path.dirname(__file__), "prompts.json")
try:
    with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
        SYSTEM_PROMPTS = json.load(f)
except Exception:
    SYSTEM_PROMPTS = {}

async def analyze_asset(asset_data: dict) -> str:
    if not settings.GEMINI_API_KEY:
        return "AI analysis unavailable. Set GEMINI_API_KEY in your .env file."
    
    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        
        name = asset_data.get("name", "Unknown Asset")
        asset_type = asset_data.get("asset_type", "asset")
        current_price = asset_data.get("current_price", 0)
        previous_price = asset_data.get("previous_price", 0)
        change_pct = asset_data.get("change_pct", 0.0)
        is_alert = asset_data.get("is_alert", False)
        
        if is_alert:
            prompt_config = SYSTEM_PROMPTS.get("disaster_alert_prompt", {})
            prompt = f"SYSTEM INSTRUCTIONS:\n{json.dumps(prompt_config, indent=2)}\n\nUSER REQUEST: URGENT: {name} has dropped {change_pct}% today. Explain the global or local events causing this drop. Assess if this is a hype bubble bursting. Suggest safer alternatives in a similar price bracket. Keep the investor calm but be honest."
        else:
            prompt_config = SYSTEM_PROMPTS.get("daily_update_prompt", {})
            prompt = f"SYSTEM INSTRUCTIONS:\n{json.dumps(prompt_config, indent=2)}\n\nUSER REQUEST: Analyze the performance of {name} ({asset_type}). Current: {current_price}, Previous: {previous_price}, Change: {change_pct}%. Connect this performance to specific global/local events. Warn if the stock is hype-driven, and suggest alternative solid investments in a similar price range."
            
        response = await client.aio.models.generate_content(model='gemini-3.5-flash', contents=prompt)
        return response.text
    except Exception as e:
        return f"AI analysis temporarily unavailable: {str(e)}"

async def generate_portfolio_report(assets: list) -> str:
    if not settings.GEMINI_API_KEY:
        return "AI portfolio analysis unavailable. Set GEMINI_API_KEY in your .env file."
        
    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        
        formatted_assets = ""
        for a in assets:
            formatted_assets += f"- {a.get('name')} ({a.get('asset_type')}): {a.get('current_price')} (Change: {a.get('change_pct')}%)\n"
            
        prompt_config = SYSTEM_PROMPTS.get("portfolio_report_prompt", {})
        prompt = f"SYSTEM INSTRUCTIONS:\n{json.dumps(prompt_config, indent=2)}\n\nUSER REQUEST: Here is a portfolio summary:\n{formatted_assets}\nAssess the portfolio health. Highlight how recent global/local events impacted the winners and losers. Warn against any hype-inflated assets held, and suggest historically stable alternatives matching the portfolio's value level."
        
        response = await client.aio.models.generate_content(model='gemini-3.5-flash', contents=prompt)
        return response.text
    except Exception as e:
        return f"AI portfolio analysis temporarily unavailable: {str(e)}"
