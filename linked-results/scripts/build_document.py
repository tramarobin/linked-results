#!/usr/bin/env python3
"""Build a linked results document: one self-contained HTML file from data, a stats sheet and a study file.

    python build_document.py study.json [--out "Results.html"] [--check]

study.json   the study description (factors, outcomes, tabs, texts); see references/data-contract.md.
             Paths inside it are relative to its own folder.
--out        the page to write (default: "<title>.html" beside study.json).
--check      validate and print the texts without writing the page.

The statistics are never computed here: every p-value, F, t and threshold comes from the stats sheet.
Means, SDs, differences and relative differences are computed from the data; effect sizes are read
from the sheet, and computed only when the sheet has none (the page says so in its reading guide).
Every number in a generated text comes from the page's own data, and every cited statistic is a
linked span whose key is asserted to exist.
"""
import argparse
import csv
import html
import json
import math
import re
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

HERE = Path(__file__).resolve().parent
MINUS = '−'
TIMES = '×'


def fail(msg):
    sys.exit('build_document: ' + msg)


# ------------------------------------------------------------------ numbers, formatted as the page does
def fixed(x, d):
    """Number.prototype.toFixed: the exact binary value, ties away from zero; U+2212 for minus."""
    q = Decimal(float(x)).quantize(Decimal(1).scaleb(-d), rounding=ROUND_HALF_UP)
    s = format(q, 'f')
    if s.startswith('-'):
        s = s[1:] if float(q) == 0 else MINUS + s[1:]
    return s


def signed(x, d):
    s = fixed(x, d)
    return s if s.startswith(MINUS) or float(s) == 0 else '+' + s


def plab(p):
    return 'p < 0.001' if p < 0.001 else 'p = ' + fixed(p, 3)


def ph(p):
    """plab for HTML: the texts are HTML, so '<' is escaped."""
    return html.escape(plab(p), quote=False)


def with_unit(s, unit):
    if not unit:
        return s
    return s + unit if unit.startswith('%') else s + ' ' + unit


def natural(s):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)]


def num(s):
    s = (s or '').strip()
    if s == '' or s.upper() in ('NA', 'NAN', 'NULL'):
        return None
    try:
        v = float(s)
    except ValueError:
        return None
    return v if math.isfinite(v) else None


def mean(v):
    v = [x for x in v if x is not None]
    return sum(v) / len(v) if v else None


def sd(v):
    v = [x for x in v if x is not None]
    if len(v) < 2:
        return None
    m = sum(v) / len(v)
    return math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1))


def cap(s):
    return s[:1].upper() + s[1:] if s else s


def join_words(parts, last='and'):
    parts = [p for p in parts if p]
    if len(parts) < 2:
        return ''.join(parts)
    return ', '.join(parts[:-1]) + ' ' + last + ' ' + parts[-1]


# ------------------------------------------------------------------ the study file
def load_study(path):
    S = json.loads(Path(path).read_text(encoding='utf-8'))
    for k in ('title', 'data', 'stats', 'factors', 'outcomes', 'results'):
        if k not in S:
            fail(f'study.json has no "{k}"')
    if not 1 <= len(S['factors']) <= 2:
        fail('this builder handles one or two factors (see references/data-contract.md to extend it)')
    for F in S['factors']:
        for k in ('id', 'name', 'levels'):
            if k not in F:
                fail(f'a factor has no "{k}"')
        if len(F['levels']) < 2:
            fail(f'factor {F["id"]} needs at least two levels')
        F.setdefault('within', True)
        F.setdefault('noun', F['name'].lower())
        F.setdefault('plural', F['noun'] + 's')
        F.setdefault('reference', F['levels'][0]['code'])
        for L in F['levels']:
            L.setdefault('short', L['name'])
            L.setdefault('phrase', ('with ' if F['within'] else 'in the ') + L['name'].lower())
            L.setdefault('color', '#6b717a')
            L.setdefault('color_dark', L['color'])
        if F['reference'] not in [L['code'] for L in F['levels']]:
            fail(f'factor {F["id"]}: reference {F["reference"]} is not one of its levels')
    if S.get('split'):
        S['split'].setdefault('name', S['split']['id'])
        for L in S['split']['levels']:
            L.setdefault('long', L['name'])
    for O in S['outcomes']:
        for k in ('id', 'file', 'name'):
            if k not in O:
                fail(f'an outcome has no "{k}"')
        O.setdefault('noun', O['name'].lower())
        O.setdefault('unit', '')
        O.setdefault('dec', 2)
        O.setdefault('relative', True)
        O.setdefault('split', bool(S.get('split')))
        O.setdefault('fixed', {})
    S['stats'].setdefault('alpha', 0.05)
    return S


# ------------------------------------------------------------------ the data
def read_wide(path, id_col):
    with open(path, encoding='utf-8-sig', newline='') as f:
        rows = list(csv.reader(f))
    if len(rows) < 2:
        fail(f'{path} has no data rows')
    head = rows[0]
    ids = [r[id_col].strip() for r in rows[1:] if r and any(c.strip() for c in r)]
    cols = {}
    for j, h in enumerate(head):
        if j == id_col:
            continue
        cols[h.strip()] = [num(r[j]) if j < len(r) else None for r in rows[1:] if r and any(c.strip() for c in r)]
    if len(set(ids)) != len(ids):
        fail(f'{path}: duplicate participant IDs')
    return ids, cols


