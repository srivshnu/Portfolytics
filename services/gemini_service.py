import json
import os
import asyncio
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

# Model priority list — tries each in order if the previous is overloaded
GEMINI_MODELS = [
    "gemini-3.7-flash",    # Latest & fastest
    "gemini-3.5-flash",    # Stable fallback
    "gemini-3.1-flash-lite",  # Lightweight last resort
]

async def _generate(client, system_instruction: str, user_msg: str, schema) -> str:
    """Try models in order; fall back on 503/429 overload errors."""
    last_err = None
    for model in GEMINI_MODELS:
        try:
            response = await client.aio.models.generate_content(
                model=model,
                contents=user_msg,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=schema,
                ),
            )
            return response.text
        except Exception as e:
            err_str = str(e)
            if "503" in err_str or "429" in err_str or "UNAVAILABLE" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                last_err = e
                await asyncio.sleep(1)  # brief pause before retrying next model
                continue
            raise  # Any other error (404, auth, etc.) — raise immediately
    raise last_err  # All models failed

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
    educational_guidance: str = Field(description="Educate the user on what qualities make a company historically stable, without suggesting specific tickers")

class PortfolioReportResponse(BaseModel):
    executive_summary: str
    market_and_event_context: str
    winners_and_losers: str
    hype_warning: str = Field(description="Call out any assets that seem driven purely by hype rather than fundamentals.")
    diversification_check: str
    strategic_thoughts: str
    diversification_education: str = Field(description="Discuss historically stable asset classes to offset weaknesses, without suggesting specific tickers")
    behavioral_coaching: str

class MarketEducationItem(BaseModel):
    name: str = Field(description="Name of the stock or mutual fund")
    change_pct: str = Field(description="Today's percentage change, e.g. +3.2%")
    reason: str = Field(description="Simple 2-3 sentence educational explanation of WHY this asset performed well today in 10th-grade language, citing real events or business fundamentals")

class MarketEducationResponse(BaseModel):
    intro: str = Field(description="1 friendly opening sentence for the Education Corner section")
    top_stocks: list[MarketEducationItem] = Field(description="Top 3 performing stocks today with educational reasoning")
    top_mfs: list[MarketEducationItem] = Field(description="Top 3 performing mutual funds today with educational reasoning")
    closing_lesson: str = Field(description="One grounding educational lesson the user can learn from today's top performers")

DISCLAIMER = "\n\n---\n*⚠️ Caution: My analysis is for your learning and perspective only. Please do not use this as direct financial advice for making trading decisions.*"

async def generate_market_education(top_performers: dict) -> str:
    """Generate an educational 'Education Corner' section about today's top performers."""
    if not settings.GEMINI_API_KEY:
        return ""
    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        stocks_text = "\n".join([f"- {s['name']} ({s['ticker']}): +{s['change_pct']:.2f}%" for s in top_performers.get("top_stocks", [])])
        mfs_text = "\n".join([f"- {m['name']}: +{m['change_pct']:.2f}%" for m in top_performers.get("top_mfs", [])])
        user_msg = (
            f"Today's top performing stocks:\n{stocks_text}\n\n"
            f"Today's top performing mutual funds:\n{mfs_text}\n\n"
            "For each of these, explain in simple 10th-grade language WHY they performed well today. "
            "Link it to real events, sector trends, or business fundamentals. "
            "This is purely educational — do NOT suggest buying any of these. "
            "Close with one broad investment lesson the user can take away from today's market."
        )
        sys_instruction = (
            "You are a PhD economist and trusted close friend explaining today's market winners purely for education. "
            "Never recommend buying. Speak in simple 10th-grade language. Be concise. Link performance to real events."
        )
        raw = await _generate(client, sys_instruction, user_msg, MarketEducationResponse)
        data = json.loads(raw)

        formatted = f"### 📚 Education Corner — Today's Top Performers\n{data.get('intro')}\n\n"
        formatted += "**🏆 Top Stocks Today:**\n"
        for item in data.get("top_stocks", []):
            formatted += f"- **{item.get('name')}** ({item.get('change_pct')}): {item.get('reason')}\n"
        formatted += "\n**🏆 Top Mutual Funds Today:**\n"
        for item in data.get("top_mfs", []):
            formatted += f"- **{item.get('name')}** ({item.get('change_pct')}): {item.get('reason')}\n"
        formatted += f"\n**💡 Today's Lesson:** {data.get('closing_lesson')}"
        formatted += "\n\n*⚠️ This section is purely educational. None of the above are recommendations to buy.*"
        return formatted
    except Exception as e:
        print(f"[Portfolytics] Market education generation failed: {e}")
        return ""


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
            user_msg = f"URGENT: {name} has dropped {change_pct}% today. Explain the global or local events causing this drop. Assess if this is a hype bubble bursting. Educate the user on fundamental qualities of stable assets during a crash. Keep the investor calm but be honest."
            schema = DisasterAlertResponse
        else:
            prompt_config = SYSTEM_PROMPTS.get("daily_update_prompt", {})
            user_msg = f"Analyze the performance of {name} ({asset_type}). Current: {current_price}, Previous: {previous_price}, Change: {change_pct}%. Connect this performance to specific global/local events. Warn if the stock is hype-driven, and provide pure educational guidance."
            schema = DailyUpdateResponse
            
        sys_instruction = f"SYSTEM INSTRUCTIONS:\n{json.dumps(prompt_config, indent=2)}\n{json.dumps(SYSTEM_PROMPTS.get('key_principles', {}))}"

        raw = await _generate(client, sys_instruction, user_msg, schema)
        data = json.loads(raw)
        
        if is_alert:
            formatted = f"**Severity:** {data.get('severity_rating')}\n\n{data.get('situation_assessment')}\n\n"
            formatted += f"**What Happened:** {data.get('event_reasoning')}\n\n**Hype Check:** {data.get('hype_check')}\n\n"
            formatted += f"**Historical Precedent:** {data.get('historical_precedent')}\n\n**Worst Case:** {data.get('worst_case_scenario')}\n\n"
            formatted += f"**Next Steps:** {data.get('decision_framework')} {data.get('action_guidance')}\n\n"
            if data.get('educational_guidance'):
                formatted += f"**Educational Guidance:** {data.get('educational_guidance')}"
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
        user_msg = f"Here is a portfolio summary:\n{formatted_assets}\nAssess the portfolio health. Highlight how recent global/local events impacted the winners and losers. Warn against any hype-inflated assets held, and educate the user on diversification principles."
        
        sys_instruction = f"SYSTEM INSTRUCTIONS:\n{json.dumps(prompt_config, indent=2)}\n{json.dumps(SYSTEM_PROMPTS.get('key_principles', {}))}"

        raw = await _generate(client, sys_instruction, user_msg, PortfolioReportResponse)
        data = json.loads(raw)
        
        formatted = f"### Executive Summary\n{data.get('executive_summary')}\n\n"
        formatted += f"### Market & Event Context\n{data.get('market_and_event_context')}\n\n"
        formatted += f"### Winners & Losers\n{data.get('winners_and_losers')}\n\n"
        formatted += f"### Hype Warning ⚠️\n{data.get('hype_warning')}\n\n"
        formatted += f"### Diversification & Strategy\n{data.get('diversification_check')} {data.get('strategic_thoughts')}\n\n"
        
        if data.get('diversification_education'):
            formatted += f"### Education: Building Stability\n{data.get('diversification_education')}\n\n"
            
        formatted += f"**Final Thought:** {data.get('behavioral_coaching')}"

        return formatted + DISCLAIMER
    except Exception as e:
        return f"AI portfolio analysis temporarily unavailable: {str(e)}"
