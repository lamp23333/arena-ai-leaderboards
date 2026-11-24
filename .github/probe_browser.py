from playwright.sync_api import sync_playwright

URL = "https://arena.ai/leaderboard/"

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(locale="en-US", viewport={"width": 1440, "height": 900})
    pg = ctx.new_page()
    resp = pg.goto(URL, wait_until="domcontentloaded", timeout=60000)
    print("STATUS:", resp.status if resp else None)
    pg.wait_for_timeout(7000)
    print("TITLE:", pg.title())
    body = pg.inner_text("body")
    print("BODY_HEAD:", body[:800].replace("\n", " | "))
    print("BODY_LEN:", len(body))
    links = pg.eval_on_selector_all("a", "els => els.map(e => e.href)")
    hits = sorted({h for h in links if "leaderboard" in h})
    print("LEADERBOARD_LINKS:", hits[:15])
    print("LINK_COUNT:", len(links))
    b.close()
