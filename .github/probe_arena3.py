import re, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"}

def get(u, t=30):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=t).read().decode("utf-8", "replace")

robots = get("https://arena.ai/robots.txt")
print("ROBOTS bytes:", len(robots))
lbs = [l.strip() for l in robots.splitlines() if "leaderboard" in l]
print("LB_RULES:", len(lbs))
for l in lbs:
    print("   ", l)
other = [l.strip() for l in robots.splitlines() if l.strip().startswith(("Sitemap", "Disallow", "Crawl"))]
print("OTHER:", len(other))
for l in other[:15]:
    print("   ", l)

sm = get("https://arena.ai/sitemap.xml")
print("SITEMAP bytes:", len(sm))
locs = re.findall(r"<loc>(.*?)</loc>", sm)
lastmods = re.findall(r"<lastmod>(.*?)</lastmod>", sm)
print("URLS:", len(locs), "LASTMODS:", len(lastmods))
if lastmods:
    print("NEWEST_LASTMOD:", max(lastmods), "OLDEST:", min(lastmods))
lb = [u for u in locs if "leaderboard" in u]
print("LB_URLS:", len(lb))
for u in lb[:14]:
    print("   ", u)
pairs = re.findall(r"<url>\s*<loc>(.*?)</loc>\s*(?:<lastmod>(.*?)</lastmod>)?", sm)
lbp = [(u, m) for u, m in pairs if "leaderboard" in u]
print("LB_PAIRS:", len(lbp))
for u, m in lbp[:8]:
    print("   ", m or "-", u)
