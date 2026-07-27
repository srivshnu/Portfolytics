# TrackBucks

**TrackBucks: AI-Powered Behavioral Portfolio Management**

TrackBucks is a full-stack web application designed for savings-oriented retail investors who experience stock market anxiety. Built with **FastAPI, MongoDB, and Jinja2**, the platform allows users to track domestic and international stocks alongside mutual funds with real-time financial data. 

What sets TrackBucks apart is its deep integration with **Google's Gemini 3.5 Flash AI**. Instead of generic summaries, the AI is constrained by a highly structured, data-driven "National Institute of Statistics PhD Economist" persona. It provides:
- **Daily Performance Updates**: Contextualizes daily volatility against historical norms and sector averages.
- **Disaster Alerts**: Automatically triggers crisis-communication protocols during steep drops, using historical crash data to prevent panic selling.
- **Behavioral Coaching**: Highlights psychological traps and reinforces long-term wealth creation principles.
- **Scheduled Email Reports**: Delivers personalized, automated insights directly to the user's inbox via a custom APScheduler backend.

## Features

- **Track Stocks & Mutual Funds** — Add tickers (yfinance) and MF scheme codes (mfapi.in)
- **AI Analysis** — Gemini 2.5 Flash explains performance with reasoning
- **Scheduled Reports** — Choose your frequency and time, delivered to Gmail
- **Disaster Alerts** — Immediate email when assets drop beyond your threshold
- **Secure Auth** — bcrypt-hashed passwords, signed session cookies

## Tech Stack

- **Backend:** FastAPI + Uvicorn
- **Database:** MongoDB (motor async driver)
- **Frontend:** Server-side rendered Jinja2 templates + vanilla CSS
- **AI:** Google Gemini 2.5 Flash
- **Email:** Gmail SMTP
- **Scheduler:** APScheduler

## Setup

### 1. Install MongoDB Community Edition
Make sure `mongod` is running on `localhost:27017`.

### 2. Get a Gemini API Key
Visit [Google AI Studio](https://aistudio.google.com/apikey) and create a free API key.

### 3. Create Gmail App Password
1. Enable 2-Factor Authentication on your Google account
2. Go to [App Passwords](https://myaccount.google.com/apppasswords)
3. Generate a new app password for "Mail"

### 4. Configure Environment
```bash
cp .env.example .env
# Edit .env with your actual values
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
├── main.py              # FastAPI app entry point
├── config.py            # Settings from .env
├── database.py          # MongoDB connection
├── auth.py              # Authentication helpers
├── routes/              # HTTP route handlers
├── services/            # Business logic services
├── templates/           # Jinja2 HTML templates
├── static/css/          # Stylesheets
├── .env.example         # Environment variable template
└── requirements.txt     # Python dependencies
```
