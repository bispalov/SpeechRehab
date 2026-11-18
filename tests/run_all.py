"""Прогнать все тесты SpeechRehab по очереди и вывести итог.

    python3 tests/run_all.py            # все тесты
    python3 tests/run_all.py test16 sw  # только выбранные (по части имени)

Нужны Python 3 и Playwright с Chromium:  pip install playwright && python3 -m playwright install chromium
"""
import os, re, sys, subprocess, time

HERE = os.path.dirname(os.path.abspath(__file__))
def order(f):
    m = re.match(r'test(\d*)\.py$', f)
    return (0, int(m.group(1) or 1)) if m else (1, f)
files = sorted([f for f in os.listdir(HERE) if re.match(r'test.*\.py$', f)], key=order) + ['audit.py']
want = sys.argv[1:]
if want: files = [f for f in files if any(w in f for w in want)]

total_ok = total = 0; bad = []
for f in files:
    t0 = time.time()
    args = [sys.executable, os.path.join(HERE, f)] + (['ru', 'uk', 'en'] if f == 'audit.py' else [])
    r = subprocess.run(args, capture_output=True, text=True, timeout=1800)
    out = r.stdout + r.stderr
    fails = [l for l in out.splitlines() if l.startswith('FAIL')]
    if f == 'audit.py':
        issues = [int(x) for x in re.findall(r'(\d+) issues', out)]
        good = bool(issues) and not any(issues) and r.returncode == 0
        line = 'layout audit: %d views x scales, %s' % (len(issues), 'no issues' if good else 'ISSUES: ' + str(sum(issues)))
    else:
        m = re.findall(r'(\d+)\s*/\s*(\d+)(?: passed)?', out)
        k, n = (int(m[-1][0]), int(m[-1][1])) if m else (0, 1)
        total_ok += k; total += n
        good = k == n and r.returncode == 0 and not fails
        line = '%d/%d' % (k, n)
    print('%-12s %-40s %5.0fs' % (f, line, time.time() - t0))
    if not good:
        bad.append(f)
        for l in (fails or out.strip().splitlines()[-15:])[:15]: print('    ' + l)
print('\nИтого проверок: %d/%d%s' % (total_ok, total, '' if not bad else ' — с ошибками: ' + ', '.join(bad)))
sys.exit(1 if bad else 0)
