import requests, time
from datetime import datetime
import re
from xml.etree import ElementTree as ET

TELEGRAM_TOKEN = 'SEU_TOKEN'
TELEGRAM_CHAT_ID = 'SEU_CHAT_ID'
RSS_FEEDS = [
  'https://api.allorigins.win/raw?url=https://cointelegraph.com/rss',
  'https://api.allorigins.win/raw?url=https://livecoins.com.br/feed/'
] 
SLEEP_SECONDS = 3600
BUY_THRESHOLDS = {
    'mvrv': 0.1,
    'puell': 0.4,
    'nupl': 0.0,
    'sopr': None
}

def fetch_indicator(url, pattern):
    r = requests.get(url, timeout=10)
    text = r.text
    m = re.search(pattern, text)
    return float(m.group(1)) if m else None

def fetch_all():
    results = {}
    # MVRV – via Bitcoinition API
    resp = requests.get('https://bitcoinition.com/api/mvrv/zscore.json', timeout=10)
    results['mvrv'] = float(resp.json().get('zscore'))
    # Puell – scraping Bitbo
    puell = fetch_indicator('https://charts.bitbo.io/puell-multiple/', r'Puell Multiple.*?(\d+\.\d+)')
    results['puell'] = puell
    # NUPL – scraping Bitbo
    nupl = fetch_indicator('https://charts.bitbo.io/net-unrealized-profit-loss/', r'NUPL.*?(\d+\.\d+)')
    results['nupl'] = nupl
    # SOPR – tentativa similar
    sopr = fetch_indicator('https://charts.bitbo.io/', r'SOPR.*?(\d+\.\d+)')
    results['sopr'] = sopr
    return results

def fetch_news():
    items=[]
    for f in RSS_FEEDS:
        try:
            r = requests.get(f, timeout=10)
            txt = r.json().get('contents', r.text)
            root = ET.fromstring(txt)
            for itm in root.findall('.//item')[:3]:
                items.append((itm.find('title').text, itm.find('link').text))
        except:
            pass
    return items

def send_telegram(msg):
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    return requests.post(url, json={'chat_id': TELEGRAM_CHAT_ID, 'text':msg, 'parse_mode':'Markdown'}).ok

def main():
    last_signal = {}
    while True:
        inds = fetch_all()
        signals = []
        if inds['mvrv'] is not None and inds['mvrv'] <= BUY_THRESHOLDS['mvrv']:
            signals.append(f"MVRV Z‑Score baixo: {inds['mvrv']:.2f}")
        if inds['puell'] is not None and inds['puell'] <= BUY_THRESHOLDS['puell']:
            signals.append(f"Puell Multiple baixo: {inds['puell']:.2f}")
        if inds['nupl'] is not None and inds['nupl'] <= BUY_THRESHOLDS['nupl']:
            signals.append(f"NUPL <= 0: {inds['nupl']:.2f}")
        # SOPR não tem threshold definido
        if signals and signals != last_signal.get('signals'):
            news = fetch_news()
            msg = "*🔔 Possível zona de compra identificada*\n"
            msg += "\n".join(f"- {s}" for s in signals)
            msg += "\n\n*Últimas notícias:*"
            for t, l in news:
                msg += f"\n– [{t}]({l})"
            send_telegram(msg)
            last_signal['signals'] = signals
        time.sleep(SLEEP_SECONDS)

if __name__ == '__main__':
    main()
