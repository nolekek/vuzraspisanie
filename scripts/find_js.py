import re

with open('scripts/inspect_form4.py', 'r') as f: pass
import urllib.request, ssl
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
req = urllib.request.Request('https://uspu.ru/education/eios/schedule/', headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
    html = resp.read().decode('utf-8', errors='ignore')

# Search for any script matching group_name or rasp-row or ajax
scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.S)
print(f"Total scripts: {len(scripts)}")
for idx, s in enumerate(scripts):
    if 'group_name' in s or 'stud-r' in s or 'select' in s:
        print(f"\n=== Script {idx} ===")
        print(s[:1500])

# Also check linked script tags src
srcs = re.findall(r'<script[^>]*src=[\'"]([^\'"]*)[\'"]', html)
print("\nLinked scripts:")
for src in srcs:
    if 'rasp' in src.lower() or 'sched' in src.lower() or 'custom' in src.lower():
        print(" ", src)
