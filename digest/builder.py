from datetime import datetime, timezone


def _score_badge(score: int) -> str:
    if score >= 9:  return "🏆"
    if score >= 7:  return "⭐"
    if score >= 5:  return "✅"
    return "🔹"


def _deal_row(deal: dict) -> str:
    badge = _score_badge(deal.get("value_score", 1))
    title = deal.get("title", "Unknown")
    desc  = deal.get("value_description", "")
    url   = deal.get("entry_url") or ""
    expiry= deal.get("expiry_date") or ""
    expiry_str = f" &nbsp;·&nbsp; Expires: {expiry}" if expiry else ""
    link  = f'<a href="{url}" style="color:#2563eb">{title}</a>' if url else title
    return (
        f'<tr>'
        f'<td style="padding:8px 4px">{badge}</td>'
        f'<td style="padding:8px 4px">{link}</td>'
        f'<td style="padding:8px 4px;color:#6b7280">{desc}{expiry_str}</td>'
        f'</tr>'
    )


def build(
    wins: list[dict],
    entered: list[dict],
    manual: list[dict],
    top_deals: list[dict],
) -> str:
    now_str = datetime.now(timezone.utc).strftime("%B %d, %Y")

    sections = []

    # Section 1: Wins
    if wins:
        rows = "".join(
            f'<tr><td style="padding:8px 4px">🎉</td>'
            f'<td style="padding:8px 4px">{w.get("subject","(no subject)")}</td>'
            f'<td style="padding:8px 4px;color:#6b7280">{w.get("inbox_email","")}</td></tr>'
            for w in wins
        )
        sections.append(f"""
        <h2 style="color:#16a34a">🎉 Wins Detected ({len(wins)})</h2>
        <table style="width:100%;border-collapse:collapse">{rows}</table>
        """)

    # Section 2: Auto-entered giveaways
    if entered:
        rows = "".join(_deal_row(d) for d in entered)
        sections.append(f"""
        <h2 style="color:#2563eb">✅ Auto-Entered Giveaways ({len(entered)})</h2>
        <table style="width:100%;border-collapse:collapse">{rows}</table>
        """)

    # Section 3: Manual entry needed
    if manual:
        rows = "".join(_deal_row(d) for d in manual)
        sections.append(f"""
        <h2 style="color:#d97706">👆 Manual Entry Needed ({len(manual)})</h2>
        <p style="color:#6b7280;font-size:13px">These require liking, following, or commenting on social media.</p>
        <table style="width:100%;border-collapse:collapse">{rows}</table>
        """)

    # Section 4: Top deals
    if top_deals:
        rows = "".join(_deal_row(d) for d in top_deals)
        sections.append(f"""
        <h2 style="color:#7c3aed">🔥 Top Deals Today</h2>
        <table style="width:100%;border-collapse:collapse">{rows}</table>
        """)

    if not sections:
        sections.append("<p style='color:#6b7280'>No new deals or giveaways found today.</p>")

    body = "\n".join(sections)

    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family:sans-serif;max-width:700px;margin:0 auto;padding:20px;color:#111">
      <h1 style="border-bottom:2px solid #e5e7eb;padding-bottom:10px">
        SLC Deal Digest &mdash; {now_str}
      </h1>
      {body}
      <hr style="margin-top:30px;border:none;border-top:1px solid #e5e7eb">
      <p style="color:#9ca3af;font-size:12px">
        Wins: {len(wins)} &nbsp;·&nbsp;
        Entered: {len(entered)} &nbsp;·&nbsp;
        Manual: {len(manual)} &nbsp;·&nbsp;
        Deals shown: {len(top_deals)}
      </p>
    </body>
    </html>
    """
