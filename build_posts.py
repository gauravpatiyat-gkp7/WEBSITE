#!/usr/bin/env python3
"""
Generate standalone, crawlable HTML pages for each blog post.
- Reads posts + CSS from index.html
- Writes /posts/{slug}/index.html  (real URL: https://codenull.in/posts/{slug}/)
- Each page: full per-post SEO head, self-canonical, Article JSON-LD, frame-ancestors
  clickjacking protection, and reuses the #postview styling for identical look.
- Updates sitemap.xml with every post URL
- Rewrites the homepage card links from #blog/{slug} -> /posts/{slug}/ and recomputes the CSP hash
Re-run this whenever posts change (it reads them straight from index.html).
"""
import re, json, html, hashlib, base64, os

ROOT = "/mnt/user-data/outputs"
SITE = "https://codenull.in"
BRAND = "CA Gaurav K Patiyat"   # top-bar brand (update here after the {CODE.NULL} rebrand)
TODAY = "2026-06-25"

src = open(f"{ROOT}/index.html", encoding="utf-8").read()

# --- extract the full <style> block (reused verbatim for identical styling) ---
CSS = re.search(r"<style>(.*?)</style>", src, re.S).group(1)

# --- extract posts JSON ---
posts = json.loads(re.search(r'<script type="application/json" id="posts">(.*?)</script>', src, re.S).group(1))

# --- defaults from the head ---
DEFAULT_DESC = re.search(r'<meta name="description" content="([^"]*)"', src).group(1)
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
         '<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&'
         'family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">')

SECTION = {"vibe": ("series", "Vibe Coding"),
           "business": ("business", "Business Solutions"),
           "investing": ("investing", "Investing")}

# small inline script: makes the "Copy" button work without external JS (whitelisted by hash)
COPY_JS = ("document.querySelectorAll('.copy-btn').forEach(function(b){"
           "b.addEventListener('click',function(){"
           "var p=b.closest('.prompt-box').querySelector('.prompt');"
           "navigator.clipboard.writeText(p.innerText).then(function(){"
           "b.textContent='Copied';b.classList.add('done');"
           "setTimeout(function(){b.textContent='Copy';b.classList.remove('done');},2000);});});});")
COPY_HASH = "sha256-" + base64.b64encode(hashlib.sha256(COPY_JS.encode()).digest()).decode()

# extra CSS for the standalone top bar (not present in the main stylesheet)
EXTRA_CSS = ("""
  .site-bar{border-bottom:1px solid var(--line);background:#fff;position:sticky;top:0;z-index:10}
  .site-bar .wrap{max-width:900px;display:flex;align-items:center;justify-content:space-between;height:60px}
  .site-bar .brand{font-family:var(--display);font-weight:600;color:var(--ink);font-size:1.02rem;display:flex;align-items:center;gap:8px}
  .site-bar .brand .bm{font-family:var(--mono);color:var(--teal);font-weight:500}
  .site-bar .brand:hover{color:var(--teal)}
""")

def meta_desc(p):
    raw = p.get("seoDesc") or p["dek"]
    txt = html.unescape(re.sub(r"<[^>]+>", "", raw))
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt[:157].rstrip() + ("..." if len(txt) > 157 else "")

def page(p):
    slug = p["slug"]
    url = f"{SITE}/posts/{slug}/"
    section, label = SECTION.get(p["category"], ("series", "Vibe Coding"))
    title_txt = p.get("seoTitle") or f"{p['title']} \u2014 {BRAND}"
    desc = meta_desc(p)
    img = f"{SITE}/og-cover.jpg"

    t = html.escape(title_txt, quote=True)
    d = html.escape(desc, quote=True)

    jsonld = json.dumps({
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "headline": p["title"],
        "description": desc,
        "image": img,
        "url": url,
        "inLanguage": "en",
        "author": {"@type": "Person", "name": BRAND, "url": f"{SITE}/"},
        "publisher": {"@type": "Person", "name": BRAND}
    }, ensure_ascii=False, indent=2)

    # body: re-anchor in-page hash links to the homepage
    body = p["body"].replace('href="#', f'href="{SITE}/#')

    date_html = ""
    if p.get("date"):
        date_html = f'<span class="sep"></span><span>{html.escape(p["date"])}</span>'

    head = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; base-uri 'self'; object-src 'none'; img-src 'self' data:; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; script-src '{COPY_HASH}'; connect-src 'self'; form-action 'none'; frame-ancestors 'none'; upgrade-insecure-requests">
