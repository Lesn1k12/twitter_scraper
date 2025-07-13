import asyncio
from playwright.async_api import async_playwright
import os, re
from datetime import datetime, timezone
from dotenv import load_dotenv
from gologin import GoLogin
import openai
import asyncpg

load_dotenv()

TWITTER_EMAIL = os.getenv("TWITTER_EMAIL", "")
TWITTER_PASSWORD = os.getenv("TWITTER_PASSWORD", "")

GLOGIN_API_KEY = os.getenv("GLOGIN_API_KEY", "")
GLOGIN_PROFILE_ID = os.getenv("GLOGIN_PROFILE_ID", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

STORAGE_PATH = "playwright_storage/twitter_session.json"

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "logs")

pool = None

async def init_db():
    global pool
    pool = await asyncpg.create_pool(
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        database=POSTGRES_DB,
        host=POSTGRES_HOST,
        port=POSTGRES_PORT
    )
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS session_logs (
                id SERIAL PRIMARY KEY,
                twitter_handle TEXT,
                timestamp TIMESTAMPTZ,
                tweet_content TEXT,
                ai_reply TEXT,
                likes INTEGER,
                retweets INTEGER
            );
        """)
    print("[+] bd is ready.")

async def log_tweet_to_db(tweet, ai_reply=None):
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO session_logs (twitter_handle, timestamp, tweet_content, ai_reply, likes, retweets)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, "(unknown)", datetime.now(timezone.utc), tweet["content"], ai_reply, tweet["likes"], tweet["retweets"])



async def generate_comment(tweet_text):
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    prompt = f"Write a short friendly comment in English for this post:\n\n\"{tweet_text}\"\n\nComment:"
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=50,
        temperature=0.7,
    )
    comment = response.choices[0].message.content.strip()
    return comment

def extract_last_4_numbers_from_text(text):
    tokens = text.strip().split()

    numbers = [t for t in tokens if re.match(r'^\d', t)]

    if len(numbers) >= 4:
        last_four = numbers[-4:]
        return [parse_number(n) for n in last_four]
    else:
        return [0, 0, 0, 0]

def parse_number(s):
    s = s.replace(',', '')
    if 'K' in s: return int(float(s.replace('K', '')) * 1000)
    if 'M' in s: return int(float(s.replace('M', '')) * 1000000)
    try: return int(s)
    except ValueError: return 0

async def wait_and_query(page, selector, timeout=3000):
    try:
        await page.wait_for_selector(selector, timeout=timeout)
        return await page.query_selector(selector)
    except:
        return None

async def collect_tweets(page):
    tweets = dict()
    attempts = 0
    while len(tweets) < 20 and attempts < 20:
        articles = await page.query_selector_all('article[role="article"]')
        for article in articles:
            spans = await article.query_selector_all('div[lang] > span')
            parts = [await span.inner_text() for span in spans]
            content = ' '.join(parts).strip()
            if not content: continue
            content_hash = hash(content)
            if content_hash in tweets: continue
            anchor = await article.query_selector('a[href*="/status/"]')
            href = await anchor.get_attribute("href") if anchor else None
            tweet_url = f"https://x.com{href}" if href else None
            replies, retweets, likes, views = extract_last_4_numbers_from_text(content)
            tweets[content_hash] = {
                "content": content, "tweet_url": tweet_url,
                "replies": replies, "retweets": retweets, "likes": likes, "views": views
            }
            print(f"[+] Зібрано твіт: {content[:50]}... url: {tweet_url}")
        await page.mouse.wheel(0, 1000)
        await page.wait_for_timeout(1000)
        attempts += 1
    return list(tweets.values())


async def main():
    await init_db()

    gl = GoLogin({
        "token": GLOGIN_API_KEY,
        "profile_id": GLOGIN_PROFILE_ID,
        # "extra_params": ["--headless"]
    })
    debugger_address = gl.start()
    print(f"[+] : http://{debugger_address}")

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(f"http://{debugger_address}")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()

        try:
            await page.goto("https://x.com/login")
            print("[+] Navigated to Twitter login page")

            selectors = [
                'input[name="text"]',
                'input[autocomplete="username"]',
                'input[placeholder*="e-mail"]',
                'input[placeholder]'
            ]
            email_field = None
            for sel in selectors:
                email_field = await wait_and_query(page, sel)
                if email_field: break

            if email_field:
                await email_field.fill(TWITTER_EMAIL)
                await page.keyboard.press("Enter")
                await page.wait_for_timeout(2000)
                pwd_field = await wait_and_query(page, 'input[name="password"]')
                if pwd_field:
                    await pwd_field.fill(TWITTER_PASSWORD)
                    await page.keyboard.press("Enter")
                    print("[+] login done")
            else:
                print("[!] field not found for email input")

            await page.wait_for_selector('article[role="article"]', timeout=15000)
            print("[+] main page")

        except Exception as e:
            print(f"[-] logging err: {e}")

        tweets_data = await collect_tweets(page)
        print(f"[+] unique tweets: {len(tweets_data)}")
        for t in tweets_data:
            await log_tweet_to_db(t)

        best = max(tweets_data, key=lambda t: t["likes"] + t["retweets"], default=None)
        if best and best["tweet_url"]:
            await page.goto(best["tweet_url"])
            print(f"[+] best tweet: {best['tweet_url']}")

            await page.wait_for_timeout(2000)
            await page.wait_for_selector('[data-testid="retweet"]', timeout=5000)
            rt_btn = await page.query_selector('[data-testid="retweet"]')
            if rt_btn:
                await rt_btn.click()
                await page.wait_for_selector('[data-testid="retweetConfirm"]', timeout=5000)
                conf_btn = await page.query_selector('[data-testid="retweetConfirm"]')
                if conf_btn:
                    await conf_btn.click()
                    print("[+] Retweet done")

            close_btn = await wait_and_query(page, 'button[data-testid="app-bar-close"]', 3000)
            if close_btn:
                await close_btn.click()
                print("[+] Popup closed")

            reply_box = await wait_and_query(page, 'div[data-testid="tweetTextarea_0"]', 5000)
            if reply_box:
                await reply_box.click()
                comment = await generate_comment(best["content"])
                await reply_box.fill(comment)
                await log_tweet_to_db(best, ai_reply=comment)
                print("[+] Generated comment:", comment)
                await page.wait_for_timeout(10000)
                reply_button = await page.query_selector('[data-testid="tweetButton"]') or \
                        await page.query_selector('[data-testid="tweetButtonInline"]')
                if reply_button:
                    try:
                        await reply_button.click(timeout=2000)
                        print("[+] Reply submitted normally.")
                    except:
                        print("[!] Normal click failed, trying force click...")
                        await reply_button.click(force=True)
                        print("[+] Reply submitted with force click.")
                else:
                    print("[!] Reply button not found — fallback to Enter.")
                    await reply_box.press("Enter")
        else:
            print("[-] No tweets found or best tweet is None")

        await browser.close()

    gl.stop()
    print("[+] Browser closed, GoLogin stopped.")

asyncio.run(main())



