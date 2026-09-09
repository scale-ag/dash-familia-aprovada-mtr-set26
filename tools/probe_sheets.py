#!/usr/bin/env python3
"""TEMPORARIO: despeja os CSVs completos para teste local do build."""
import base64, urllib.request
S = {"meta": ("1op35YxXrib70If3Ywo3iRHIZxdbLOYGxMkk3za1hVC0", "0"),
     "leads": ("11AzC3YayPbFx_jtKfHc566gwVAaR_2AtUnja_tdW4-s", "0")}
for label, (sid, gid) in S.items():
    url = f"https://docs.google.com/spreadsheets/d/{sid}/export?format=csv&gid={gid}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    raw = urllib.request.urlopen(req, timeout=120).read()
    b64 = base64.b64encode(raw).decode()
    print(f"@@BEGIN {label} bytes={len(raw)}@@")
    for i in range(0, len(b64), 500):
        print("@@" + b64[i:i+500])
    print(f"@@END {label}@@")
