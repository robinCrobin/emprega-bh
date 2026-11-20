"""Mede latencia HTTP. A renderizacao visual precisa de verificacao separada."""
import argparse
import json
import math
import statistics
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--url', required=True, help='Endpoint funcional real, com ocupacao existente')
parser.add_argument('--samples', type=int, default=30)
parser.add_argument('--limit', type=float, default=3.0)
parser.add_argument('--output', default='reports/local/latencia.json')
args = parser.parse_args()
if args.samples < 1 or args.limit <= 0:
    parser.error('samples e limit devem ser positivos')
results = []
errors = []

def query():
    start = time.perf_counter()
    with urllib.request.urlopen(args.url, timeout=max(5.0, args.limit + 1.0)) as response:
        response.read()
    return time.perf_counter() - start

try:
    cold_seconds = query()
except Exception as error:
    print('Falha na primeira consulta:', type(error).__name__)
    sys.exit(1)
for index in range(args.samples):
    try:
        results.append(query())
    except Exception as error:
        errors.append({'sample': index + 1, 'error': type(error).__name__})
ordered = sorted(results)
report = {
    'timestamp_utc': datetime.now(timezone.utc).isoformat(),
    'url': args.url,
    'samples_requested': args.samples,
    'samples_ok': len(results),
    'errors': errors,
    'first_request_seconds': cold_seconds,
    'mean_seconds': statistics.mean(results) if results else None,
    'p95_seconds': ordered[math.ceil(.95 * len(ordered)) - 1] if results else None,
    'max_seconds': max(results) if results else None,
    'limit_seconds': args.limit,
    'passed_warm_http': not errors and len(results) == args.samples and max(results) <= args.limit,
    'scope': 'HTTP apenas; nao comprova tempo de renderizacao do grafico',
}
output = Path(args.output)
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps(report, indent=2, ensure_ascii=False))
sys.exit(0 if report['passed_warm_http'] else 1)
