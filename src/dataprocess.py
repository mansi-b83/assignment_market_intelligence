import pandas as pd
import numpy as np
import hashlib
import unicodedata
import re
from datetime import datetime
from googletrans import Translator
import regex as reg

translator = Translator()

def is_english(text):
    print("inside is_english")
    try:
        lang = detect(text)
        print("lang boolean: ",lang == "en")
        return lang == "en"
    except LangDetectException:
        return False

def transslate_to_english(content):
    print("inside translate to english")
    try:
        result = translator.translate(content, dest='en')
        return result.content
    except Exception as e:
        print("Translation failed:", e)
        return text  # use original text

def clean_username(username):
    if not username:
        return ""

    # Encoding/decoding username
    try:
        username = username.encode("latin1").decode("utf-8")
    except:
        pass

    # Remove emogis and symbols
    def remove_emojis(t):
        return "".join(
            ch for ch in t
            if not unicodedata.category(ch).startswith(("So","Sk","Sm"))
        )
    username = remove_emojis(username)

    # 3. Remove garbage unicode, keep English + Hindi + valid separators
    # username = re.sub(r"[^\u0900-\u097Fa-zA-Z0-9 .,|\-]+", "", username)

    # Keep letters from ANY language and digits and mmon symbols
    username = reg.sub(r"[^0-9\p{L} .,\-_|]+", "", username)

    # 4. Remove multiple spaces
    username = re.sub(r"\s+", " ", username).strip()

    return username
        
def clean_tweet_content(content):
# """Clean tweet text: remove URLs, mentions, emojis, excessive spaces."""
    # print("normalize data")
    if pd.isna(content):
        return ""

    # text = re.sub(r"http\S+", "", text)            # remove URLs
    # text = re.sub(r"@\w+", "", text)               # remove @mentions
    # text = re.sub(r"#\w+", "", text)               # (optional) remove hashtags
    # text = unicodedata.normalize("NFKD", text)     # normalize unicode/emojis
    # text = re.sub(r"\s+", " ", text).strip()
    # # print("text: ",text)
    # return text

    # change language content
    if not is_english :
        content = translate_to_english(content)
        print("translated content: ",content)
    
    # Remove encoding
    content = content.encode("latin1", "ignore").decode("utf-8", "ignore")

    # Remove URLs
    content = re.sub(r"http\S+|www\S+", "", content)

    # Remove mentions
    content = re.sub(r"@\w+", "", content)

    # Remove emojis & unwanted symbols
    # content = re.sub(r"[^\x00-\x7F]+", "", content)
    
    content = re.sub(r"[\x00-\x1F\x7F]", " ", content)

    # Remove multiple spaces
    content = re.sub(r"\s+", " ", content).strip()

    # If only hashtags present, keep them or replace
    hashtags = re.findall(r"#\w+", content)

    text_only = re.sub(r"#\s+", "", content).strip()

    if text_only == "":  
        # FIXES your blank clean_content
        return " ".join(hashtags) 

    return text_only

def extract_stocktags(hashtags):
     # """Return which stock hashtags match your Indian stock list."""
    INDIAN_STOCK_TAGS = ["#nifty", "#nifty50", "#sensex", "#niftybank", "#banknifty","#stockmarket", "#indiastocks", "#stocks","#trading", "#nse", "#bse", "#optiontrading", "#intraday"]
    low = [t.lower() for t in hashtags]
    return [t for t in low if t in INDIAN_STOCK_TAGS]


def parse_metrics(val):
    # print("inside parse_metrics")
    # Convert likes/retweets/replies like '1K', '3M' to int.
    if pd.isna(val) or val == "":
        return 0

    val = str(val).lower().replace(",", "")

    try:
        if val.endswith("k"):
            return int(float(val[:-1]) * 1000)
        if val.endswith("m"):
            return int(float(val[:-1]) * 1_000_000)
        return int(val)
    except:
        return 0

def extract_handle(username_block):
    # extracting username and handle id for username in data collected
    # print("in extract_handle")
    if pd.isna(username_block):
        return "", ""

    parts = username_block.split("\n")
    if len(parts) < 2:
        return username_block.strip(), ""

    display = parts[0].strip()
    lower = parts[1].lower()

    handle_match = re.search(r"@[\w_]+", lower)
    handle = handle_match.group(0) if handle_match else ""

    return display, handle

def generate_id(handle, timestamp, clean_text):
    # tweet id for each data to uniquely identify if duplicates
    key = f"{handle}|{timestamp}|{clean_text}"
    return hashlib.sha256(key.encode()).hexdigest()

def deduplicate(df):
    # --- Generate unique ID ---
    df["tweet_id"] = df.apply(
        lambda r: generate_id(r["handle"], str(r["timestamp"]), r["clean_content"]),
        axis=1
    )
    
# -------------------deduplication----------------------------
    before = df.shape[0]
    df = df.drop_duplicates(subset=["tweet_id"])
    after = df.shape[0]
    print(f"Removed duplicates: {before - after}")
    return df

def normalizeData(df):
    # print("inside normalizeData")

    new_df = pd.DataFrame()
    
    # --- Fix username into display & handle ---
    new_df["display_name"], new_df["handle"] = zip(*df["username"].apply(extract_handle))

    #-----Clean username-------------------
    new_df["display_name"] = new_df["display_name"].apply(clean_username)

    # --- Extract Indian stock hashtags present ---
    new_df["hashtags"] = df["hashtags"].apply(extract_stocktags)
    
    # --- Clean content ---
    new_df["clean_content"] = df["content"].fillna("").apply(clean_tweet_content)
    # print("clean_content: ",new_df["clean_content"])
    
    # --- Normalize metrics ---
    new_df["likes"] = df["likes"].apply(parse_metrics)
    new_df["retweets"] = df["retweets"].apply(parse_metrics)
    new_df["replies"] = df["replies"].apply(parse_metrics)
    
    # --- Normalize timestamp ---
    new_df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)

    # --- Add processing timestamp ---
    new_df["processed_at"] = datetime.utcnow().isoformat()

    new_df = deduplicate(new_df)
    # print("new_df length: ",new_df.shape[0])

    return new_df