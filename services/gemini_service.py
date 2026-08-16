import json
import os
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from config import settings

PROMPTS_FILE = os.path.join(os.path.dirname(__file__), "prompts.json")
try:
    with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
        SYSTEM_PROMPTS = json.load(f)
except Exception:
    SYSTEM_PROMPTS = {}

# Define exact, strict schemas for the AI to follow
class DailyUpdateResponse(BaseModel):
    market_analysis: str = Field(description="2-3 sentences explaining today's movement simply and honestly")
    event_reasoning: str = Field(description="Clear explanation of the global or local events causing this change")
    hype_check: str = Field(description="Reality check on whether the current price is driven by fundamentals or hype")
    performance_context: str = Field(description="How this fits into the bigger picture")
    investor_perspective: str = Field(description="What a long-term investor should actually focus on right now")
    action_items: str = Field(description="Specific, practical thoughts")
    key_takeaway: str = Field(description="One honest, grounding principle to remember")

class DisasterAlertResponse(BaseModel):
    situation_assessment: str
    severity_rating: str = Field(description="NORMAL_DIP, MAJOR_DROP, or CRASH")
    event_reasoning: str
    hype_check: str
    historical_precedent: str
    worst_case_scenario: str
    decision_framework: str
    action_guidance: str
    alternative_suggestions: list[str] = Field(description="Suggest 1-2 historically stable alternative stocks/ETFs in a similar price bracket")

class PortfolioReportResponse(BaseModel):
    executive_summary: str
    market_and_event_context: str
    winners_and_losers: str
    hype_warning: str = Field(description="Call out any assets that seem driven purely by hype rather than fundamentals.")
    diversification_check: str
    strategic_thoughts: str
    alternative_suggestions: list[str]
    behavioral_coaching: str

DISCLAIMER = "\n\n---\n*⚠️ Caution: My analysis is for your learning and perspective only. Please do not use this as direct financial advice for making trading decisions.*"

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
            user_msg = f"URGENT: {name} has dropped {change_pct}% today. Explain the global or local events causing this drop. Assess if this is a hype bubble bursting. Suggest safer alternatives in a similar price bracket. Keep the investor calm but be honest."
            schema = DisasterAlertResponse
        else:
            prompt_config = SYSTEM_PROMPTS.get("daily_update_prompt", {})
            user_msg = f"Analyze the performance of {name} ({asset_type}). Current: {current_price}, Previous: {previous_price}, Change: {change_pct}%. Connect this performance to specific global/local events. Warn if the stock is hype-driven, and suggest alternative solid investments in a similar price range."
            schema = DailyUpdateResponse
            
        sys_instruction = f"SYSTEM INSTRUCTIONS:\n{json.dumps(prompt_config, indent=2)}\n{json.dumps(SYSTEM_PROMPTS.get('key_principles', {}))}"

        response = await client.aio.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_msg,
            config=types.GenerateContentConfig(
                system_instruction=sys_instruction,
                response_mime_type="application/json",
                response_schema=schema,
            ),
        )
        
        # Parse the JSON and assemble into a conversational markdown block
        data = json.loads(response.text)
        
        if is_alert:
            formatted = f"**Severity:** {data.get('severity_rating')}\n\n{data.get('situation_assessment')}\n\n"
            formatted += f"**What Happened:** {data.get('event_reasoning')}\n\n**Hype Check:** {data.get('hype_check')}\n\n"
            formatted += f"**Historical Precedent:** {data.get('historical_precedent')}\n\n**Worst Case:** {data.get('worst_case_scenario')}\n\n"
            formatted += f"**Next Steps:** {data.get('decision_framework')} {data.get('action_guidance')}\n\n"
            if data.get('alternative_suggestions'):
                formatted += f"**Alternatives to Consider:**\n" + "\n".join([f"- {a}" for a in data.get('alternative_suggestions', [])])
        else:
            formatted = f"{data.get('market_analysis')}\n\n**The 'Why' (Events):** {data.get('event_reasoning')}\n\n"
            formatted += f"**Hype Check:** {data.get('hype_check')}\n\n"
            formatted += f"**Big Picture:** {data.get('performance_context')} {data.get('investor_perspective')}\n\n"
            formatted += f"**Takeaway:** {data.get('key_takeaway')}\n\n**Action Items:** {data.get('action_items')}"

        return formatted + DISCLAIMER
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
        user_msg = f"Here is a portfolio summary:\n{formatted_assets}\nAssess the portfolio health. Highlight how recent global/local events impacted the winners and losers. Warn against any hype-inflated assets held, and suggest historically stable alternatives matching the portfolio's value level."
        
        sys_instruction = f"SYSTEM INSTRUCTIONS:\n{json.dumps(prompt_config, indent=2)}\n{json.dumps(SYSTEM_PROMPTS.get('key_principles', {}))}"

        response = await client.aio.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_msg,
            config=types.GenerateContentConfig(
                system_instruction=sys_instruction,
                response_mime_type="application/json",
                response_schema=PortfolioReportResponse,
            ),
        )
        
        data = json.loads(response.text)
        
        formatted = f"### Executive Summary\n{data.get('executive_summary')}\n\n"
        formatted += f"### Market & Event Context\n{data.get('market_and_event_context')}\n\n"
        formatted += f"### Winners & Losers\n{data.get('winners_and_losers')}\n\n"
        formatted += f"### Hype Warning ⚠️\n{data.get('hype_warning')}\n\n"
        formatted += f"### Diversification & Strategy\n{data.get('diversification_check')} {data.get('strategic_thoughts')}\n\n"
        
        if data.get('alternative_suggestions'):
            formatted += f"### Stable Alternatives\n" + "\n".join([f"- {a}" for a in data.get('alternative_suggestions', [])]) + "\n\n"
            
        formatted += f"**Final Thought:** {data.get('behavioral_coaching')}"

        return formatted + DISCLAIMER
    except Exception as e:
        return f"AI portfolio analysis temporarily unavailable: {str(e)}"
