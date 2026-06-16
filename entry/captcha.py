from twocaptcha import TwoCaptcha
import config


def solve_recaptcha_v2(sitekey: str, page_url: str) -> str:
    """Solve reCAPTCHA v2 via 2captcha. Returns token string."""
    solver = TwoCaptcha(config.TWOCAPTCHA_API_KEY)
    try:
        result = solver.recaptcha(sitekey=sitekey, url=page_url)
        return result["code"]
    except Exception as e:
        raise RuntimeError(f"2captcha solve failed: {e}") from e


def check_balance() -> float:
    """Return current 2captcha balance in USD."""
    solver = TwoCaptcha(config.TWOCAPTCHA_API_KEY)
    return float(solver.balance())
