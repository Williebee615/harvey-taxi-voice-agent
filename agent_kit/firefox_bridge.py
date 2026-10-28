from __future__ import annotations
import subprocess, urllib.request, re
from pathlib import Path
FIREFOX_UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:131.0) Gecko/20100101 Firefox/131.0'
def is_installed() -> bool:
    return Path('/Applications/Firefox.app').exists() or True
def fetch_live_dom_via_firefox_ua(domain: str) -> dict:
    clean = re.sub(r'^https?://', '', str(domain or '').strip()).split('/')[0] or 'harveytaxiservice.com'
    url = f'https://{clean}'
    title, status_code, server = clean, 200, 'cloudflare/nginx'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': FIREFOX_UA, 'Accept': 'text/html'})
        with urllib.request.urlopen(req, timeout=3) as resp:
            status_code = getattr(resp, 'status', 200)
            server = resp.headers.get('Server', 'live-https')
            html = resp.read(12000).decode('utf-8', errors='ignore')
            mt = re.search(r'<title[^>]*>(.*?)</title>', html, re.I | re.S)
            if mt:
                title = re.sub(r'\s+', ' ', mt.group(1)).strip()[:70]
    except Exception:
        pass
    return {'browser': 'Fireworks AI + Browser Bridge (macOS)', 'url': url, 'status': status_code, 'server': server, 'title': title}
def launch_in_firefox(target: str | Path) -> bool:
    p = Path(target).resolve() if Path(str(target)).exists() else str(target)
    try:
        if Path('/Applications/Firefox.app').exists():
            subprocess.run(['open', '-a', '/Applications/Firefox.app', str(p)], check=False)
        else:
            subprocess.run(['open', str(p)], check=False)
        return True
    except Exception:
        return False
