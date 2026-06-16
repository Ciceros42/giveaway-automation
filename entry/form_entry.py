import asyncio
from playwright.async_api import async_playwright
from entry.captcha import solve_recaptcha_v2
import config

SEM = asyncio.Semaphore(3)  # max 3 concurrent CAPTCHA solves


async def enter_giveaway(deal: dict, account: dict) -> bool:
    """
    Fill and submit a giveaway entry form.
    account = {"email": ..., "name": ..., "app_password": ...}
    Returns True only if a confirmed success signal is found on the page.
    """
    async with SEM:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                context = await browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    )
                )
                page = await context.new_page()
                await page.goto(deal["entry_url"], wait_until="domcontentloaded", timeout=20000)

                # Fill email
                for selector in ['input[name*="email"]', 'input[type="email"]']:
                    el = await page.query_selector(selector)
                    if el:
                        await page.fill(selector, account["email"])
                        break

                # Fill name
                for selector in [
                    'input[name="name"]',
                    'input[name*="first"]',
                    'input[name*="full"]',
                    'input[placeholder*="name" i]',
                ]:
                    el = await page.query_selector(selector)
                    if el:
                        await page.fill(selector, account["name"])
                        break

                # Handle reCAPTCHA v2
                captcha_el = await page.query_selector(".g-recaptcha")
                if captcha_el:
                    sitekey  = await captcha_el.get_attribute("data-sitekey") or ""
                    callback = await captcha_el.get_attribute("data-callback") or ""
                    if sitekey:
                        token = solve_recaptcha_v2(sitekey, deal["entry_url"])
                        # Inject token and fire data-callback
                        await page.evaluate(f"""
                            (function() {{
                                var el = document.getElementById('g-recaptcha-response');
                                if (el) {{
                                    el.value = "{token}";
                                    el.innerHTML = "{token}";
                                }}
                                if ("{callback}" && typeof window["{callback}"] === "function") {{
                                    window["{callback}"]("{token}");
                                }}
                            }})();
                        """)

                # Submit form
                submit = await page.query_selector(
                    'button[type="submit"], input[type="submit"], button:has-text("Enter"), button:has-text("Submit")'
                )
                if not submit:
                    return False

                await submit.click()
                await page.wait_for_timeout(3000)

                # Verify by checking page text for confirmation signals
                try:
                    page_text = (await page.inner_text("body")).lower()
                except Exception:
                    page_text = ""

                success_signals = [
                    "thank you", "you're entered", "you are entered",
                    "successfully entered", "entry confirmed",
                    "good luck", "submitted", "received your entry",
                ]
                return any(sig in page_text for sig in success_signals)

            finally:
                await browser.close()
