#!/usr/bin/env python3
"""TEMPORARIO: inspeciona as ABAS e COLUNAS atuais das planilhas do cliente."""
import csv, io, re, urllib.request
S = {"META":  "1op35YxXrib70If3Ywo3iRHIZxdbLOYGxMkk3za1hVC0",
     "LEADS": "11AzC3YayPbFx_jtKfHc566gwVAaR_2AtUnja_tdW4-s"}
def get(u):
    r = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(r, timeout=120).read().decode("utf-8", "replace")
for label, sid in S.items():
    print("="*90); print(f"### {label}")
    html = get(f"https://docs.google.com/spreadsheets/d/{sid}/htmlview")
    gids = list(dict.fromkeys(re.findall(r'[?&#]gid=(\d+)', html)))
    print(f"ABAS (gids): {gids}")
    for gid in gids:
        rows = list(csv.reader(io.StringIO(get(
            f"https://docs.google.com/spreadsheets/d/{sid}/export?format=csv&gid={gid}"))))
        if not rows: continue
        print(f"\n  -- gid={gid} · {len(rows)-1} linhas de dados")
        print(f"     COLUNAS ({len(rows[0])}): {list(enumerate(rows[0]))}")
        for i, r in enumerate(rows[1:3], 1):
            print(f"     [{i}] {r}")
        for ci, cn in enumerate(rows[0]):
            vals = {(r[ci].strip() if ci < len(r) else "") for r in rows[1:400]}
            vals.discard("")
            if 0 < len(vals) <= 10:
                print(f"     DISTINTOS col[{ci}] {cn!r}: {sorted(vals)}")
