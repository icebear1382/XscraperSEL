# X (Twitter) Search Scraper with Selenium

This script uses Selenium to scrape search results from X (Twitter) and
export them to an Excel file.

It opens `https://x.com/search` for a given keyword, scrolls the page,
and extracts basic metadata for each tweet.

> Note: The CLI prompts are in Persian, but the script itself and output
> are usable in any language.

------------------------------------------------------------------------

## Features

-   Uses **Selenium + Chrome** to load the real X UI.
-   Searches X for a given **keyword or phrase**.
-   Scrolls the search results feed and collects tweets until:
    -   the page stops loading new content, or\
    -   the configured `max_tweets` limit is reached.
-   Extracts:
    -   `user_id` (username without `@`)
    -   `name` (display name)
    -   `tweet` (full text)
    -   `date` (ISO timestamp from the `<time>` element, if present)
    -   `likes` (parsed from the like button: supports raw numbers,
        `1.2K`, `3.4M`, etc.)
-   Saves everything as an **Excel file**:\
    `x_selenium_<keyword>_<YYYYMMDD_HHMMSS>.xlsx`

------------------------------------------------------------------------

## Requirements

-   Python 3.9+ (recommended)
-   Google Chrome installed
-   The following Python packages:
    -   `selenium`
    -   `webdriver-manager`
    -   `pandas`
    -   `openpyxl` (for `DataFrame.to_excel`)

Install them with:

``` bash
pip install selenium webdriver-manager pandas openpyxl
```

------------------------------------------------------------------------

## Cookie-Based Login (Optional but Recommended)

To access full search results (and avoid being treated like a logged-out
user), you can log in with an **`auth_token` cookie** from your X
account.

In your script, you should have something like:

``` python
X_COOKIE_NAME = "auth_token"
X_COOKIE_VALUE = "YOUR_AUTH_TOKEN_HERE"
X_DOMAIN = ".x.com"

def inject_cookie(driver):
    driver.get("https://x.com")
    time.sleep(2)

    driver.add_cookie({
        "name": X_COOKIE_NAME,
        "value": X_COOKIE_VALUE,
        "domain": X_DOMAIN,
    })

    driver.refresh()
    time.sleep(2)
```

And in `main()`:

``` python
driver = setup_driver()
inject_cookie(driver)
```

### How to get `auth_token`

1.  Log in to X in your browser.
2.  Open **Developer Tools → Application → Storage → Cookies** (or
    similar, depending on the browser).
3.  Find cookie named `auth_token` for `.x.com`.
4.  Copy its value and paste it into `X_COOKIE_VALUE`.

**Keep this token secret.** It is effectively a login session.

------------------------------------------------------------------------

## Usage

From the directory containing `xscrapersel.py`:

``` bash
python xscrapersel.py
```

The script will prompt you in the terminal:

1.  `کلمه / عبارت سرچ در X:`\
    → Enter any keyword or phrase you want to search on X.

2.  `حداکثر تعداد tweet (مثلاً 200، 0 = تا جایی که می‌شه):`

    -   Enter an integer:
        -   `0` = no hard limit (scrape as much as the page can load)
        -   `N` = stop after **approximately** N tweets collected

The script will:

-   Open Chrome.

-   (Optionally) inject your login cookie.

-   Load the search page and start scrolling.

-   Print progress for each tweet, e.g.:

    ``` text
    [15] @username (Display Name): 'some text...' | likes=42
    ```

-   When done, save an Excel file in the current directory, for example:

    ``` text
    x_selenium_python_20251127_153045.xlsx
    ```

------------------------------------------------------------------------

## Output Schema

The exported Excel file contains the following columns:

-   `user_id` -- X username (without `@`)
-   `name` -- display name
-   `tweet` -- tweet text
-   `date` -- timestamp from the tweet's `<time>` element (if available)
-   `likes` -- integer like count (e.g., `"2.5K"` → `2500`)

------------------------------------------------------------------------

## Limitations

-   This is a **UI scraper**. It depends heavily on:
    -   X's HTML structure
    -   `data-testid` attributes
    -   the existence of certain elements (`tweetText`, `User-Name`,
        `like`, etc.)
-   If X changes its frontend, selectors may break and you'll need to
    update the XPaths.
-   X does not guarantee that the search feed will go back "forever".
    Even with scrolling, you usually get:
    -   a limited time range, and
    -   rate limiting / throttling if you push too hard.
-   Using `auth_token` directly is fragile:
    -   It may expire.
    -   It may be invalidated if you log out or change your password.
    -   Treat it like a password.

------------------------------------------------------------------------

## Legal / Terms of Use

-   This script is for **personal / educational use**.
-   Check X's **Terms of Service** and any applicable laws before
    scraping.
-   Respect rate limits and avoid abusive behavior.

------------------------------------------------------------------------
