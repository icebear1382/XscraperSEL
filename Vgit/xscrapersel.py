import time
from urllib.parse import quote, urlparse
from datetime import datetime
import pandas as pd

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

X_COOKIE_NAME = "auth_token"
X_COOKIE_VALUE = "f2ab242bb3bdbc05105cabe118e348efac300fd6"
X_DOMAIN = ".x.com"

def inject_cookie(driver):
    """
    تزریق auth_token به مرورگر برای لاگین بدون نیاز به username/password
    """
    driver.get("https://x.com")      # لازم است یکبار دامنه لود شود
    time.sleep(2)

    driver.add_cookie({
        "name": X_COOKIE_NAME,
        "value": X_COOKIE_VALUE,
        "domain": X_DOMAIN
    })

    driver.refresh()
    time.sleep(2)

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options,
    )
    return driver


def manual_login(driver):
    driver.get("https://x.com/login")
    print("مرورگر باز شد. لطفاً توی X لاگین کن.")
    input("وقتی کامل لاگین شدی Enter بزن...")


def parse_like_count(article):
    """
    تعداد لایک را از داخل article استخراج می‌کند.
    سعی می‌کند element با data-testid='like' را پیدا کند و عددش را بخواند.
    """
    try:
        like_btn = article.find_element(By.XPATH, ".//*[@data-testid='like']")
    except Exception:
        return 0

    # معمولاً یک span داخلش هست که عدد را دارد
    spans = like_btn.find_elements(By.TAG_NAME, "span")
    text = ""
    for sp in spans:
        t = sp.text.strip()
        if t:
            text = t
            break

    if not text:
        return 0

    # تبدیل رشته به عدد: هندل '1,234', '2.5K', '1.2M' و ...
    text = text.replace(",", "").upper()

    try:
        if text.endswith("K"):
            return int(float(text[:-1]) * 1000)
        if text.endswith("M"):
            return int(float(text[:-1]) * 1_000_000)
        return int(text)
    except ValueError:
        return 0


def parse_user_info(article):
    """
    گرفتن display name و username از بلوک User-Name.
    X معمولاً یه data-testid=User-Name دارد که هم name و هم @username داخلش است.
    """
    display_name = None
    username = None

    try:
        user_block = article.find_element(By.XPATH, ".//*[@data-testid='User-Name']")
        spans = user_block.find_elements(By.TAG_NAME, "span")
        for sp in spans:
            txt = sp.text.strip()
            if not txt:
                continue
            if txt.startswith("@"):
                username = txt.lstrip("@")
            else:
                # اولی که @ نیست رو به‌عنوان display name می‌گیریم
                if display_name is None:
                    display_name = txt
    except Exception:
        pass

    # اگر username رو نتونستیم از این راه بگیریم، از URL استفاده می‌کنیم
    if username is None:
        try:
            link_els = article.find_elements(By.XPATH, ".//a[contains(@href, '/status/')]")
            if link_els:
                href = link_els[0].get_attribute("href")
                if href:
                    parts = urlparse(href).path.split("/")
                    if len(parts) >= 3:
                        username = parts[1]
        except Exception:
            pass

    return display_name, username


def scrape_tweets(
    driver,
    keyword: str,
    max_tweets: int = 100,
    since: str | None = None,
    until: str | None = None,
):
    """
    سرچ keyword در X و جمع کردن tweetها با Selenium.
    اگر since / until داده شود، از فیلتر تاریخ خود X استفاده می‌کنیم:
      - since: 'YYYY-MM-DD'
      - until: 'YYYY-MM-DD'
    """

    search_query = keyword
    if since:
        search_query += f" since:{since}"
    if until:
        search_query += f" until:{until}"

    q = quote(search_query)
    search_url = f"https://x.com/search?q={q}&src=typed_query&f=live"
    driver.get(search_url)
    time.sleep(5)

    rows = []
    seen_ids = set()

    last_height = driver.execute_script("return document.body.scrollHeight")
    same_height_count = 0

    limit = max_tweets if max_tweets and max_tweets > 0 else None

    while True:
        articles = driver.find_elements(By.XPATH, "//article[@role='article']")

        for art in articles:
            try:
                # اول URL توییت
                link_els = art.find_elements(By.XPATH, ".//a[contains(@href, '/status/')]")
                if not link_els:
                    continue

                href = link_els[0].get_attribute("href")
                if not href:
                    continue

                parsed = urlparse(href)
                parts = parsed.path.split("/")  # ['', 'username', 'status', 'id']
                if len(parts) < 4:
                    continue

                tweet_id = parts[3]
                if tweet_id in seen_ids:
                    continue
                seen_ids.add(tweet_id)

                # متن توییت
                text_els = art.find_elements(By.XPATH, ".//*[@data-testid='tweetText']")
                if text_els:
                    text = text_els[0].text
                else:
                    text = art.text

                # تاریخ
                time_els = art.find_elements(By.TAG_NAME, "time")
                if time_els:
                    created_at = time_els[0].get_attribute("datetime")
                else:
                    created_at = None

                # نام و یوزرنیم
                display_name, username = parse_user_info(art)
                if username is None:
                    # حداقل یه چیزی برای user_id داشته باشیم
                    username = ""

                # تعداد لایک
                likes = parse_like_count(art)

                rows.append(
                    {
                        "user_id": username,          # ستون ۱
                        "name": display_name,         # ستون ۲
                        "tweet": text,                # ستون ۳
                        "date": created_at,           # ستون ۴
                        "likes": likes,               # ستون ۵
                    }
                )

                print(f"[{len(rows)}] @{username} ({display_name}): {text[:60]!r} | likes={likes}")

                # اگر limit داریم و رسیدیم، برگرد
                if limit is not None and len(rows) >= limit:
                    return pd.DataFrame(rows)

            except Exception:
                continue

        # اسکرول به پایین
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            same_height_count += 1
            if same_height_count >= 3:
                break
        else:
            same_height_count = 0
            last_height = new_height

    return pd.DataFrame(rows)


def main():
    keyword = input("Enter Your Keyword:").strip()
    if not keyword:
        print("You Did'nt enter a Keyword, Exit")
        return

    try:
        max_tweets = int(input("Maximum tweet count to Scrape:(0 = no limit)").strip() or "0")
    except ValueError:
        print("Not a number, Exit")
        return

    if max_tweets < 0:
        print("Negative number, Exit")
        return

    since = input("Enter from Date YYYY-MM-DD").strip()
    if not since:
        since = None

    until = input("Enter To Date YYYY-MM-DD").strip()
    if not until:
        until = None

    driver = setup_driver()
    inject_cookie(driver)

    driver.get("https://x.com/home")
    time.sleep(3)

    if "Login" in driver.page_source or "log in" in driver.page_source:
        print("Cookie was'nt accepted. Not logged in")
    else:
        print("Logged in with Cookie")

    
    try:
        # manual_login(driver)
        df = scrape_tweets(driver, keyword, max_tweets=max_tweets, since=since, until=until)

        if df.empty:
            print("No tweets were found.")
            return

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"x_selenium_{keyword.replace(' ', '_')}_{ts}.xlsx"
        df.to_excel(filename, index=False)
        print(f"\n✅ {len(df)} Saved in: {filename}")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
