import anthropic
import trafilatura
import config

# Verify model ID at: https://docs.anthropic.com/en/docs/about-claude/models
MODEL = "claude-haiku-4-5-20251001"

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


def parse_one(raw_html: str, source: str, url: str | None = None) -> dict | None:
    """Extract deal info from raw HTML. Returns dict or None if not SLC-relevant."""
    text = trafilatura.extract(raw_html) or raw_html[:3000]

    response = _get_client().messages.create(
        model=MODEL,
        max_tokens=512,
        tools=[{
            "name": "extract_deal",
            "description": "Extract deal or giveaway info from scraped text",
            "input_schema": {
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
        }],
        tool_choice={"type": "tool", "name": "extract_deal"},
        system=(
            "Extract deal or giveaway info from scraped text. "
            "Set is_slc_utah_relevant=false if not relevant to Salt Lake City / Utah, "
            "or if no actual deal/giveaway is present. "
            "Set requires_manual_entry=true if entry needs social actions (like, follow, comment). "
            "Value score: 10=cash $100+, 9=cash $50-99, 8=free meal, 7=gift card $50+, "
            "6=gift card $20-49, 5=free product, 4=50%+ off, 3=25-49% off, 2=notable deal, 1=minor. "
            "expiry_date: ISO YYYY-MM-DD or null."
        ),
        messages=[{
            "role": "user",
            "content": f"Source: {source}\nURL: {url}\n\n{text[:3500]}"
        }],
    )

    result = response.content[0].input
    result["source"] = source
    return result  # caller filters on is_slc_utah_relevant
