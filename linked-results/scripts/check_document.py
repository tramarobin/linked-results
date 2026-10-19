#!/usr/bin/env python3
"""Check a results document in a headless browser (Edge or Chrome), and optionally take a screenshot.

    python check_document.py "<page.html>" [--width 1600] [--height 1000] [--dark] [--dpr 1.25]
                             [--shot out.png] [--tab G,T] [--full]

The checks, on every tab of the Results:
  - every linked statistic of the texts, every value and p of the tables and every row of the statistics
    panel marks its counterparts when hovered (the same statistic in the table, the statistics panel and
    the figure); the bad* lists name the ones that do not;
  - a click pins, Esc releases, a click on nothing releases;
  - hovering moves nothing: every element of the tab keeps its box to 0.01 px (shifts);
  - the methods: the participants' statistics, table rows and figure mark each other; every citation opens
    its reference and marks its entry, and closes again;
  - the enlarged figure opens and closes;
  - no exception, console error, "NaN", "undefined", "Infinity" or "null" in the page.
It prints one JSON report and exits with 1 when a check fails. --tab G,T picks the tab of the screenshot
(group G, tab T, from 0; G = -1: the methods). Set CHROME to a browser executable to choose one.
Standard library only: the browser is driven through its DevTools protocol over a small WebSocket client.
"""
import argparse
import base64
import json
import os
import random
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

BROWSERS = [
    os.environ.get('CHROME'),
    r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
    r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
    r'C:\Program Files\Google\Chrome\Application\chrome.exe',
    r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
    '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser', '/usr/bin/microsoft-edge',
]


