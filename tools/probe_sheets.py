#!/usr/bin/env python3
"""TEMPORARIO: audita 13/09 da campanha 'Escala horizontal', por conjunto."""
import csv, io, re, unicodedata, urllib.request
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo
META="1op35YxXrib70If3Ywo3iRHIZxdbLOYGxMkk3za1hVC0"; LEADS="11AzC3YayPbFx_jtKfHc566gwVAaR_2AtUnja_tdW4-s"
DIA="2026-09-13"; ALVO="Escala horizontal"
def get(sid):
    u=f"https://docs.google.com/spreadsheets/d/{sid}/export?format=csv&gid=0"
    r=urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0"})
    return list(csv.reader(io.StringIO(urllib.request.urlopen(r,timeout=120).read().decode("utf-8","replace"))))
def f(v):
    s=re.sub(r"[^\d,.-]","",str(v or ""))
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
TAX=1.13806
m=get(META); l=get(LEADS)
camps=sorted({r[1] for r in m[1:] if any(c.strip() for c in r)})
alvo=[c for c in camps if ALVO in c]
print(f"campanhas na planilha: {len(camps)} · alvo encontrado: {alvo}")
CAMP=alvo[0]
# mídia do dia, por conjunto
mid=defaultdict(lambda:[0.0,0,0,0])
for r in m[1:]:
    if not any(c.strip() for c in r): continue
    if r[0]!=DIA or r[1]!=CAMP: continue
    a=mid[r[2]]; a[0]+=f(r[7]); a[1]+=int(f(r[4])); a[2]+=int(f(r[5])); a[3]+=int(f(r[6]))
# leads do dia, por conjunto (utm_medium)
lid=defaultdict(int); desc=defaultdict(int)
for r in l[1:]:
    if not any(c.strip() for c in r): continue
    if dlead(r[0])!=DIA: continue
    if r[5]!=CAMP:
        if nrm(r[5]).startswith("mtr-set26"): desc["outra campanha"]+=1
        continue
    if nrm(r[4])!="meta-ads": desc["sem meta-ads"]+=1; continue
    if not (r[1].strip() and r[2].strip() and r[3].strip()): desc["incompleto"]+=1; continue
    lid[r[6]]+=1
print(f"\n=== {DIA} · {CAMP}")
print(f"{'CONJUNTO':<46}{'GASTO c/imp':>12}{'GASTO s/imp':>12}{'IMPR':>7}{'CLQ':>5}{'VisLP':>7}{'LEADS':>7}{'CPL c/imp':>11}{'CPL s/imp':>11}")
T=[0.0,0,0,0,0]
for cj in sorted(set(mid)|set(lid)):
    a=mid.get(cj,[0.0,0,0,0]); n=lid.get(cj,0)
    T=[T[0]+a[0],T[1]+a[1],T[2]+a[2],T[3]+a[3],T[4]+n]
    cpl_c=f"{a[0]*TAX/n:.2f}" if n else "-"; cpl_s=f"{a[0]/n:.2f}" if n else "-"
    print(f"{cj[-44:]:<46}{a[0]*TAX:>12.2f}{a[0]:>12.2f}{a[1]:>7}{a[2]:>5}{a[3]:>7}{n:>7}{cpl_c:>11}{cpl_s:>11}")
cpl_c=f"{T[0]*TAX/T[4]:.2f}" if T[4] else "-"; cpl_s=f"{T[0]/T[4]:.2f}" if T[4] else "-"
print(f"{'TOTAL':<46}{T[0]*TAX:>12.2f}{T[0]:>12.2f}{T[1]:>7}{T[2]:>5}{T[3]:>7}{T[4]:>7}{cpl_c:>11}{cpl_s:>11}")
print(f"\nleads do dia descartados por outro motivo: {dict(desc)}")
# leads desta campanha em OUTROS dias (p/ ver deslocamento de atribuição)
viz=defaultdict(int)
for r in l[1:]:
    if not any(c.strip() for c in r): continue
    if r[5]!=CAMP or nrm(r[4])!="meta-ads": continue
    d=dlead(r[0])
    if d: viz[d]+=1
print(f"leads desta campanha por dia (planilha): {dict(sorted(viz.items()))}")
