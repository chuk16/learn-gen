# packages/engines/research.py
# Web search gatherer: prefers Google CSE if keys are set; falls back to Wikipedia + optional URLs.

import os, re, json, html
from urllib.parse import quote
from urllib.request import Request, urlopen

UA = "learn-gen/0.1 (+https://example.com)"

def _http_get(url, timeout=12):
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="ignore")

def _strip_html(text):
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", text)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def wiki_search(topic, lang="en", max_chars=6000):
    q = quote(topic)
    try:
        search_json = _http_get(f"https://{lang}.wikipedia.org/w/api.php?action=query&list=search&format=json&srsearch={q}")
        data = json.loads(search_json)
        hits = data.get("query", {}).get("search", [])
        if not hits:
            return []
        title = hits[0]["title"]
        page_json = _http_get(f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote(title)}")
        p = json.loads(page_json)
        txt = " ".join([p.get("title",""), p.get("description","") or "", p.get("extract","")])
        url = (
            p.get("content_urls", {}).get("desktop", {}).get("page")
            or f"https://{lang}.wikipedia.org/wiki/{quote(title)}"
        )
        return [{"title": p.get("title","Wikipedia"), "url": url, "text": txt[:max_chars]}]
    except Exception:
        return []

def _chunk(text, size=900):
    words = text.split()
    out, buf, cur = [], [], 0
    for w in words:
        buf.append(w); cur += len(w) + 1
        if cur >= size:
            out.append(" ".join(buf)); buf=[]; cur=0
    if buf: out.append(" ".join(buf))
    return out

def gather(topic, extra_urls=None, use_google_if_available=True):
    """
    Returns:
      { "chunks":[{source_id,title,url,text,score}, ... up to ~8], "sources":[{id,title,url}, ...] }
    """
    sources = []

    # Prefer Google CSE if keys exist
    if use_google_if_available and os.getenv("GOOGLE_CSE_API_KEY") and os.getenv("GOOGLE_CSE_ID"):
        try:
            from . import research_google
            sources += research_google.search_and_fetch(topic, max_results=6)
        except Exception:
            pass

    # Fallback to Wikipedia if we got nothing from Google
    if not sources:
        sources += wiki_search(topic)

    # Add any user-provided URLs
    for u in (extra_urls or []):
        try:
            raw = _http_get(u)
            txt = _strip_html(raw)
            sources.append({"title": u, "url": u, "text": txt[:12000]})
        except Exception:
            pass

    # Simple scoring: length + keyword hits
    keys = [k for k in topic.lower().split() if len(k) > 2]
    def score(t):
        s = len(t)
        s += sum(5 for k in keys if k in t.lower())
        return s

    chunks = []
    for i, s in enumerate(sources, start=1):
        for j, c in enumerate(_chunk(s["text"], size=900), start=1):
            chunks.append({
                "source_id": f"S{i}",
                "title": s["title"],
                "url": s["url"],
                "text": c,
                "score": score(c)
            })

    chunks.sort(key=lambda x: x["score"], reverse=True)
    top = chunks[:8]

    uniq = {}
    for c in top:
        uniq.setdefault(c["source_id"], {"id": c["source_id"], "title": c["title"], "url": c["url"]})

    return {"chunks": top, "sources": list(uniq.values())}
