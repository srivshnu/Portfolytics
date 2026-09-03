# 📈 Portfolytics

**Portfolytics: AI-Powered Portfolio Education & Alerting Engine**

Portfolytics is a full-stack web application designed for savings-oriented retail investors who experience stock market anxiety. Built with **FastAPI, MongoDB, and Jinja2**, the platform allows users to track domestic and international stocks alongside mutual funds with real-time financial data.

What sets Portfolytics apart is its deep integration with **Google's Gemini AI** (with automatic model fallback: `3.7 → 3.5 → 3.1-lite`). The AI operates under a carefully engineered persona — a **PhD Economist and trusted close friend** — constrained by JSON-structured system instructions fed via the **Native System Instruction** parameter and enforced through **Pydantic Structured Outputs**.

### 🌟 Key Value Pillars
- **Event-Based Reasoning**: Links every price movement (growth, loss, or stagnation) to specific global or local events to educate the user on *why* things are changing.
- **Hype Protection**: Actively warns users away from stocks trading on social media hype rather than business fundamentals (e.g., meme stocks, news-driven bubbles).
- **Strictly Educational Framework**: Stripped entirely of standard robotic "LLM suggestions." The AI is engineered to provide objective, jargon-free education and diversification analysis without offering unsolicited financial advice or behavioral coaching.
- **Disaster Alerts**: Automatically triggers calm, honest crisis communication during steep drops, using historical precedents to prevent panic selling.
- **Scheduled Email Reports**: Delivers personalized, beautifully formatted, AI-generated portfolio reviews directly to the user's inbox via the **Resend API** with automated **SMTP** fallbacks.

---

## 🚀 Core Features

- **Track Stocks & Mutual Funds** — Add tickers via Yahoo Finance and MF scheme codes via `mfapi.in`.
- **Bulletproof Data Fetching** — Bypasses traditional `yfinance` rate limits and IP blocks by utilizing raw HTTP requests to Yahoo's unauthenticated `query1` endpoints, wrapped in a 10-minute caching layer to ensure lightning-fast loading.
- **"Did You Mean?" Smart Search** — Fuzzy search for both stocks and mutual funds with intuitive suggestion tables.
- **AI Analysis with Structured Outputs** — Gemini returns strict JSON (via Pydantic schemas), which is then assembled into conversational Markdown. *(Strictly for educational purposes. Not financial advice).*
- **Native System Instructions** — AI persona rules sit at a higher privilege layer in the model's attention mechanism, ensuring absolute consistency in tone and format.
- **Automatic Model Fallback** — If the primary Gemini model is overloaded (`503`/`429`), the app silently falls back through a priority chain to guarantee uptime.
- **Timezone-Aware Scheduling** — Users select their timezone from 597 options; `APScheduler` triggers reports in the correct local time.
- **Scheduled Reports & Alerts** — Choose daily or weekly frequency and delivery time. Immediate email alerts trigger when assets drop beyond configurable thresholds.
- **Premium Email Templates** — HTML emails styled with an elegant, calming color palette (cream, sage green, warm brown) with robust Markdown rendering (`nl2br`, `sane_lists`).
- **Secure Auth & Fallback DB** — bcrypt-hashed passwords, signed session cookies via `itsdangerous`, and MongoDB Atlas cloud deployment with automatic fallback to `localhost`.

---

## 💻 Tech Stack

- **Backend:** FastAPI + Uvicorn
- **Database:** MongoDB Atlas (motor async driver) with local fallback
- **Frontend:** Server-side rendered Jinja2 templates + vanilla CSS (zero JavaScript required)
- **AI Engine:** Google Gemini (`3.7-flash` / `3.5-flash` / `3.1-flash-lite`) with Native System Instructions & Pydantic Structured Outputs
- **Prompt Engineering:** JSON-formatted prompts for token efficiency, hierarchical attention, and context caching
- **Email:** Resend API & standard SMTP with dynamic Markdown-to-HTML compilation
- **Scheduler:** APScheduler with per-user timezone support (`pytz`)

---

## 🧠 AI Architecture

```text
┌─────────────────────────────┐
│   prompts.json (v1.2)       │  ← Static persona, rules, objective educational format
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
│   Markdown formatter        │    conversational, perfectly spaced Markdown
└─────────────────────────────┘
```

---

## ⚙️ Setup & Installation

### 1. Database Setup
Install **MongoDB Community Edition** and run `mongod` on `localhost:27017`, or configure a **MongoDB Atlas** cluster.

### 2. Get a Gemini API Key
Visit [Google AI Studio](https://aistudio.google.com/apikey) and create a free API key.

### 3. Configure Email Credentials
You can use the Resend API (recommended) or a standard SMTP relay (like Gmail App Passwords).
- **Resend**: Get an API key from [Resend](https://resend.com)
- **Gmail SMTP**: Go to [App Passwords](https://myaccount.google.com/apppasswords) and generate a 16-character password for "Mail".

### 4. Configure Environment
Create a `.env` file in the project root:
```env
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority
GEMINI_API_KEY=your_gemini_api_key

# Email Configuration (Use Resend or SMTP)
RESEND_API_KEY=re_your_resend_api_key
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

### 6. Run the Application
```bash
python main.py
```
*Access the platform at `http://localhost:8000` in your browser.*

---

## 📁 Project Structure

```text
Portfolytics/
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
│   ├── prompts.json         # JSON-structured AI persona & prompt framework
│   ├── stock_service.py     # Custom query1 raw HTTP integration
│   ├── mf_service.py        # mfapi.in integration
│   ├── mail_service.py      # Resend API / SMTP email delivery & HTML templates
│   └── scheduler_service.py # APScheduler (timezone-aware cron/interval jobs)
├── templates/               # Jinja2 HTML templates
├── static/css/              # Stylesheets (Indian ₹500 note calming palette)
└── requirements.txt         # Python dependencies
```
