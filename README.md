# TrackBucks

**TrackBucks: AI-Powered Behavioral Portfolio Management**

TrackBucks is a full-stack web application designed for savings-oriented retail investors who experience stock market anxiety. Built with **FastAPI, MongoDB, and Jinja2**, the platform allows users to track domestic and international stocks alongside mutual funds with real-time financial data.

What sets TrackBucks apart is its deep integration with **Google's Gemini AI** (with automatic model fallback: 3.7 → 3.5 → 3.1-lite). The AI operates under a carefully engineered persona — a **PhD Economist and trusted close friend** — constrained by JSON-structured system instructions fed via the **Native System Instruction** parameter and enforced through **Pydantic Structured Outputs**. It provides:
- **Event-Based Reasoning**: Links every price movement (growth, loss, or stagnation) to specific global or local events to educate the user on *why* things are changing.
- **Hype Protection**: Actively warns users away from stocks trading on social media hype rather than business fundamentals (e.g., meme stocks, news-driven bubbles).
- **Alternative Suggestions**: Recommends historically stable alternatives in a similar price bracket when an asset underperforms.
- **Disaster Alerts**: Automatically triggers calm, honest crisis communication during steep drops, using historical precedents to prevent panic selling.
- **Behavioral Coaching**: Highlights psychological traps and reinforces long-term wealth creation principles with 10th-grade accessible language and zero sugar-coating.
- **Scheduled Email Reports**: Delivers personalized, AI-generated portfolio reviews directly to the user's inbox via Gmail SMTP.

## Key Features

- **Track Stocks & Mutual Funds** — Add tickers via Yahoo Finance and MF scheme codes via mfapi.in
- **"Did You Mean?" Smart Search** — Fuzzy search for both stocks and mutual funds with suggestion tables
- **AI Analysis with Structured Outputs** — Gemini returns strict JSON (via Pydantic schemas), then assembled into conversational Markdown for display
- **Native System Instructions** — AI persona rules sit at a higher privilege layer in the model's attention mechanism, ensuring consistent tone and format
- **Automatic Model Fallback** — If the primary Gemini model is overloaded (503/429), the app silently falls back through a priority chain
- **Timezone-Aware Scheduling** — Users select their timezone from 597 options; APScheduler triggers reports in the correct local time
- **Scheduled Reports** — Choose daily/weekly frequency and delivery time
- **Disaster Alerts** — Immediate email when assets drop beyond configurable thresholds
- **Premium Email Templates** — HTML emails styled with the Indian ₹500 note palette (cream, sage green, warm brown) with proper Markdown rendering
- **Secure Auth** — bcrypt-hashed passwords, signed session cookies via itsdangerous
- **MongoDB Atlas with Local Fallback** — Tries cloud database first, gracefully falls back to localhost if Atlas is unreachable

## Tech Stack

- **Backend:** FastAPI + Uvicorn
- **Database:** MongoDB Atlas (motor async driver) with local fallback
- **Frontend:** Server-side rendered Jinja2 templates + vanilla CSS (zero JavaScript)
- **AI Engine:** Google Gemini (3.7-flash / 3.5-flash / 3.1-flash-lite) with Native System Instructions & Pydantic Structured Outputs
- **Prompt Engineering:** JSON-formatted prompts for token efficiency, hierarchical attention, and context caching
- **Email:** Gmail SMTP with Markdown-to-HTML rendering
- **Scheduler:** APScheduler with per-user timezone support (pytz)

## AI Architecture

```
┌─────────────────────────────┐
│   prompts.json (v1.2)       │  ← Static persona, rules, output format
│   JSON-structured prompts   │    (cached by the model — lower cost)
└─────────┬───────────────────┘
          │ Injected via native
          │ system_instruction parameter
          ▼
┌─────────────────────────────┐
│   Gemini API                │  ← Higher privilege attention layer
│   + Pydantic Schema         │    (100% guaranteed output structure)
└─────────┬───────────────────┘
          │ Returns strict JSON
          ▼
┌─────────────────────────────┐
│   gemini_service.py         │  ← Parses JSON → assembles into
│   Markdown formatter        │    conversational Markdown for display
└─────────────────────────────┘
```

## Setup

### 1. Install MongoDB Community Edition
Make sure `mongod` is running on `localhost:27017`, or configure MongoDB Atlas.

### 2. Get a Gemini API Key
Visit [Google AI Studio](https://aistudio.google.com/apikey) and create a free API key.

### 3. Create Gmail App Password
1. Enable 2-Factor Authentication on your Google account
2. Go to [App Passwords](https://myaccount.google.com/apppasswords)
3. Generate a new app password for "Mail"

### 4. Configure Environment
Create a `.env` file in the project root:
```env
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority
GEMINI_API_KEY=your_gemini_api_key
SMTP_EMAIL=your_email@gmail.com
SMTP_PASSWORD=your_16_char_app_password
SECRET_KEY=any_long_random_string
```

### 5. Install Dependencies
```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

### 6. Run
```bash
python main.py
```
Open http://localhost:8000 in your browser.

## Project Structure

```
TrackBucks/
├── main.py                  # FastAPI app entry point
├── config.py                # Pydantic Settings from .env
├── database.py              # MongoDB connection (Atlas + local fallback)
├── auth.py                  # Authentication (bcrypt + itsdangerous sessions)
├── routes/
│   ├── pages.py             # GET route handlers (dashboard, settings, etc.)
│   ├── auth_routes.py       # Login / Register / Logout
│   ├── watchlist_routes.py  # Add/remove stocks & mutual funds
│   └── settings_routes.py   # Schedule & alert configuration
├── services/
│   ├── gemini_service.py    # AI integration (Structured Outputs + model fallback)
│   ├── prompts.json         # JSON-structured AI persona & prompt framework (v1.2)
│   ├── stock_service.py     # Yahoo Finance integration
│   ├── mf_service.py        # mfapi.in integration
│   ├── mail_service.py      # Gmail SMTP with HTML templates
│   └── scheduler_service.py # APScheduler (timezone-aware cron/interval jobs)
├── templates/               # Jinja2 HTML templates
├── static/css/              # Stylesheets (Indian ₹500 note palette)
└── requirements.txt         # Python dependencies
```