<meta name="referrer" content="strict-origin-when-cross-origin">
<title>{t}</title>
<meta name="description" content="{d}" />
<meta name="author" content="{html.escape(BRAND)}" />
<meta name="robots" content="index, follow, max-image-preview:large" />
<link rel="canonical" href="{url}" />
<meta property="og:site_name" content="{html.escape(BRAND)}" />
<meta property="og:type" content="article" />
<meta property="og:title" content="{t}" />
<meta property="og:description" content="{d}" />
<meta property="og:url" content="{url}" />
<meta property="og:image" content="{img}" />
<meta property="og:image:width" content="1200" />
<meta property="og:image:height" content="630" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="{t}" />
<meta name="twitter:description" content="{d}" />
<meta name="twitter:image" content="{img}" />
<script type="application/ld+json">
{jsonld}
</script>
{FONTS}
<style>{CSS}{EXTRA_CSS}</style>
</head>
<body>
<header class="site-bar"><div class="wrap"><a class="brand" href="{SITE}/"><span class="bm">//</span> {html.escape(BRAND)}</a></div></header>
<main id="postview" class="show">
  <div class="wrap">
    <a class="crumb" href="{SITE}/#{section}">{label}</a>
    <header class="post">
      <span class="eyebrow">{html.escape(p.get('tag',''))}</span>
      <h1>{p['title']}</h1>
      <p class="dek">{p['dek']}</p>
      <div class="meta"><span>{html.escape(p.get('read',''))}</span>{date_html}</div>
    </header>
    <article>{body}</article>
  </div>
</main>
<footer><div class="wrap"><p class="mono">// built from scratch &mdash; without writing a single line of code</p><p style="margin-top:6px">&copy; 2026 {html.escape(BRAND)} &middot; Bengaluru</p></div></footer>
<script>{COPY_JS}</script>
</body>
</html>"""
    return head

# --- write post pages ---
written = []
for p in posts:
    d = f"{ROOT}/posts/{p['slug']}"
    os.makedirs(d, exist_ok=True)
    open(f"{d}/index.html", "w", encoding="utf-8").write(page(p))
    written.append((p["slug"], len(page(p))))

# --- sitemap.xml ---
urls = [(f"{SITE}/", "weekly", "1.0")]
for p in posts:
    urls.append((f"{SITE}/posts/{p['slug']}/", "monthly", "0.8"))
sm = ['<?xml version="1.0" encoding="UTF-8"?>',
      '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for loc, cf, pr in urls:
    sm += ["  <url>", f"    <loc>{loc}</loc>", f"    <lastmod>{TODAY}</lastmod>",
           f"    <changefreq>{cf}</changefreq>", f"    <priority>{pr}</priority>", "  </url>"]
sm.append("</urlset>")
open(f"{ROOT}/sitemap.xml", "w", encoding="utf-8").write("\n".join(sm) + "\n")

# --- rewire homepage cards: #blog/{slug} -> /posts/{slug}/ , then recompute CSP hash ---
old_card = "href=\"#blog/'+p.slug+'\""
new_card = "href=\"/posts/'+p.slug+'/\""
assert src.count(old_card) == 1, f"expected 1 card link, found {src.count(old_card)}"
src2 = src.replace(old_card, new_card)

exec_script = re.findall(r"<script>(.*?)</script>", src2, re.S)[-1]
new_hash = "sha256-" + base64.b64encode(hashlib.sha256(exec_script.encode()).digest()).decode()
old_hash = re.search(r"script-src '(sha256-[^']+)'", src2).group(1)
src2 = src2.replace(old_hash, new_hash)
open(f"{ROOT}/index.html", "w", encoding="utf-8").write(src2)

print("=== post pages ===")
for s, n in written:
    print(f"  /posts/{s}/index.html  ({n//1024} KB)")
print("copy-script hash:", COPY_HASH)
print("homepage card link -> /posts/{slug}/  (1 replaced)")
print("old CSP hash:", old_hash)
print("new CSP hash:", new_hash)
print("sitemap urls:", len(urls))
