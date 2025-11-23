import time, logging, hashlib, re, pickle
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
import argparse, json
import undetected_chromedriver as uc

COOKIE_FILE = "twitter_cookies.pkl"

# -------------Driver Setup-------------------------
def setup_driver(headless=False):
    options = uc.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")

    ua = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
    options.add_argument(f"user-agent={ua}")

    driver = uc.Chrome(options=options)

    # prevent WinError 6 when closing
    try:
        driver._ignore_process_destructor = True
    except:
        pass

    return driver

# ---------------------Cookie Handling------------------------
def save_cookies(driver):
    pickle.dump(driver.get_cookies(), open(COOKIE_FILE, "wb"))
    # print("Cookies saved!")


def load_cookies(driver):
    driver.get("https://x.com")

    try:
        cookies = pickle.load(open(COOKIE_FILE, "rb"))
        for c in cookies:
            driver.add_cookie(c)

        driver.get("https://x.com/home")
        time.sleep(3)

        # print("Cookies loaded, session resumed.")
        return
    except Exception:
        print("No valid cookies. Login required.")
        driver.get("https://x.com/login")
        input("Login manually → go to home page → press ENTER...")
        save_cookies(driver)


# -----------HASH + TWEET EXTRACTION------------------
def tweet_hash(tweet):
    key = (tweet.get("username", "") + tweet.get("timestamp", "") + tweet.get("content", ""))[:300]
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def extract_from_tweet_element(el):
    # USERNAME
    try:
        username = el.find_element(By.XPATH, ".//div[@data-testid='User-Name']").text
    except:
        username = ""

    # CONTENT
    try:
        content = el.find_element(By.XPATH, ".//div[@data-testid='tweetText']").text
    except:
        content = ""

    # TIMESTAMP
    try:
        ts = el.find_element(By.XPATH, ".//time").get_attribute("datetime")
    except:
        ts = ""

    # LIKE,REPLIES,RETWEETS METRICS
    replies = retweets = likes = 0
    try:
        r = el.find_elements(By.CSS_SELECTOR, "button[data-testid='reply']")
        if r: replies = r[-1].text or "0"
    except:
        pass

    try:
        rt = el.find_elements(By.CSS_SELECTOR, "button[data-testid='retweet']")
        if rt: retweets = rt[-1].text or "0"
    except:
        pass

    try:
        lk = el.find_elements(By.CSS_SELECTOR, "button[data-testid='like']")
        if lk: likes = lk[-1].text or "0"
    except:
        pass

    hashtags = re.findall(r"#\w+", content)
    mentions = re.findall(r"@\w+", content)

    return {
        "username": username,
        "timestamp": ts,
        "content": content,
        "likes": likes,
        "retweets": retweets,
        "replies": replies,
        "hashtags": hashtags,
        "mentions": mentions
    }

def contains_stock_tag(HASHTAGS,text: str) -> bool:
    #print("inside contains_stock_tag")
    # print("data content: ",text)
    text = text.lower()
    return any(tag in text for tag in HASHTAGS)

# -------------Tweet Scraper-----------------------
def search_hashtag(driver, hashtag: str,  hashtags,scrolls=50,delay=1.0):
    query = hashtag.replace("#", "%23")
    url = f"https://x.com/search?q={query}&src=typed_query&f=live"
    # print("Opening:", url)

    driver.get(url)
    time.sleep(4)

    seen = set()
    last_height = driver.execute_script("return document.body.scrollHeight")

    for i in range(scrolls):

        # ---------- SCROLL CONTROL ----------
        driver.execute_script("window.scrollBy(0, 500);")
        time.sleep(delay)

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(delay + 0.8)

        # ---------- CAPTURE TWEETS ----------
        cards = driver.find_elements(By.CSS_SELECTOR, "article[data-testid='tweet']")
        # print(f"Scroll {i} → {len(cards)} tweets on screen")

        for el in cards:
            data = extract_from_tweet_element(el)

            if not contains_stock_tag(hashtags,data["content"]):
                continue

            h = tweet_hash(data)
            if h in seen:
                continue

            seen.add(h)
            yield data

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:  # no more tweets loading
            # print("Reached end of page.")
            break

        last_height = new_height

# ---------Scraper for multiple tags---------------------
def scrape_multiple_hashtags(driver, hashtags, limit_per_tag=100, scrolls=50):
    print("Collecting tweets..please wait")
    all_tweets = {}
    final_output = []

    for tag in hashtags:
        # print(f"\n=== Searching {tag} ===\n")
        for t in search_hashtag(driver, tag, hashtags,scrolls=scrolls):
            h = tweet_hash(t)
            # print("h value: ",h)
            if h not in all_tweets:
                all_tweets[h] = t

            if len(all_tweets) >= limit_per_tag:
                break
    print("Tweets collected successfully")
    return list(all_tweets.values())
    # return all_tweets