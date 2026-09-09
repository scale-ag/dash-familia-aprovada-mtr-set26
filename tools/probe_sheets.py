#!/usr/bin/env python3
"""TEMPORARIO: descobre abas/gids/cabecalhos das planilhas do cliente (read-only)."""
import csv, io, re, urllib.request

SHEETS = {
    "META":  "1op35YxXrib70If3Ywo3iRHIZxdbLOYGxMkk3za1hVC0",
    "LEADS": "11AzC3YayPbFx_jtKfHc566gwVAaR_2AtUnja_tdW4-s",
}

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode("utf-8", errors="replace")

def tabs(sid):
    out = []
    try:
        html = get(f"https://docs.google.com/spreadsheets/d/{sid}/htmlview")
        out = re.findall(r'id="sheet-button-(\d+)"[^>]*>(?:<a[^>]*>)?([^<]+)', html)
    except Exception as e:
        print(f"  [htmlview falhou: {e!r}]")
    if not out:
        html = get(f"https://docs.google.com/spreadsheets/d/{sid}/edit")
        out = [(g, n) for n, g in re.findall(r'\{"name":"([^"]+)"[^}]*?"gid":"?(\d+)', html)]
        if not out:
            out = [(g, "?") for g in dict.fromkeys(re.findall(r'[?&#]gid=(\d+)', html))]
    return out

for label, sid in SHEETS.items():
    print("=" * 100)
    print(f"### {label}  id={sid}")
    found = tabs(sid)
    print(f"ABAS: {found}")
    for gid, name in found:
        url = f"https://docs.google.com/spreadsheets/d/{sid}/export?format=csv&gid={gid}"
        try:
            rows = list(csv.reader(io.StringIO(get(url))))
        except Exception as e:
            print(f"  -- gid={gid} ({name}) ERRO {e!r}")
            continue
        print("-" * 90)
        print(f"  -- ABA '{name}' gid={gid} linhas={len(rows)}")
        for i, r in enumerate(rows[:4]):
            print(f"     [{i}] {r}")
        if rows:
            hdr = rows[0]
            print(f"     COLUNAS ({len(hdr)}): {list(enumerate(hdr))}")
            # valores distintos das primeiras colunas curtas (ajuda a achar MQL / campanha)
            for ci, cname in enumerate(hdr):
                vals = {(r[ci].strip() if ci < len(r) else "") for r in rows[1:400]}
                vals.discard("")
                if 0 < len(vals) <= 12:
                    print(f"     DISTINTOS col[{ci}] '{cname}': {sorted(vals)[:12]}")
            low = [c.strip().lower() for c in hdr]
            for key in ("campaign name", "campanha", "campaign"):
                if key in low:
                    ci = low.index(key)
                    camps = sorted({r[ci].strip() for r in rows[1:] if ci < len(r) and r[ci].strip()})
                    print(f"     CAMPANHAS ({len(camps)}): {camps[:60]}")
                    break
