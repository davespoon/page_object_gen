from __future__ import annotations

from dataclasses import dataclass
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


@dataclass(frozen=True)
class CapturedPage:
    url_requested: str
    url_final: str
    title: str
    html: str


def capture_page(url: str, *, headless: bool = True, timeout_seconds: int = 30) -> CapturedPage:
    """
    Open the given URL in Chrome and return final URL, title, and page HTML.

    Uses Selenium Manager automatically (no driver binaries required).
    """
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1600,900")
    opts.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(timeout_seconds)
    try:
        driver.get(url)

        try:
            driver.execute_script(
                """
                const cb = arguments[arguments.length - 1];
                const start = Date.now();
                (function poll(){
                  if (document.readyState === 'complete') return cb(true);
                  if (Date.now() - start > 15000) return cb(false);
                  setTimeout(poll, 100);
                })();
                """
            )
        except Exception:
            pass

        html = driver.page_source or ""
        title = driver.title or ""
        url_final = driver.current_url or url

        return CapturedPage(
            url_requested=url,
            url_final=url_final,
            title=title,
            html=html,
        )
    finally:
        driver.quit()
