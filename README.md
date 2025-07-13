# Twitter Scraper & Automation Bot

This project automates coordinated activity on Twitter (X) using Playwright, GoLogin, and OpenAI.  
The script logs into Twitter via a GoLogin browser profile, collects tweets from the feed, finds the most engaging tweet (likes + retweets), performs a retweet, generates an AI-based comment, and stores all activity logs in a PostgreSQL database.

---

## 🚀 Features

- Automated login through GoLogin profile and Playwright
- Organic scrolling and scraping of at least 20 unique tweets
- Metrics extraction (likes, retweets, replies, views)
- Retweeting of most popular tweet
- AI-generated reply using GPT-3.5 API
- All tweets and actions logged into PostgreSQL for tracking

---

## 🛠️ Setup instructions

### 1️⃣ Clone repository and navigate:

```bash
git clone https://github.com/yourusername/twitter_scraper.git
cd twitter_scraper
```

### 2️⃣ Create virtual environment:

```bash
python -m venv .venv
# Activate venv:
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate
```
### 3️⃣ Install dependencies:

```bash
pip install -r requirements.txt
```

### 4️⃣ Environment variables configuration
Create a .env file in the project root directory with the following fields:

TWITTER_EMAIL=your-twitter-email
TWITTER_PASSWORD=your-twitter-password

GLOGIN_API_KEY=your-gologin-api-key
GLOGIN_PROFILE_ID=your-gologin-profile-id

OPENAI_API_KEY=your-openai-api-key

POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=twitter_bot

▶️ How to run the bot

```bash
python main.py
```
