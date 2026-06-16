import json
import trafilatura
from openai import OpenAI
import config

MODEL = "gpt-4o-mini"

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=config.OPENAI_API_KEY)
    return _client


TOOL = {
    "type": "function",
    "function": {
        "name": "extract_deal",
        "description": "Extract deal or giveaway info from scraped text",
        "parameters": {
            "type": "object",
            "properties": {
                "title":                 {"type": "string"},
                "description":           {"type": "string"},
                "entry_url":             {"type": ["string", "null"]},
                "type":                  {"type": "string", "enum": ["giveaway", "deal", "coupon", "contest"]},
                "value_score":           {"type": "integer", "minimum": 1, "maximum": 10},
                "value_description":     {"type": "string"},
                "expiry_date":           {
                    "type": ["string", "null"],
                    "description": "ISO YYYY-MM-DD or null"
                },
                "requires_manual_entry": {"type": "boolean"},
                "is_slc_utah_relevant":  {"type": "boolean"},
            },
            "required": [
                "title", "type", "value_score",
                "requires_manual_entry", "is_slc_utah_relevant"
            ],
        },
    },
}

SYSTEM = (
    "Extract deal or giveaway info from scraped text. "
    "Set is_slc_utah_relevant=false if not relevant to Salt Lake City / Utah, "
    "or if no actual deal/giveaway is present. "
    "Set requires_manual_entry=true if entry needs social actions (like, follow, comment). "
    "Value score: 10=cash $100+, 9=cash $50-99, 8=free meal, 7=gift card $50+, "
    "6=gift card $20-49, 5=free product, 4=50%+ off, 3=25-49% off, 2=notable deal, 1=minor. "
    "expiry_date: ISO YYYY-MM-DD or null."
)


def parse_one(raw_html: str, source: str, url: str | None = None) -> dict | None:
    """Extract deal info from raw HTML. Returns dict or None if not SLC-relevant."""
    text = trafilatura.extract(raw_html) or raw_html[:3000]

    response = _get_client().chat.completions.create(
        model=MODEL,
        max_tokens=512,
        tools=[TOOL],
        tool_choice={"type": "function", "function": {"name": "extract_deal"}},
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"Source: {source}\nURL: {url}\n\n{text[:3500]}"},
        ],
    )

    tool_call = response.choices[0].message.tool_calls[0]
    result = json.loads(tool_call.function.arguments)
    result["source"] = source
    return result  # caller filters on is_slc_utah_relevant
