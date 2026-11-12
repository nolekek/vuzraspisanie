import re

with open('scripts/inspect_uspu.py', 'r') as f: pass
import urllib.request, ssl
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
req = urllib.request.Request('https://uspu.ru/education/eios/schedule/', headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
    html = resp.read().decode('utf-8', errors='ignore')

# Extract all group options
options = re.findall(r'<select[^>]*name=[\'"]group_name[\'"][^>]*>(.*?)</select>', html, re.S)
if options:
    groups = re.findall(r'<option[^>]*value=[\'"]([^\'"]*)[\'"][^>]*>(.*?)</option>', options[0])
    print(f"Total groups: {len(groups)}")
    # Print some 2024/2025/2026 groups
    recent_groups = [g[0] for g in groups if any(yr in g[0] for yr in ['23', '24', '25', '26'])]
    print(f"Recent groups (23-26): {len(recent_groups)}")
    print("Sample:", recent_groups[:20])
