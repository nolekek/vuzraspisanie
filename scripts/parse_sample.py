import urllib.request, urllib.parse, ssl
from bs4 import BeautifulSoup

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = 'https://uspu.ru/ajax/rasp.php'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Referer': 'https://uspu.ru/education/eios/schedule/',
    'X-Requested-With': 'XMLHttpRequest',
}
data = urllib.parse.urlencode({'group_name': 'АИ-2431'}).encode('utf-8')
req = urllib.request.Request(url, data=data, headers=headers)
with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
    html = resp.read().decode('utf-8', errors='ignore')

soup = BeautifulSoup(html, 'html.parser')
days = soup.find_all('div', class_='rasp-item')
print(f"Total days found: {len(days)}")

for d in days[:3]:
    day_name = d.find('span', class_='rasp-day')
    week_day = d.find('div', class_='rasp-week')
    print(f"\n--- {day_name.text.strip() if day_name else ''} ({week_day.text.strip() if week_day else ''}) ---")
    paras = d.find_all('div', class_='rasp-para')
    for p in paras:
        time_span = p.find('span', class_='para-time')
        desc = p.find('div', class_='rasp-desc')
        time_text = time_span.text.strip() if time_span else ''
        text_lines = [l.strip() for l in desc.stripped_strings] if desc else []
        print(f"  [{time_text}] {text_lines}")