def read_participants(S, base):
    """Between-participant factors: a participants file with one row per participant (see the contract)."""
    P = S.get('participants')
    if not P:
        return {}
    with open(base / P['file'], encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    idc = P.get('id', 'id')
    out = {}
    for r in rows:
        out[r[idc].strip()] = {k: (v or '').strip() for k, v in r.items()}
    return out


# ------------------------------------------------------------------ the stats sheet
def term_id(s):
    s = (s or '').strip()
    s = re.sub(r'\s*(?:×|\*|:|\s[xX]\s)\s*', ':', s)
    return s.replace(' ', '')


def read_stats(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    need = {'outcome', 'split', 'test', 'effect', 'p'}
    miss = need - set(rows[0].keys() if rows else [])
    if miss:
        fail(f'{path}: missing columns {sorted(miss)}')
    for r in rows:
        r['effect'] = term_id(r['effect'])
        r['test'] = r['test'].strip().lower()
        r['split'] = (r.get('split') or '').strip()
        for k in ('value', 'df1', 'df2', 'threshold', 'p', 'p_own', 'g', 'diff', 'n', 'n_perm'):
            r[k] = num(r.get(k))
        r['at'] = {a.split('=')[0].strip(): a.split('=')[1].strip()
                   for a in (r.get('at') or '').split(';') if '=' in a}
    return rows


# ------------------------------------------------------------------ one analysed row: outcome x split
def build_rows(S, base):
    F = S['factors']
    fids = [f['id'] for f in F]
    pattern = S['data'].get('column_pattern', fids + ([S['split']['id']] if S.get('split') else []))
    sep = S['data'].get('separator', '.')
    id_col = S['data'].get('id_column', 0)
    ddir = base / S['data'].get('dir', '.')
    groups = read_participants(S, base)
    stats = read_stats(base / S['stats']['file'])
    alpha = S['stats']['alpha']

    terms = fids[:] + ([':'.join(fids)] if len(F) == 2 else [])
    lev = {f['id']: [L['code'] for L in f['levels']] for f in F}
    # the cells, in factor order (first factor fastest within the second, as a table reads)
    if len(F) == 1:
        cells = [{fids[0]: a} for a in lev[fids[0]]]
    else:
        cells = [{fids[0]: a, fids[1]: b} for b in lev[fids[1]] for a in lev[fids[0]]]
    code = lambda c: '|'.join(c[f] for f in fids)

    rows, ids_all = {}, None
    for O in S['outcomes']:
        ids, cols = read_wide(ddir / O['file'], id_col)
        if ids_all is None:
            ids_all = sorted(ids, key=natural)
        elif sorted(ids, key=natural) != ids_all:
            fail(f'{O["file"]}: not the same participants as the other files')
        order = [ids.index(i) for i in ids_all]
        parsed = {}
        for h, v in cols.items():
            tok = h.split(sep)
            if len(tok) != len(pattern):
                fail(f'{O["file"]}: column "{h}" does not match the pattern {sep.join(pattern)}')
            parsed[h] = (dict(zip(pattern, tok)), [v[k] for k in order])
        splits = [L['code'] for L in S['split']['levels']] if (S.get('split') and O['split']) else ['']
        for sp in splits:
            fixed_lv = dict(O['fixed'])
            if sp:
                fixed_lv[S['split']['id']] = sp
            values = {}
            for c in cells:
                want = dict(c)
                # a between factor is not in the columns: its level comes from the participants file
                within = {k: v for k, v in want.items() if next(f for f in F if f['id'] == k)['within']}
                hit = [h for h, (t, _) in parsed.items()
                       if all(t.get(k) == v for k, v in {**within, **fixed_lv}.items())]
                if len(hit) != 1:
                    fail(f'{O["file"]}: {len(hit)} columns for cell {code(c)} {fixed_lv} (need exactly 1)')
                v = list(parsed[hit[0]][1])
                for f in F:
                    if not f['within']:
                        col = f.get('column', f['id'])
                        v = [x if groups.get(pid, {}).get(col) == c[f['id']] else None for x, pid in zip(v, ids_all)]
                values[code(c)] = v
            # listwise: a participant missing a within cell of their group is left out of this row
            keep = []
            for i, pid in enumerate(ids_all):
                mine = [values[code(c)][i] for c in cells
                        if all(f['within'] or groups.get(pid, {}).get(f.get('column', f['id'])) == c[f['id']] for f in F)]
                keep.append(bool(mine) and all(x is not None for x in mine))
            for k in values:
                values[k] = [x if keep[i] else None for i, x in enumerate(values[k])]
            rid = O['id'] + ('|' + sp if sp else '')
            st = [r for r in stats if r['outcome'] == O['id'] and r['split'] == sp]
            if not st:
                fail(f'stats sheet: no rows for {O["id"]} {sp or "(no split)"}')
            rows[rid] = make_row(S, O, sp, rid, cells, code, values, st, terms, alpha, ids_all, groups)
    return rows, ids_all, stats, terms


def make_row(S, O, sp, rid, cells, code, values, st, terms, alpha, ids, groups):
    F = S['factors']
    fids = [f['id'] for f in F]
    lvname = {(f['id'], L['code']): L for f in F for L in f['levels']}
    n = sum(1 for i in range(len(ids)) if any(values[k][i] is not None for k in values))
    cell_rows = []
    for c in cells:
        v = values[code(c)]
        cell_rows.append({'code': code(c), 'lv': c, 'n': sum(x is not None for x in v), 'mean': mean(v), 'sd': sd(v)})
    cmean = {r['code']: r['mean'] for r in cell_rows}

    def emm(fixed_lv):
        """Estimated marginal mean: the unweighted mean of the cell means (as type III)."""
        ms = [cmean[code(c)] for c in cells if all(c[k] == v for k, v in fixed_lv.items())]
        return sum(ms) / len(ms)

    def part(fixed_lv):
        """Each participant's value at these levels: the mean over the cells they have."""
        cs = [code(c) for c in cells if all(c[k] == v for k, v in fixed_lv.items())]
        return [mean([values[k][i] for k in cs]) if any(values[k][i] is not None for k in cs) else None
                for i in range(len(ids))]

    levels = []
    if len(F) == 2:
        for f in F:
            for L in f['levels']:
                v = part({f['id']: L['code']})
                levels.append({'key': f'lv:{f["id"]}={L["code"]}', 'factor': f['id'], 'level': L['code'],
                               'values': v, 'n': sum(x is not None for x in v), 'mean': mean(v), 'sd': sd(v),
                               'emm': emm({f['id']: L['code']})})

    aov = []
    for t in terms:
        r = [x for x in st if x['test'] == 'anova' and x['effect'] == t]
        if len(r) != 1:
            fail(f'stats sheet: {rid}: {len(r)} ANOVA rows for {t} (need exactly 1)')
        r = r[0]
        aov.append({'key': 't:' + t, 'term': t, 'F': r['value'], 'df1': r['df1'], 'df2': r['df2'],
                    'thr': r['threshold'], 'p': r['p'], 'sig': r['p'] <= alpha})
    asig = {a['term']: a['sig'] for a in aov}

    comps, g_computed = [], False
    for r in [x for x in st if x['test'] == 'posthoc']:
        fac = r.get('factor') or r['effect']
        f = next((x for x in F if x['id'] == fac), None)
        if f is None:
            fail(f'stats sheet: {rid}: comparison of an unknown factor "{fac}"')
        a, b = r['level_a'].strip(), r['level_b'].strip()
        codes = [L['code'] for L in f['levels']]
        if a not in codes or b not in codes:
            fail(f'stats sheet: {rid}: levels {a}, {b} are not levels of {fac}')
        ref = f['reference'] if f['reference'] in (a, b) else (a if codes.index(a) < codes.index(b) else b)
        test = b if ref == a else a
        flip = 1 if test == a else -1                     # the sheet's a - b, turned into test - ref
        at = r['at']
        for k, v in at.items():
            if (k, v) not in lvname:
                fail(f'stats sheet: {rid}: unknown level {k}={v}')
        mt, mr = emm({fac: test, **at}), emm({fac: ref, **at})
        diff = mt - mr
        if r['diff'] is not None:
            stored = flip * r['diff']
            if abs(stored - diff) > 1e-6 * max(1.0, abs(diff)):
                fail(f'stats sheet: {rid}: {fac} {test} - {ref} {at}: the sheet\'s diff {stored:.6g} is not the '
                     f'difference of the data\'s means {diff:.6g}; are the levels or the sign convention swapped?')
        g = r['g']
        if g is None:
            g = hedges_g(part({fac: test, **at}), part({fac: ref, **at}), f['within'])
            g_computed = g_computed or g is not None
        g = None if g is None else math.copysign(abs(g), diff)
        term = r['effect']
        inter = ':' in term
        key = ('x:' if inter else 'm:') + fac + ('@' + ';'.join(f'{k}={v}' for k, v in at.items()) if at else '') \
            + ':' + test + '~' + ref
        comps.append({
            'key': key, 'term': term, 'factor': fac, 'at': at, 'test': test, 'ref': ref,
            'mt': mt, 'mr': mr, 'diff': diff, 'rel': 100 * diff / mr if (O['relative'] and mr) else None,
            't': None if r['value'] is None else flip * r['value'], 'df': r['df1'], 'thr': r['threshold'],
            'p': r['p'], 'pOwn': r['p_own'], 'g': g, 'sig': r['p'] <= alpha,
            'inside': (asig.get(term, False) if inter else None)})
    # every pair of levels of every family has its comparison
    for f in F:
        codes = [L['code'] for L in f['levels']]
        npairs = len(codes) * (len(codes) - 1) // 2
        have = [c for c in comps if c['factor'] == f['id'] and not c['at']]
        if len(have) != npairs and not (len(codes) == 2 and not have):
            fail(f'stats sheet: {rid}: {len(have)} main comparisons for {f["id"]}, need {npairs}')
        if len(F) == 2:
            other = next(x for x in F if x['id'] != f['id'])
            for L in other['levels']:
                h = [c for c in comps if c['factor'] == f['id'] and c['at'].get(other['id']) == L['code']]
                if len(h) != npairs:
                    fail(f'stats sheet: {rid}: {len(h)} comparisons of {f["id"]} at {other["id"]}={L["code"]}, need {npairs}')
    # a two-level main effect with no comparison row: its comparison is the ANOVA term itself
    for f in F:
        codes = [L['code'] for L in f['levels']]
        if len(codes) == 2 and not [c for c in comps if c['factor'] == f['id'] and not c['at']]:
            A = next(a for a in aov if a['term'] == f['id'])
            ref = f['reference']; test = next(x for x in codes if x != ref)
            mt, mr = emm({f['id']: test}), emm({f['id']: ref})
            g = hedges_g(part({f['id']: test}), part({f['id']: ref}), f['within'])
            g_computed = g_computed or g is not None
            comps.insert(0, {'key': f'm:{f["id"]}:{test}~{ref}', 'term': f['id'], 'factor': f['id'], 'at': {},
                             'test': test, 'ref': ref, 'mt': mt, 'mr': mr, 'diff': mt - mr,
                             'rel': 100 * (mt - mr) / mr if (O['relative'] and mr) else None,
                             't': None, 'df': None, 'thr': None, 'p': A['p'], 'pOwn': None,
                             'g': None if g is None else math.copysign(abs(g), mt - mr), 'sig': A['sig'], 'inside': None})
    nperm = sorted({x['n_perm'] for x in st if x['n_perm']})
    spl = next((L for L in S['split']['levels'] if L['code'] == sp), None) if sp else None
    return {
        'id': rid, 'outcome': O['id'], 'split': sp, 'name': O['name'], 'noun': O['noun'], 'unit': O['unit'],
        'dec': O['dec'], 'relative': O['relative'], 'splitName': spl['name'] if spl else '',
        'splitLong': spl['long'] if spl else '', 'n': n, 'values': values, 'cells': cell_rows,
        'levels': levels, 'aov': aov, 'comps': comps, 'nPerm': nperm, 'gComputed': g_computed}


def hedges_g(x, y, paired):
    """Only when the sheet has no effect size: paired d_z or pooled-SD d, with the small-sample correction."""
    if paired:
        d = [a - b for a, b in zip(x, y) if a is not None and b is not None]
        if len(d) < 3 or not sd(d):
            return None
        n = len(d)
        return mean(d) / sd(d) * (1 - 3 / (4 * (n - 1) - 1))
    a = [v for v in x if v is not None]
    b = [v for v in y if v is not None]
    if len(a) < 2 or len(b) < 2:
        return None
    sp = math.sqrt(((len(a) - 1) * sd(a) ** 2 + (len(b) - 1) * sd(b) ** 2) / (len(a) + len(b) - 2))
    if not sp:
        return None
    return (mean(a) - mean(b)) / sp * (1 - 3 / (4 * (len(a) + len(b)) - 9))


# ------------------------------------------------------------------ texts written from the data
class Texts:
    """Sentences with placeholders filled from a row's data. ref() wraps a statistic in a linked span and
    records its key, so that build() can assert that every cited key exists."""

    def __init__(self, S):
        self.S = S
        self.F = S['factors']
        self.cited = []

    def lv(self, fid, code):
        f = next(x for x in self.F if x['id'] == fid)
        return next(L for L in f['levels'] if L['code'] == code)

    def fac(self, fid):
        return next(x for x in self.F if x['id'] == fid)

    def ref(self, row, key, inner):
        self.cited.append((row['id'], key))
        return f'<span class="ref" data-row="{html.escape(row["id"])}" data-k="{html.escape(key)}">{inner}</span>'

    def cmp_stat(self, row, c):
        """"−10.0 Hz, −34.8%, p = 0.003": absolute difference with its unit, relative difference, p."""
        parts = [with_unit(signed(c['diff'], row['dec']), row['unit'])]
        if c['rel'] is not None:
            parts.append(signed(c['rel'], 1) + '%')
        parts.append(ph(c['p']))
        return self.ref(row, c['key'], ', '.join(parts))

    def term_name(self, t):
        return f' {TIMES} '.join(self.fac(x)['name'] for x in t.split(':'))

    def direction(self, c):
        return 'higher' if c['diff'] > 0 else 'lower'

    def main_clause(self, row, f, subject):
        """One factor's main effect: its significant comparisons, or that it did not differ."""
        A = next(a for a in row['aov'] if a['term'] == f['id'])
        cs = [c for c in row['comps'] if c['factor'] == f['id'] and not c['at']]
        if not A['sig']:
            return None, f'did not differ between {f["plural"]} ({self.ref(row, A["key"], ph(A["p"]))})'
        if len(f['levels']) == 2:
            c = cs[0]
            T, R = self.lv(f['id'], c['test']), self.lv(f['id'], c['ref'])
            return f'was {self.direction(c)} {T["phrase"]} than {R["phrase"]} ({self.cmp_stat(row, c)})', None
        sig = [c for c in cs if c['sig']]
        lead = f'differed between {f["plural"]} ({self.ref(row, A["key"], ph(A["p"]))})'
        if not sig:
            return lead + ', although no pair of levels differed on its own', None
        bits = [f'{self.direction(c)} {self.lv(f["id"], c["test"])["phrase"]} than {self.lv(f["id"], c["ref"])["phrase"]} '
                f'({self.cmp_stat(row, c)})' for c in sig]
        rest = len(cs) - len(sig)
        tail = '' if not rest else (', the other comparison not significant' if rest == 1 else ', the other comparisons not significant')
        return lead + ': ' + join_words(bits) + tail, None

    def reading(self, row, f, g, subject, first):
        """The interaction read as factor f within each level of g."""
        out = []
        groups = []
        for L in g['levels']:
            cs = [c for c in row['comps'] if c['factor'] == f['id'] and c['at'].get(g['id']) == L['code']]
            groups.append((L, cs))
        subj = cap(subject) if first else 'It'
        if len(f['levels']) == 2:
            cs = [(L, c[0]) for L, c in groups]
            sig = [(L, c) for L, c in cs if c['sig']]
            T = self.lv(f['id'], cs[0][1]['test']); R = self.lv(f['id'], cs[0][1]['ref'])
            if len(sig) == len(cs) and len({c['diff'] > 0 for _, c in cs}) == 1:
                d = self.direction(cs[0][1])
                order = sorted(cs, key=lambda x: -abs(x[1]['diff']))
                if len(order) == 2:
                    (L1, c1), (L2, c2) = order
                    out.append(f'{subj} was {d} {T["phrase"]} than {R["phrase"]}, more {L1["phrase"]} '
                               f'({self.cmp_stat(row, c1)}) than {L2["phrase"]} ({self.cmp_stat(row, c2)}).')
                else:
                    out.append(f'{subj} was {d} {T["phrase"]} than {R["phrase"]} ' +
                               join_words([f'{L["phrase"]} ({self.cmp_stat(row, c)})' for L, c in order]) + '.')
            elif sig:
                ns = [(L, c) for L, c in cs if not c['sig']]
                bits = [f'{self.direction(c)} {T["phrase"]} than {R["phrase"]} {L["phrase"]} ({self.cmp_stat(row, c)})'
                        for L, c in sig]
                s = f'{subj} was ' + join_words(bits, 'and')
                if ns:
                    s += ', but did not differ ' + join_words([f'{L["phrase"]} ({self.cmp_stat(row, c)})' for L, c in ns], 'or')
                out.append(s + '.')
            else:
                out.append(f'{subj} did not differ between {f["plural"]} ' +
                           join_words([f'{L["phrase"]} ({self.cmp_stat(row, c)})' for L, c in cs], 'or') + '.')
        else:
            bits = []
            for L, cs in groups:
                sig = [c for c in cs if c['sig']]
                if sig:
                    bits.append(cap(L['phrase']) + ', ' + subject + ' was ' + join_words(
                        [f'{self.direction(c)} {self.lv(f["id"], c["test"])["phrase"]} than '
                         f'{self.lv(f["id"], c["ref"])["phrase"]} ({self.cmp_stat(row, c)})' for c in sig]) + '.')
                else:
                    bits.append(cap(L['phrase']) + f', no pair of {f["plural"]} differed.')
            out.extend(bits)
        return out

    def row_paragraph(self, row, lead):
        F = self.F
        subject = row['noun']
        s = []
        if len(F) == 1:
            f = F[0]
            ok, no = self.main_clause(row, f, subject)
            s.append(cap(subject) + ' ' + (ok or no) + '.')
        else:
            A, B = F
            X = next(a for a in row['aov'] if ':' in a['term'])
            if X['sig']:
                s.append(f'The {A["noun"]} effect depended on the {B["noun"]} '
                         f'({self.ref(row, X["key"], self.term_name(X["term"]) + ", " + ph(X["p"]))}).')
                s += self.reading(row, A, B, subject, True)
                s += self.reading(row, B, A, subject, False)
            else:
                okA, noA = self.main_clause(row, A, subject)
                okB, noB = self.main_clause(row, B, subject)
                inter = (f'with no interaction between the {A["noun"]} and the {B["noun"]} '
                         f'({self.ref(row, X["key"], ph(X["p"]))})')
                if okA and okB:
                    s.append(f'{cap(subject)} {okA} and {okB[4:] if okB.startswith("was ") else okB}, {inter}.')
                elif okA or okB:
                    ok, no = (okA, noB) if okA else (okB, noA)
                    s.append(f'{cap(subject)} {ok}; it {no}, {inter}.')
                else:
                    s.append(f'{cap(subject)} {noA} or between {B["plural"]} '
                             f'({self.ref(row, next(a for a in row["aov"] if a["term"] == B["id"])["key"], ph(next(a for a in row["aov"] if a["term"] == B["id"])["p"]))}), {inter}.')
        return (f'<b>{html.escape(lead)}.</b> ' if lead else '') + ' '.join(s)


    # ---------------------------------------------------------------- correlations
    def corr_stat(self, row, e, X):
        """"r = −0.77, strong, −3.44% per mm, p = 0.012": r, its strength (significant only), slope, p."""
        parts = ['r = ' + fixed(e['r'], 2)]
        if e['sig'] and e['strength']:
            parts.append(e['strength'])
        parts.append(with_unit(signed(e['slope'], 2), row['yUnit']) + ' per ' + (X['unit'] or 'unit'))
        parts.append(ph(e['p']))
        return ', '.join(parts)

    def corr_paragraph(self, rows_sp, lead, C, X):
        """One split level's correlations: the significant ones by direction, then how many were not."""
        by = self.fac(C['by'])
        items = [(r, e) for r in rows_sp for e in r['entries']]
        sig = [(r, e) for r, e in items if e['sig']]
        ns = [(r, e) for r, e in items if not e['sig']]
        yname = rows_sp[0]['yNoun']

        def item(r, e):
            L = self.lv(by['id'], e['level'])
            return f'{r["noun"]} {L["phrase"]} ({self.ref(r, e["key"], self.corr_stat(r, e, X))})'
        s = []
        if sig:
            for word, grp in (('decreased', [x for x in sig if x[1]['r'] < 0]), ('increased', [x for x in sig if x[1]['r'] > 0])):
                if grp:
                    s.append(f'{cap(yname)} {word} with {X["noun"]} for ' + join_words([item(r, e) for r, e in grp]) + '.')
            if ns:
                r, e = min(ns, key=lambda x: x[1]['p'])
                k = len(ns)
                low = f'{math.floor(e["p"] * 1000) / 1000:.3f}'
                s.append(f'The other {k} correlation{"s" if k > 1 else ""} {"were" if k > 1 else "was"} not significant '
                         f'({self.ref(r, e["key"], "p ≥ " + low)}).')
        else:
            r, e = min(items, key=lambda x: x[1]['p'])
            s.append(f'{cap(yname)} did not correlate significantly with {X["noun"]} for any variable '
                     f'(smallest {self.ref(r, e["key"], ph(e["p"]))}).')
        return (f'<b>{html.escape(lead)}.</b> ' if lead else '') + ' '.join(s)


def strip_tags(h):
    return html.unescape(re.sub(r'<[^>]+>', '', h))


# ------------------------------------------------------------------ participants' characteristics
def read_people(S, base, ids):
    """The characteristics of the participants file (anonymized: the data's IDs only), for the methods."""
    P = S.get('participants') or {}
    if not (P.get('variables') or P.get('categorical')):
        return None
    rows = read_participants(S, base)
    miss = [i for i in ids if i not in rows]
    if miss:
        fail(f'participants file: no row for {", ".join(miss)}')
    out = {'section': P.get('section', 'Participants'), 'vars': [], 'cats': []}
    for V in P.get('variables', []):
        v = [num(rows[i].get(V['id'])) for i in ids]
        vv = [x for x in v if x is not None]
        if not vv:
            fail(f'participants file: no value in column "{V["id"]}"')
        out['vars'].append({'id': V['id'], 'key': 'pv:' + V['id'], 'name': V['name'],
                            'noun': V.get('noun', 'the ' + V['name'].lower()), 'unit': V.get('unit', ''),
                            'dec': V.get('dec', 1), 'vdec': 0 if all(float(x).is_integer() for x in vv) else V.get('dec', 1),
                            'values': v, 'n': len(vv), 'mean': mean(v), 'sd': sd(v),
                            'min': min(vv), 'max': max(vv)})
    for Cc in P.get('categorical', []):
        v = [(rows[i].get(Cc['id']) or '').strip() for i in ids]
        codes = [L['code'] for L in Cc['levels']]
        bad = sorted(set(v) - set(codes))
        if bad:
            fail(f'participants file: {Cc["id"]} has levels {bad} that study.json does not list')
        out['cats'].append({'id': Cc['id'], 'key': 'pc:' + Cc['id'], 'name': Cc['name'], 'values': v,
                            'levels': [{'code': L['code'], 'name': L['name'], 'plural': L.get('plural', L['name'] + 's'),
                                        'count': v.count(L['code'])} for L in Cc['levels']]})
    return out


# ------------------------------------------------------------------ correlations (given in a sheet of their own)
def y_spec(spec, S):
    """'rel:Device=ACC~Echo': 100 × (ACC − Echo) / Echo per participant; 'diff:…': ACC − Echo."""
    m = re.fullmatch(r'(rel|diff):(\w+)=([^~]+)~(.+)', spec or '')
    if not m:
        fail(f'correlations: y "{spec}" is not rel:<factor>=<test>~<ref> or diff:<factor>=<test>~<ref>')
    kind, fid, test, ref = m.groups()
    f = next((x for x in S['factors'] if x['id'] == fid), None)
    if not f or test not in [L['code'] for L in f['levels']] or ref not in [L['code'] for L in f['levels']]:
        fail(f'correlations: y "{spec}" names an unknown factor or level')
    T = next(L for L in f['levels'] if L['code'] == test)['name'].lower()
    R = next(L for L in f['levels'] if L['code'] == ref)['name'].lower()
    noun = ('the relative difference' if kind == 'rel' else 'the difference') + f' between {T} and {R}'
    label = 'Relative difference' if kind == 'rel' else 'Difference'
    formula = f'100 × ({T} − {R}) / {R}' if kind == 'rel' else f'{T} − {R}'
    return kind, fid, test, ref, noun, label, formula, f'negative when {T} gives the lower value'


def pearson(x, y):
    p = [(a, b) for a, b in zip(x, y) if a is not None and b is not None]
    mx, my = mean([a for a, _ in p]), mean([b for _, b in p])
    sxy = sum((a - mx) * (b - my) for a, b in p)
    sxx, syy = sum((a - mx) ** 2 for a, _ in p), sum((b - my) ** 2 for _, b in p)
    return sxy / math.sqrt(sxx * syy), sxy / sxx, len(p)


def build_corr(S, base, rows, people):
    C = S.get('correlations')
    if not C:
        return {}, None
    if not people:
        fail('correlations need the participants file (its x variable)')
    X = next((v for v in people['vars'] if v['id'] == C['x']), None)
    if not X:
        fail(f'correlations: x "{C["x"]}" is not a variable of the participants file')
    by = next((f for f in S['factors'] if f['id'] == C['by']), None)
    if not by:
        fail(f'correlations: by "{C["by"]}" is not a factor')
    with open(base / C['file'], encoding='utf-8-sig', newline='') as fh:
        sheet = list(csv.DictReader(fh))
    for r in sheet:
        r['at'] = {a.split('=')[0].strip(): a.split('=')[1].strip() for a in (r.get('at') or '').split(';') if '=' in a}
        r['split'] = (r.get('split') or '').strip()
    alpha = S['stats']['alpha']
    strength = sorted(C.get('strength', []), key=lambda t: -t[0])
    out = {}
    fam = sorted({r.get('family') for r in sheet if r.get('family')})
    for oid in C['outcomes']:
        O = next((o for o in S['outcomes'] if o['id'] == oid), None)
        if not O:
            fail(f'correlations: unknown outcome {oid}')
        for base_row in [r for r in rows.values() if r['outcome'] == oid]:
            sp = base_row['split']
            entries, ydesc = [], None
            for L in by['levels']:
                hit = [r for r in sheet if r['outcome'] == oid and r['split'] == sp and r['at'] == {by['id']: L['code']}
                       and r.get('x', C['x']) == C['x']]
                if len(hit) != 1:
                    fail(f'correlations: {len(hit)} rows for {oid} {sp or ""} {by["id"]}={L["code"]} (need exactly 1)')
                h = hit[0]
                kind, fid, test, ref, noun, label, formula, neg = y_spec(h.get('y'), S)
                ydesc = (noun, label, kind, formula, neg)
                lv = {by['id']: L['code']}
                code = lambda d: '|'.join(d[f['id']] for f in S['factors'])
                if len({by['id'], fid}) != len(S['factors']):
                    fail('correlations: y and by must name every factor of the design between them')
                t = base_row['values'][code({**lv, fid: test})]
                rf = base_row['values'][code({**lv, fid: ref})]
                yv = [None if a is None or b is None or (kind == 'rel' and not b) else
                      (100 * (a - b) / b if kind == 'rel' else a - b) for a, b in zip(t, rf)]
                r_sheet, p, p_raw = num(h.get('r')), num(h.get('p')), num(h.get('p_uncorrected'))
                r_data, slope_data, n = pearson(X['values'], yv)
                if r_sheet is None or abs(r_sheet - r_data) > 1e-6:
                    fail(f'correlations: {oid} {sp} {L["code"]}: the sheet\'s r {r_sheet} is not the data\'s {r_data:.8f}; '
                         'are the participants in the same order, or y defined the same way?')
                slope = num(h.get('slope'))
                slope = slope_data if slope is None else slope
                icpt = num(h.get('intercept'))
                if icpt is None:
                    icpt = mean([b for a, b in zip(X['values'], yv) if a is not None and b is not None]) - \
                        slope * mean([a for a, b in zip(X['values'], yv) if a is not None and b is not None])
                sig = p is not None and p <= alpha
                word = next((w for th, w in strength if abs(r_sheet) >= th), '') if sig else ''
                entries.append({'key': f'r:{by["id"]}={L["code"]}', 'level': L['code'], 'r': r_sheet, 'p': p,
                                'pRaw': p_raw, 'slope': slope, 'intercept': icpt, 'n': n, 'sig': sig,
                                'strength': word, 'y': yv})
            rid = 'c:' + base_row['id']
            out[rid] = {'id': rid, 'kind': 'corr', 'outcome': oid, 'name': O['name'], 'noun': O['noun'],
                        'split': sp, 'splitName': base_row['splitName'], 'splitLong': base_row['splitLong'],
                        'by': by['id'], 'x': X['id'], 'yNoun': ydesc[0], 'yLabel': ydesc[1], 'yFormula': ydesc[3], 'yNeg': ydesc[4],
                        'yUnit': '%' if ydesc[2] == 'rel' else O['unit'], 'yDec': 1 if ydesc[2] == 'rel' else O['dec'],
                        'entries': entries, 'n': max(e['n'] for e in entries)}
    meta = {'x': X['id'], 'by': by['id'], 'family': fam[0] if len(fam) == 1 else None,
            'method': sorted({r.get('method', '') for r in sheet}), 'correction': sorted({r.get('correction', '') for r in sheet}),
            # family_of 'split': the tests were corrected within each split level (each axis), not all together
            'within': (S.get('split') or {}).get('name', '').lower() if {r.get('family_of', '') for r in sheet} == {'split'} else '',
            'strength': strength}
    return out, meta


# ------------------------------------------------------------------ methods (Markdown) and the reading guide
def md_inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r'&lt;(/?)(sub|sup|b|i)&gt;', r'<\1\2>', s)
    s = re.sub(r'\[([^\]]+)\]\((https?://[^)\s]+)\)', r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>', s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
    s = re.sub(r'(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])', r'<i>\1</i>', s)
    return s


def read_methods(path, fill):
    if not path.exists():
        return []
    secs, cur, para = [], None, []

    def flush():
        if para and cur is not None:
            cur['p'].append(fill(md_inline(' '.join(para))))          # placeholders may be linked spans
        para.clear()
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.startswith('## '):
            flush()
            cur = {'h': line[3:].strip(), 'p': []}
            secs.append(cur)
        elif not line.strip():
            flush()
        else:
            if cur is None:
                cur = {'h': '', 'p': []}
                secs.append(cur)
            para.append(line.strip())
    flush()
    return secs


def ref_label(text):
    """'Freedman D, Lane D (1983). …' -> ('Freedman & Lane', '1983'); three authors or more: 'Winkler et al.'."""
    m = re.match(r'\s*(.+?)\s*\((\d{4}[a-z]?)\)', text)
    if not m:
        fail(f'reference without "Authors (Year)": {text[:60]}')

    def surname(a):
        t = a.split()
        return ' '.join(t[:-1]) if len(t) > 1 and re.fullmatch(r'[A-Z][A-Z.-]{0,4}', t[-1]) else a
    names = [surname(a.strip()) for a in m.group(1).split(',') if a.strip()]
    lab = names[0] if len(names) == 1 else f'{names[0]} & {names[1]}' if len(names) == 2 else f'{names[0]} et al.'
    return lab, m.group(2)


def resolve_refs(methods):
    """The reference list ([@key] entries of the References section) and the citations of the other sections:
    [@key] -> 'Freedman & Lane, 1983' (inside your own parentheses), [@key|n] -> 'Freedman & Lane (1983)'. Each
    citation shows its reference in a popover; a citation and its entry mark each other."""
    sec = next((x for x in methods if x['h'].strip().lower() == 'references'), None)
    refs = {}
    if sec:
        for i, para in enumerate(sec['p']):
            m = re.match(r'\[@([\w-]+)\]\s*(.*)', para, flags=re.S)
            if not m:
                continue
            key, body = m.groups()
            if key in refs:
                fail(f'methods.md: reference [@{key}] listed twice')
            refs[key] = {'label': ref_label(strip_tags(body)), 'html': body}
            sec['p'][i] = f'<span class="refentry" data-ref="{key}">{body}</span>'
    used = set()

    def rep(m):
        key, narrative = m.group(1), m.group(2)
        if key not in refs:
            fail(f'methods.md cites [@{key}], which the References section does not list')
        used.add(key)
        a, y = refs[key]['label']
        return f'<span class="cite" data-cite="{key}" tabindex="0">{a} ({y})</span>' if narrative else \
            f'<span class="cite" data-cite="{key}" tabindex="0">{a}, {y}</span>'
    for x in methods:
        if x is not sec:
            x['p'] = [re.sub(r'\[@([\w-]+)(\|n)?\]', rep, q) for q in x['p']]
    for key in sorted(set(refs) - used):
        print(f'note: reference [@{key}] is listed but never cited')
    return {k: {'label': list(v['label']), 'html': v['html']} for k, v in refs.items()}


def guide(S, rows, people=None, cmeta=None):
    F = S['factors']
    alpha = S['stats']['alpha']
    conv = []
    for f in F:
        R = next(L for L in f['levels'] if L['code'] == f['reference'])
        others = [L['name'].lower() for L in f['levels'] if L['code'] != f['reference']]
        conv.append(f'{join_words(others, "or")} − {R["name"].lower()} for {f["noun"]}')
    rel = any(r['relative'] for r in rows.values())
    gcomp = any(r['gComputed'] for r in rows.values())
    p = [
        'Every statistic in a text, a table or a figure is linked. Linked statistics in the texts have a dotted '
        'underline. <b>Hover</b> one, or a table row or cell, and the same result is marked everywhere: in the '
        'text, in the table and in the figure beside it, which shows that row. <b>Click</b> it to keep it shown '
        'while you move to the figure; click it again, press <b>Esc</b> or click anywhere else to release it. '
        'Hovering a panel or a violin of the figure marks its statistics in the same way.',
        f'<b>Bold means significant</b> (p ≤ {alpha:g}), and only that, in the tables and the figures.',
        'Each figure shows every participant as a cross, at their own value, spread sideways only to avoid '
        'overlap. A grey line joins each participant\'s values across the levels of a within-participant factor. '
        'Hover a cross to see the participant and follow them across the panels. Each violin is the '
        'distribution of its group (a kernel density), its outline bold over the mean ± SD, the black line '
        'its mean, with the mean and (SD) written on it. The ⤢ button enlarges the figure.',
    ]
    if len(F) == 2:
        A, B = F
        p.append(f'The first row of the figure shows the main effects: each participant\'s mean over the other '
                 f'factor\'s levels. The next rows read the {A["name"]} {TIMES} {B["name"]} interaction one factor '
                 f'at a time: {A["plural"]} within each {B["noun"]}, then {B["plural"]} within each {A["noun"]}. '
                 'Their comparisons are drawn solid where the interaction is significant (inside the interaction). '
                 'Where it is not, they are drawn pale and greyed in the tables: outside the interaction, they '
                 'mostly reflect the main effects and are not interaction effects.')
    d = 'Differences are ' + join_words(conv) + ', computed from the group means.'
    if rel:
        d += ' Relative differences divide them by the mean of the second level (the reference).'
    d += (' Effect sizes are Hedges\' g, signed like the difference' +
          (' (computed from the data where the statistics gave none).' if gcomp else '.'))
    p.append(d)
    if cmeta:
        p.append('The correlations relate each participant\'s difference to their characteristic: one scatter plot per '
                 'test, every participant as a cross, the least-squares line (solid when the correlation is '
                 'significant, dashed otherwise), with r, the slope and p. Their p-values are corrected together, as '
                 'the methods say.')
    if people:
        p.append(f'The participants\' characteristics are in the methods ({html.escape(people["section"])}), with a '
                 'figure. Hovering a participant anywhere in the document shows their characteristics.')
    p.append('Citations (author, year) have a dotted underline: hover one to read its reference, with its link; click it '
             'to keep it open. Its entry in the references is marked at the same time.')
    p.append('Each participant\'s values are under <b>Values per participant</b>, below each table, and can be '
             'downloaded as a CSV file.')
    return {'h': 'How to read this document', 'p': p}


# ------------------------------------------------------------------ the page
def build(study_path, out=None, check=False):
    study_path = Path(study_path).resolve()
    base = study_path.parent
    S = load_study(study_path)
    rows, ids, stats, terms = build_rows(S, base)
    n = len(ids)
    people = read_people(S, base, ids)
    crows, cmeta = build_corr(S, base, rows, people)
    nperm = sorted({p for r in rows.values() for p in r['nPerm']})
    fill_vals = {'n': str(n), 'alpha': f'{S["stats"]["alpha"]:g}'}
    if len(nperm) == 1:
        fill_vals['n_perm'] = f'{int(nperm[0]):,}'
        fill_vals['p_min'] = f'1/{int(nperm[0]):,} = {1 / nperm[0]:.6f}'.rstrip('0')

    if cmeta and cmeta['family']:
        fill_vals['n_corr'] = str(int(float(cmeta['family'])))
    pcited = []

    def pref(key, text):
        pcited.append(key)
        return f'<span class="ref" data-row="participants" data-k="{key}">{text}</span>'

    def fill(s):
        """{n}, {n_perm}, {p_min}, {alpha}, {n_corr}; from the participants file, linked to its table and figure:
        {mean_sd:age} (25.1 ± 4.4), {range:age} (21.0–34.0), {count:sex=M} (12)."""
        def rep(m):
            k, arg = m.group(1), m.group(2)
            if arg is None:
                if k not in fill_vals:
                    fail(f'unknown placeholder {{{k}}} (known: {", ".join(fill_vals)}, mean_sd:, range:, count:)')
                return fill_vals[k]
            if not people:
                fail(f'placeholder {{{k}:{arg}}} needs the participants file')
            if k in ('mean_sd', 'range'):
                V = next((v for v in people['vars'] if v['id'] == arg), None)
                if not V:
                    fail(f'placeholder {{{k}:{arg}}}: no such participants variable')
                txt = (f'{fixed(V["mean"], V["dec"])} \u00b1 {fixed(V["sd"], V["dec"])}' if k == 'mean_sd'
                       else f'{fixed(V["min"], V["vdec"])}\u2013{fixed(V["max"], V["vdec"])}')
                return pref(V['key'], txt)
            if k == 'count':
                cid, _, code = arg.partition('=')
                Cc = next((c for c in people['cats'] if c['id'] == cid), None)
                L = Cc and next((l for l in Cc['levels'] if l['code'] == code), None)
                if not L:
                    fail(f'placeholder {{count:{arg}}}: no such participants level')
                return pref(Cc['key'] + '=' + code, str(L['count']))
            fail(f'unknown placeholder {{{k}:{arg}}}')
        return re.sub(r'\{([a-z_]+)(?::([^}]+))?\}', rep, s)

    T = Texts(S)
    groups = []
    for G in S['results']:
        tabs = []
        for tab in G['tabs']:
            if tab.get('correlations'):
                if not crows:
                    fail(f'results: tab "{tab["label"]}" asks for correlations, but study.json has none')
                X = next(v for v in people['vars'] if v['id'] == cmeta['x'])
                rids = list(crows)
                splits = list(dict.fromkeys(crows[r]['split'] for r in rids))
                paras = []
                for sp in splits:
                    rs = [crows[r] for r in rids if crows[r]['split'] == sp]
                    paras.append(T.corr_paragraph(rs, rs[0]['splitLong'], S['correlations'], X))
                tabs.append({'label': tab['label'], 'rows': rids, 'text': paras, 'multi': True, 'kind': 'corr'})
                continue
            rids = []
            for oid in tab['outcomes']:
                rr = [r for r in rows.values() if r['outcome'] == oid]
                if not rr:
                    fail(f'results: unknown outcome {oid}')
                rids += [r['id'] for r in rr]
            multi = len(tab['outcomes']) > 1
            paras = []
            for rid in rids:
                r = rows[rid]
                lead = ', '.join(x for x in [r['name'] if multi else '', r['splitLong'] if not multi else r['splitName']] if x)
                paras.append(T.row_paragraph(r, lead))
            tabs.append({'label': tab['label'], 'rows': rids, 'text': paras, 'multi': multi})
        groups.append({'label': G['label'], 'tabs': tabs})

    # every cited key exists in its row
    for rid, key in T.cited:
        if rid in crows:
            if key not in {e['key'] for e in crows[rid]['entries']}:
                fail(f'text cites {key} of {rid}, which the correlation does not hold')
            continue
        r = rows[rid]
        keys = {a['key'] for a in r['aov']} | {c['key'] for c in r['comps']} | {'cell:' + c['code'] for c in r['cells']}
        if key not in keys:
            fail(f'text cites {key} of {rid}, which the row does not hold')
    methods = read_methods(base / S.get('methods', 'methods.md'), fill)
    at = next((i for i, s in enumerate(methods) if s['h'].strip().lower() == 'references'), len(methods))
    methods.insert(at, guide(S, rows, people, cmeta))      # the reading guide, before any reference list
    refs = resolve_refs(methods)
    if people and not any(s['h'] == people['section'] for s in methods):
        fail(f'methods.md has no section "{people["section"]}" for the participants\' table')

    DATA = {
        'title': S['title'], 'subtitle': fill(S.get('subtitle', '')), 'footer': S.get('footer', ''),
        'alpha': S['stats']['alpha'], 'nPerm': nperm[0] if len(nperm) == 1 else None,
        'people': [f'{S["data"].get("participant_prefix", "P")}{k + 1}' for k in range(n)],
        'factors': [{'id': f['id'], 'name': f['name'], 'noun': f['noun'], 'plural': f['plural'], 'within': f['within'],
                     'ref': f['reference'], 'levels': [{k: L[k] for k in ('code', 'name', 'short', 'color', 'color_dark')}
                                                       for L in f['levels']]} for f in S['factors']],
        'terms': terms, 'split': S.get('split', {}).get('name', ''),
        'groups': groups, 'rows': {**rows, **crows}, 'methods': methods, 'people_info': people, 'corr': cmeta, 'refs': refs,
    }
    if check:
        for G in groups:
            for t in G['tabs']:
                print(f'== {G["label"]} / {t["label"]}')
                for p in t['text']:
                    print('  ' + strip_tags(p))
        print('== Methods (participants)')
        for sec in methods:
            if people and sec['h'] == people['section']:
                for p_ in sec['p']:
                    print('  ' + strip_tags(p_))
        print(f'{len(rows)} rows, {len(crows)} correlation rows, {len(T.cited) + len(pcited)} linked statistics, {n} participants')
        return None
    tpl = (HERE / 'template.html').read_text(encoding='utf-8')
    tpl = re.sub(r'<!--.*?-->\s*', '', tpl, flags=re.S)       # template notes do not ship
    if tpl.count('/*DATA*/') != 1:
        fail('the template must hold /*DATA*/ exactly once')
    js = json.dumps(DATA, ensure_ascii=False, separators=(',', ':'), allow_nan=False).replace('</', '<\\/')
    page = tpl.replace('/*DATA*/', js).replace('<title></title>', f'<title>{html.escape(S["title"])}</title>')
    out = Path(out) if out else base / (re.sub(r'[\\/:*?"<>|]', '', S.get('file_name', S['title'])) + '.html')
    out.write_text(page, encoding='utf-8')
    print(f'wrote {out} ({len(page) / 1e6:.2f} MB): {len(rows)} rows, {len(crows)} correlation rows, '
          f'{len(T.cited) + len(pcited)} linked statistics, {n} participants')
    return out


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')            # minus signs and units on any console
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('study')
    ap.add_argument('--out')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    build(a.study, a.out, a.check)
