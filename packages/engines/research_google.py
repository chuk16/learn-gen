# packages/engines/research_google.py
# Google Custom Search JSON API wrapper with query templates & quality site hints

import json, os, html, re
from urllib.parse import urlencode
from urllib.request import Request, urlopen

UA = "learn-gen/0.1 (+https://example.com)"

def _http_get(url, timeout=15):
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="ignore")

def _strip_html(text: str) -> str:
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", text)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def _query_for(topic: str) -> list[str]:
    t = topic.lower()
    qs = [topic]
    # Lightweight heuristics to enrich the query
    if "spider" in t and "web" in t:
        qs.append(topic + " spider silk tensile strength toughness dragline study site:nih.gov OR site:nature.com OR site:sciencedirect.com")
    if "lightsaber" in t or "plasma" in t:
        qs.append(topic + " plasma physics confinement mean free path why light sabers impossible site:aps.org OR site:mit.edu OR site:wiki.phy")
    if "free throw" in t:
        qs.append(topic + " projectile arc angle 45 52 backspin swish probability site:scholar.google.com OR site:si.com")
    if "butter knife" in t or "serration" in t:
        qs.append(topic + " serrated vs straight knife butter crystallization spreadability temperature microstructure site:sciencedirect.com")
    return qs

def search_and_fetch(topic: str, max_results: int = 6):
    """Use Google CSE to find pages; fetch and clean them."""
    api_key = os.getenv("GOOGLE_CSE_API_KEY")
    cx = os.getenv("GOOGLE_CSE_ID")
    if not api_key or not cx:
        return []

    results = []
    seen = set()
    for qtext in _query_for(topic):
        q = urlencode({"key": api_key, "cx": cx, "q": qtext})
        url = f"https://www.googleapis.com/customsearch/v1?{q}"
        try:
            data = json.loads(_http_get(url))
        except Exception:
            continue
        for it in (data.get("items") or []):
            link = it.get("link")
            title = it.get("title") or link
            if not link or link in seen:
                continue
            seen.add(link)
            try:
                raw = _http_get(link, timeout=15)
                txt = _strip_html(raw)
                if len(txt) < 800:   # skip thin pages
                    continue
                results.append({"title": title, "url": link, "text": txt[:16000]})
                if len(results) >= max_results:
                    return results
            except Exception:
                continue
    return results
