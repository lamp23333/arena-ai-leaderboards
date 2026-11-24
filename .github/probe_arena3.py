import re
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"}


def get(u, t=30):
    req = urllib.request.Request(u, headers=UA)
    return urllib.request.urlopen(req, timeout=t).read().decode("utf-8", "replace")


robots = get("https://arena.ai/robots.txt")
print("ROBOTS_BYTES", len(robots))
for line in robots.splitlines():
    s = line.strip()
    if "leaderboard" in s or s.startswith(("Sitemap", "Disallow", "Crawl")):
        print("  R", s)

sm = get("https://arena.ai/sitemap.xml")
print("SITEMAP_BYTES", len(sm))
locs = re.findall(r"<loc>(.*?)</loc>", sm)
lastmods = re.findall(r"<lastmod>(.*?)</lastmod>", sm)
print("URLS", len(locs), "LASTMODS", len(lastmods))
if lastmods:
    print("NEWEST", max(lastmods), "OLDEST", min(lastmods))
lb = [u for u in locs if "leaderboard" in u]
print("LB_URLS", len(lb))
for u in lb[:14]:
    print("  U", u)

for u in ["https://arena.ai/nextjs-api/leaderboard",
          "https://arena.ai/nextjs-api/leaderboards",
          "https://arena.ai/nextjs-api/leaderboard/chat/text",
          "https://arena.ai/nextjs-api/leaderboard?name=text"]:
    try:
        body = get(u, 20)
        print("API", u, "OK", len(body), body[:120].replace(chr(10), " "))
    except Exception as e:
        print("API", u, "ERR", type(e).__name__, str(e)[:90])
