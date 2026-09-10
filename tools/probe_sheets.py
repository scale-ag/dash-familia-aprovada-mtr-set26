#!/usr/bin/env python3
"""TEMPORARIO: o que a planilha do Meta tem HOJE, por campanha e por dia."""
import csv, io, urllib.request
from collections import defaultdict
SID = "1op35YxXrib70If3Ywo3iRHIZxdbLOYGxMkk3za1hVC0"
def get(u):
    r = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(r, timeout=120).read().decode("utf-8", "replace")
rows = list(csv.reader(io.StringIO(get(
    f"https://docs.google.com/spreadsheets/d/{SID}/export?format=csv&gid=0"))))
print(f"COLUNAS ({len(rows[0])}): {rows[0]}")
print(f"LINHAS DE DADOS: {len(rows)-1}")
def f(v):
    s = (v or "").replace(".", "").replace(",", ".")
    try: return float(s)
    except ValueError: return 0.0
por = defaultdict(lambda: defaultdict(lambda: [0, 0.0]))   # campanha -> dia -> [linhas, gasto]
for r in rows[1:]:
    if not any(c.strip() for c in r): continue
    a = por[r[1]][r[0]]
    a[0] += 1; a[1] += f(r[7])
print("\n=== GASTO POR CAMPANHA E DIA (como está na planilha) ===")
for camp in sorted(por):
    tot = sum(v[1] for v in por[camp].values())
    print(f"\n  {camp}")
    for dia in sorted(por[camp]):
        n, g = por[camp][dia]
        print(f"     {dia}: {n:2d} linha(s) · R$ {g:8.2f}")
    print(f"     TOTAL: R$ {tot:.2f}")
print("\n=== ÚLTIMO DIA PRESENTE NA PLANILHA ===")
dias = sorted({r[0] for r in rows[1:] if any(c.strip() for c in r)})
print(f"  {dias}")
print("\n=== CONJUNTOS DA CAMPANHA MAIS NOVA (se houver) ===")
novos = [c for c in por if "P3-MISTO" in c or "Top ads" in c]
for c in novos:
    sets = sorted({r[2] for r in rows[1:] if len(r) > 2 and r[1] == c})
    print(f"  {c}\n     conjuntos: {sets}")
