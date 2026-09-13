#!/usr/bin/env python3
"""TEMPORARIO: agregados por dia e por campanha, direto da planilha."""
import csv, io, re, unicodedata, urllib.request
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo
META="1op35YxXrib70If3Ywo3iRHIZxdbLOYGxMkk3za1hVC0"; LEADS="11AzC3YayPbFx_jtKfHc566gwVAaR_2AtUnja_tdW4-s"
def get(sid,gid="0"):
    u=f"https://docs.google.com/spreadsheets/d/{sid}/export?format=csv&gid={gid}"
    r=urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0"})
    return list(csv.reader(io.StringIO(urllib.request.urlopen(r,timeout=120).read().decode("utf-8","replace"))))
def f(v):
    s=re.sub(r"[^\d,.-]","",str(v or "")); 
    if not s: return 0.0
    if "," in s and "." in s: s=s.replace(".","").replace(",",".")
    elif "," in s: s=s.replace(",",".")
    try: return float(s)
    except ValueError: return 0.0
def nrm(s):
    s="".join(c for c in unicodedata.normalize("NFKD",s or "") if not unicodedata.combining(c))
    return s.strip().lower()
SP=ZoneInfo("America/Sao_Paulo"); NO=ZoneInfo("America/Noronha")
def dlead(v):
    s=re.sub(r"\s+"," ",(v or "").strip())
    for fmt in ("%d/%m/%Y %H:%M:%S","%d/%m/%Y %H:%M","%d/%m/%Y"):
        try: return datetime.strptime(s,fmt).replace(tzinfo=SP).astimezone(NO).strftime("%Y-%m-%d")
        except ValueError: pass
    return None

m=get(META); l=get(LEADS)
print(f"META header: {m[0]}")
print(f"META linhas: {len(m)-1} · LEADS linhas: {len(l)-1}")
# meta por dia e por (dia,campanha)
dia=defaultdict(lambda:[0.0,0,0,0]); dc=defaultdict(lambda:[0.0,0,0,0])
for r in m[1:]:
    if not any(c.strip() for c in r): continue
    d,camp=r[0],r[1]
    for tgt in (dia[d], dc[(d,camp)]):
        tgt[0]+=f(r[7]); tgt[1]+=int(f(r[4])); tgt[2]+=int(f(r[5])); tgt[3]+=int(f(r[6]))
# leads por dia e por (dia,campanha)
ld=defaultdict(int); ldc=defaultdict(int)
for r in l[1:]:
    if not any(c.strip() for c in r): continue
    if nrm(r[4])!="meta-ads": continue
    if not nrm(r[5]).startswith("mtr-set26"): continue
    if not (r[1].strip() and r[2].strip() and r[3].strip()): continue
    d=dlead(r[0])
    if d: ld[d]+=1; ldc[(d,r[5])]+=1
TAX=1.13806
print("\n=== TOTAL POR DIA (todas as campanhas) — deve bater com a Visão Geral ===")
tot=[0.0,0,0,0,0]
for d in sorted(dia):
    a=dia[d]; tot=[tot[0]+a[0],tot[1]+a[1],tot[2]+a[2],tot[3]+a[3],tot[4]+ld[d]]
    print(f"  {d}: gasto R$ {a[0]*TAX:9.2f} · impr {a[1]:6d} · cliques {a[2]:4d} · visLP {a[3]:4d} · leads {ld[d]:3d}")
print(f"  TOTAL: gasto R$ {tot[0]*TAX:.2f} · impr {tot[1]} · cliques {tot[2]} · visLP {tot[3]} · leads {tot[4]}")
camps=sorted({c for _,c in dc})
print(f"\n=== POR CAMPANHA ({len(camps)}) ===")
for c in camps:
    print(f"\n  >>> {c}")
    t=[0.0,0,0,0,0]
    for d in sorted(dia):
        a=dc.get((d,c)); 
        if not a: continue
        n=ldc.get((d,c),0); t=[t[0]+a[0],t[1]+a[1],t[2]+a[2],t[3]+a[3],t[4]+n]
        print(f"      {d}: gasto R$ {a[0]*TAX:9.2f} · impr {a[1]:6d} · cliques {a[2]:4d} · visLP {a[3]:4d} · leads {n:3d}")
    print(f"      TOTAL: gasto R$ {t[0]*TAX:.2f} · impr {t[1]} · cliques {t[2]} · visLP {t[3]} · leads {t[4]}")
