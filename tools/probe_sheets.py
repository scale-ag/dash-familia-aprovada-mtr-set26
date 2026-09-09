#!/usr/bin/env python3
"""TEMPORARIO: descobre abas/gids/cabecalhos das planilhas do cliente (read-only)."""
import csv, io, json, re, urllib.request, urllib.error

SHEETS = {
    "META":  "1op35YxXrib70If3Ywo3iRHIZxdbLOYGxMkk3za1hVC0",
    "LEADS": "11AzC3YayPbFx_jtKfHc566gwVAaR_2AtUnja_tdW4-s",
}

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125 Safari/537.36"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.geturl(), r.read().decode("utf-8", errors="replace")

def try_get(url):
    try:
        return get(url)
    except Exception as e:
        return None, f"__ERRO__ {e!r}"

def discover(sid):
    gids = {}
    for path in (f"https://docs.google.com/spreadsheets/d/{sid}/htmlview",
                 f"https://docs.google.com/spreadsheets/d/{sid}/pubhtml",
                 f"https://docs.google.com/spreadsheets/d/{sid}/edit"):
        final, html = try_get(path)
        print(f"  [{path}] -> final={final} len={len(html)}")
        if html.startswith("__ERRO__"):
            print(f"    {html[:300]}")
            continue
        for pat in (r'id="sheet-button-(\d+)"[^>]*>(?:<a[^>]*>)?([^<]+)',
                    r'\{"name":"((?:[^"\\]|\\.)*)","id":"?(\d+)',
                    r'"(\d+)"\s*:\s*\{\s*"name"\s*:\s*"((?:[^"\\]|\\.)*)"'):
            for m in re.findall(pat, html):
                a, b = m
                gid, name = (a, b) if a.isdigit() else (b, a)
                if gid.isdigit():
                    gids.setdefault(gid, name)
        for gid in re.findall(r'[?&#]gid=(\d+)', html):
            gids.setdefault(gid, "?")
        if gids:
            print(f"    -> achou {gids}")
            break
        print(f"    HTML SAMPLE: {html[:600]!r}")
    return gids

def dump_csv(sid, gid, name):
    url = f"https://docs.google.com/spreadsheets/d/{sid}/export?format=csv"
    if gid is not None:
        url += f"&gid={gid}"
    final, txt = try_get(url)
    if txt.startswith("__ERRO__"):
        print(f"  -- gid={gid} ({name}) {txt[:200]}")
        return
    rows = list(csv.reader(io.StringIO(txt)))
    print("-" * 90)
    print(f"  == ABA '{name}' gid={gid} linhas={len(rows)}")
    for i, r in enumerate(rows[:3]):
        print(f"     [{i}] {r}")
    if not rows:
        return
    hdr = rows[0]
    print(f"     COLUNAS ({len(hdr)}): {list(enumerate(hdr))}")
    for ci, cname in enumerate(hdr):
        vals = {(r[ci].strip() if ci < len(r) else "") for r in rows[1:600]}
        vals.discard("")
        if 0 < len(vals) <= 15:
            print(f"     DISTINTOS col[{ci}] '{cname}': {sorted(vals)[:15]}")
    low = [c.strip().lower() for c in hdr]
    for key in ("campaign name", "campanha", "campaign", "nome da campanha"):
        if key in low:
            ci = low.index(key)
            camps = sorted({r[ci].strip() for r in rows[1:] if ci < len(r) and r[ci].strip()})
            print(f"     CAMPANHAS ({len(camps)}):")
            for c in camps[:80]:
                print(f"        · {c}")
            break

for label, sid in SHEETS.items():
    print("=" * 100)
    print(f"### {label}  id={sid}")
    found = discover(sid)
    print(f"ABAS ENCONTRADAS: {found}")
    if not found:
        print("  (fallback: export CSV da 1a aba, sem gid)")
        dump_csv(sid, None, "PRIMEIRA")
    for gid, name in found.items():
        dump_csv(sid, gid, name)