class WS:
    """A minimal WebSocket client (RFC 6455): text frames, masked as a client must, fragments joined."""

    def __init__(self, url):
        host, rest = url.split('://', 1)[1].split('/', 1)
        h, p = host.split(':')
        self.s = socket.create_connection((h, int(p)), timeout=120)
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall((f'GET /{rest} HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n'
                        f'Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n').encode())
        buf = b''
        while b'\r\n\r\n' not in buf:
            buf += self.s.recv(4096)
        head, self.buf = buf.split(b'\r\n\r\n', 1)
        if b' 101 ' not in head.split(b'\r\n')[0]:
            raise RuntimeError('WebSocket handshake refused: ' + head.decode(errors='replace'))

    def send(self, text):
        data = text.encode()
        n = len(data)
        hdr = bytes([0x81]) + (bytes([0x80 | n]) if n < 126 else
                               bytes([0x80 | 126]) + struct.pack('>H', n) if n < 65536 else
                               bytes([0x80 | 127]) + struct.pack('>Q', n))
        mask = os.urandom(4)
        self.s.sendall(hdr + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def _read(self, n):
        while len(self.buf) < n:
            chunk = self.s.recv(1 << 20)
            if not chunk:
                raise ConnectionError('browser closed the connection')
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def recv(self):
        parts = []
        while True:
            b0, b1 = self._read(2)
            op, n = b0 & 0x0F, b1 & 0x7F
            if n == 126:
                n = struct.unpack('>H', self._read(2))[0]
            elif n == 127:
                n = struct.unpack('>Q', self._read(8))[0]
            mask = self._read(4) if b1 & 0x80 else None
            data = self._read(n)
            if mask:
                data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
            if op == 9:                                     # ping: answer it
                self.s.sendall(bytes([0x8A, 0x80]) + os.urandom(4))
                continue
            if op == 8:
                raise ConnectionError('browser closed the WebSocket')
            parts.append(data)
            if b0 & 0x80:
                return b''.join(parts).decode()

    def close(self):
        try:
            self.s.close()
        except OSError:
            pass


class Browser:
    def __init__(self, width, height, dpr=1.0, dark=False):
        exe = next((b for b in BROWSERS if b and Path(b).exists()), None)
        if not exe:
            sys.exit('No Edge or Chrome found; set CHROME to the browser executable.')
        self.port = random.randint(9300, 9800)
        self.prof = tempfile.mkdtemp(prefix='srdcheck_')
        self.proc = subprocess.Popen([exe, '--headless=new', '--disable-gpu', f'--remote-debugging-port={self.port}',
                                      f'--user-data-dir={self.prof}', f'--window-size={width},{height}', 'about:blank'],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        page = None
        for _ in range(100):
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{self.port}/json/list', timeout=2) as r:
                    page = next((t for t in json.load(r) if t.get('type') == 'page'), None)
                if page:
                    break
            except OSError:
                pass
            time.sleep(0.2)
        if not page:
            self.quit()
            sys.exit('The browser did not start its DevTools endpoint.')
        self.ws = WS(page['webSocketDebuggerUrl'])
        self.id = 0
        self.logs = []
        self.call('Runtime.enable')
        self.call('Page.enable')
        self.call('Emulation.setDeviceMetricsOverride', width=width, height=height, deviceScaleFactor=dpr, mobile=False)
        if dark:
            self.call('Emulation.setEmulatedMedia', features=[{'name': 'prefers-color-scheme', 'value': 'dark'}])

    def call(self, method, **params):
        self.id += 1
        me = self.id
        self.ws.send(json.dumps({'id': me, 'method': method, 'params': params}))
        while True:
            d = json.loads(self.ws.recv())
            if d.get('method') == 'Runtime.exceptionThrown':
                self.logs.append('exception: ' + json.dumps(d['params']['exceptionDetails'])[:600])
            elif d.get('method') == 'Runtime.consoleAPICalled' and d['params'].get('type') in ('error', 'warning'):
                self.logs.append(d['params']['type'] + ': ' + ' '.join(str(a.get('value', '')) for a in d['params']['args']))
            if d.get('id') == me:
                return d.get('result', {})

    def eval(self, expr, wait=True):
        r = self.call('Runtime.evaluate', expression=expr, returnByValue=True, awaitPromise=wait)
        if 'exceptionDetails' in r:
            raise RuntimeError(json.dumps(r['exceptionDetails'])[:1500])
        return r.get('result', {}).get('value')

    def quit(self):
        try:
            self.ws.close()
        except AttributeError:
            pass
        self.proc.kill()
        time.sleep(1.0)                                     # the browser lets go of its profile after it exits
        shutil.rmtree(self.prof, ignore_errors=True)


# the checks, run inside the page (they call the page's own render, showRow and state)
TEST = r"""(async () => {
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const over = el => el.dispatchEvent(new PointerEvent('pointerover', { bubbles: true }));
  const out = el => el.dispatchEvent(new PointerEvent('pointerout', { bubbles: true, relatedTarget: document.body }));
  const boxes = () => [...document.querySelectorAll('#content *, #panelBody *')].map(e => { const r = e.getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; });
  const same = (a, b) => a.length === b.length && a.every((r, i) => r.every((v, j) => Math.abs(v - b[i][j]) < 0.01));
  const rep = { tabs: 0, spans: 0, cells: 0, statRows: 0, badSpans: [], badCells: [], badRows: [], shifts: [], pins: [], cites: [], dialog: null, text: [] };
  const marked = () => ({ fig: document.querySelectorAll('#panelBody [data-ks].hov').length,
                          table: document.querySelectorAll('#content td.hov, #content .ref.hov').length,
                          stats: document.querySelectorAll('#panelBody tr.hov').length });
  for (let g = 0; g < DATA.groups.length; g++) for (let t = 0; t < DATA.groups[g].tabs.length; t++) {
    nav = { top: 'results', g, t }; render(); await wait(60);
    rep.tabs++;
    const where = DATA.groups[g].label + ' / ' + DATA.groups[g].tabs[t].label;
    for (const sp of [...document.querySelectorAll('#content .ref')]) {
      rep.spans++;
      over(sp); await wait(5);
      const m = marked(), base = boxes();
      if (!sp.classList.contains('hov') || !m.fig || !(m.stats + m.table > 1)) rep.badSpans.push(where + ': ' + sp.dataset.k + ' ' + JSON.stringify(m));
      out(sp);
      if (!same(base, boxes())) rep.shifts.push(where + ': span ' + sp.dataset.k);
    }
    for (const td of [...document.querySelectorAll('#content td.k')]) {
      rep.cells++;
      showRow(td.dataset.row); await wait(5);               // a row of its own shows its figure: that is not a shift
      const b0 = boxes();
      over(td); await wait(5);
      const m = marked();
      if (!td.classList.contains('hov') || !m.fig || !m.stats) rep.badCells.push(where + ': ' + td.dataset.row + ' ' + td.dataset.k + ' ' + JSON.stringify(m));
      out(td);
      if (!same(b0, boxes())) rep.shifts.push(where + ': cell ' + td.dataset.k);
    }
    for (const rid of DATA.groups[g].tabs[t].rows) {
      showRow(rid); await wait(20);
      for (const tr of [...document.querySelectorAll('#panelBody tr[data-k]')]) {
        rep.statRows++;
        const b0 = boxes();
        over(tr); await wait(5);
        const m = marked();
        if (!tr.classList.contains('hov') || !m.fig) rep.badRows.push(where + ': ' + rid + ' ' + tr.dataset.k + ' ' + JSON.stringify(m));
        out(tr);
        if (!same(b0, boxes())) rep.shifts.push(where + ': stats row ' + tr.dataset.k);
      }
    }
    const sp = document.querySelector('#content .ref');
    if (sp) {
      const click = el => { el.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true })); el.click(); };
      click(sp); const a = !!pin && sp.classList.contains('pinned');
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true })); const b = !pin;
      click(sp); const c = !!pin;
      click(document.querySelector('footer')); const d = !pin;
      if (!(a && b && c && d)) rep.pins.push(where + ': ' + JSON.stringify({ pinned: a, esc: b, again: c, released: d }));
    }
  }
  // the methods: the participants' statistics, table and figure; every citation and its reference
  nav = { top: 'methods', g: 0, t: 0 }; render(); await wait(80);
  rep.methods = { spans: 0, rows: 0, cites: 0 };
  for (const sp of [...document.querySelectorAll('#content .ref')]) {
    rep.methods.spans++;
    over(sp); await wait(5);
    const fig = document.querySelectorAll('#content [data-ks].hov').length, tab = document.querySelectorAll('#content tr.hov, #content .ref.hov').length;
    // a statistic with a table row must mark it too; a count (sex) has no row, only its participants' crosses
    const row = !!document.querySelector(`#content tr[data-k="${sp.dataset.k}"]`);
    if (!sp.classList.contains('hov') || !fig || (row && tab < 2)) rep.badSpans.push('Methods: ' + sp.dataset.k + ' ' + JSON.stringify({ fig, tab }));
    out(sp);
  }
  for (const tr of [...document.querySelectorAll('#content .pblock tr[data-k]')]) {
    rep.methods.rows++;
    over(tr); await wait(5);
    if (!tr.classList.contains('hov') || !document.querySelectorAll('#content [data-ks].hov').length) rep.badRows.push('Methods: ' + tr.dataset.k);
    out(tr);
  }
  for (const c of [...document.querySelectorAll('#content .cite')]) {
    rep.methods.cites++;
    const key = c.dataset.cite, entry = document.querySelector(`.refentry[data-ref="${key}"]`);
    c.dispatchEvent(new PointerEvent('pointerover', { bubbles: true })); await wait(230);
    const shown = !pop.hidden && pop.textContent.includes(REFS[key].label[0].split(' ')[0]);
    const marked = !!entry && entry.classList.contains('chov');
    document.body.dispatchEvent(new PointerEvent('pointerover', { bubbles: true })); await wait(330);
    if (!shown || !marked || !pop.hidden) rep.cites.push(key + ' ' + JSON.stringify({ shown, marked, closed: pop.hidden }));
  }
  nav = { top: 'results', g: 0, t: 0 }; render(); await wait(50);
  document.querySelector('.grow').click(); await wait(50);
  const dlg = document.getElementById('big'), dsvg = dlg.querySelector('svg');
  rep.dialog = { open: dlg.open, svg: !!dsvg, width: Math.round(dsvg ? dsvg.getBoundingClientRect().width : 0) };
  dlg.close();
  nav = { top: 'methods', g: 0, t: 0 }; render(); await wait(30);
  const all = [document.body.innerText];
  for (let g = 0; g < DATA.groups.length; g++) for (let t = 0; t < DATA.groups[g].tabs.length; t++) {
    nav = { top: 'results', g, t }; render(); await wait(30);
    document.querySelectorAll('details').forEach(d => d.open = true);
    all.push(document.body.innerText, [...document.querySelectorAll('svg text')].map(x => x.textContent).join(' '));
  }
  const bad = all.join(' ').match(/\b(NaN|undefined|Infinity|null)\b/g);
  if (bad) rep.text = [...new Set(bad)];
  try { localStorage.clear(); } catch (e) {}
  return rep;
})()"""


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('page')
    ap.add_argument('--width', type=int, default=1600)
    ap.add_argument('--height', type=int, default=1000)
    ap.add_argument('--dpr', type=float, default=1.0)
    ap.add_argument('--dark', action='store_true')
    ap.add_argument('--shot')
    ap.add_argument('--tab', default='0,0')
    ap.add_argument('--full', action='store_true')
    ap.add_argument('--no-checks', action='store_true', help='only the screenshot')
    a = ap.parse_args()
    page = Path(a.page).resolve()
    if not page.exists():
        sys.exit(f'no such page: {page}')
    B = Browser(a.width, a.height, a.dpr, a.dark)
    rep = {}
    try:
        B.call('Page.navigate', url=page.as_uri())
        ready = False
        for _ in range(100):
            time.sleep(0.2)
            try:
                ready = B.eval("typeof DATA !== 'undefined' && document.readyState === 'complete' && "
                               "!!document.querySelector('#content > *')", wait=False) is True
            except RuntimeError:
                ready = False
            if ready:
                break
        if not ready:
            rep = {'ok': False, 'error': 'the page did not load or did not draw its first tab', 'console': B.logs}
        else:
            time.sleep(0.3)
            if not a.no_checks:
                try:
                    rep = B.eval(TEST)
                except RuntimeError as e:
                    rep = {'error': str(e)}
            if a.shot:
                g, t = (int(x) for x in a.tab.split(','))
                top = "'methods'" if g < 0 else "'results'"
                B.eval(f"nav = {{ top: {top}, g: {max(0, g)}, t: {t} }}; render(); window.scrollTo(0, 0); true")
                time.sleep(0.4)
                opts = {'format': 'png'}
                if a.full:
                    m = B.call('Page.getLayoutMetrics')
                    cs = m.get('cssContentSize') or m.get('contentSize')
                    opts['clip'] = {'x': 0, 'y': 0, 'width': a.width, 'height': min(cs['height'], 8000), 'scale': 1}
                    opts['captureBeyondViewport'] = True
                shot = B.call('Page.captureScreenshot', **opts)
                Path(a.shot).write_bytes(base64.b64decode(shot['data']))
                rep['shot'] = str(Path(a.shot).resolve())
            rep['console'] = B.logs
    finally:
        B.quit()
    if a.no_checks and 'error' not in rep:
        rep['ok'] = not rep.get('console')
    elif 'ok' not in rep:
        lists = ('badSpans', 'badCells', 'badRows', 'shifts', 'pins', 'cites', 'text', 'console')
        d = rep.get('dialog') or {}
        rep['ok'] = not rep.get('error') and not any(rep.get(k) for k in lists) and bool(d.get('open') and d.get('svg'))
    print(json.dumps(rep, indent=1, ensure_ascii=False))
    sys.exit(0 if rep['ok'] else 1)


if __name__ == '__main__':
    main()
