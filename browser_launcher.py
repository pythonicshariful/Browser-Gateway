import time
import threading
import logging
from config import load_config

logger = logging.getLogger(__name__)

def launch_selenium_browser(browser_name="edge"):
    """
    Launches a real browser (Edge or Chrome) using Selenium, 
    navigates to the domain, injects the cookies, and refreshes the page.
    """
    config = load_config()
    target_url = config.get("target_url", "https://hseconomicsbd.com")
    cookies = config.get("cookies", {})
    domain = config.get("domain", "hseconomicsbd.com")

    driver = None
    try:
        from selenium import webdriver
        from selenium.webdriver.edge.options import Options as EdgeOptions
        from selenium.webdriver.chrome.options import Options as ChromeOptions

        if browser_name.lower() == "chrome":
            options = ChromeOptions()
            options.add_argument("--start-maximized")
            options.add_experimental_option("detach", True)
            driver = webdriver.Chrome(options=options)
        else:
            # Edge is preinstalled on Windows 10/11
            options = EdgeOptions()
            options.add_argument("--start-maximized")
            options.add_experimental_option("detach", True)
            driver = webdriver.Edge(options=options)

        # First visit the domain so the browser accepts cookies for it
        driver.get(target_url)
        time.sleep(1)

        # Inject cookies
        for name, value in cookies.items():
            cookie_dict = {
                "name": name,
                "value": str(value),
                "domain": domain
            }
            try:
                driver.add_cookie(cookie_dict)
            except Exception as e:
                # Fallback if domain matching requires leading dot or host-only
                try:
                    driver.add_cookie({"name": name, "value": str(value)})
                except Exception as inner_e:
                    logger.warning(f"Could not add cookie {name}: {inner_e}")

        # Refresh page to apply authenticated session
        driver.get(target_url)
        return True, f"Successfully launched {browser_name.capitalize()} with cookies."

    except Exception as e:
        logger.error(f"Failed to launch Selenium browser: {e}")
        return False, str(e)

def launch_playwright_browser():
    """
    Launches Chromium using Playwright, sets cookies on context, and navigates.
    """
    config = load_config()
    target_url = config.get("target_url", "https://hseconomicsbd.com")
    cookies = config.get("cookies", {})
    domain = config.get("domain", "hseconomicsbd.com")

    try:
        from playwright.sync_api import sync_playwright

        def _run():
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)
                context = browser.new_context()

                # Add cookies
                cookie_list = [
                    {
                        "name": k,
                        "value": str(v),
                        "domain": domain,
                        "path": "/"
                    }
                    for k, v in cookies.items()
                ]
                context.add_cookies(cookie_list)
                page = context.new_page()
                page.goto(target_url)

                # Keep browser open while interactive
                while browser.is_connected():
                    time.sleep(1)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        return True, "Playwright browser launched in background thread."

    except Exception as e:
        logger.error(f"Failed to launch Playwright: {e}")
        return False, str(e)

def launch_browser(engine=None):
    """
    Dispatches to the best available launcher.
    """
    config = load_config()
    chosen_engine = engine or config.get("browser_type", "edge")

    if chosen_engine == "playwright":
        success, msg = launch_playwright_browser()
        if success:
            return success, msg

    # Default to Selenium with Edge (most reliable on Windows)
    success, msg = launch_selenium_browser("edge" if chosen_engine == "edge" else "chrome")
    if not success and chosen_engine == "chrome":
        # Fallback to Edge if Chrome fails
        success, msg = launch_selenium_browser("edge")

    return success, msg
