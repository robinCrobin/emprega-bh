"""Smoke de infraestrutura; nao e um teste funcional ponta a ponta."""
import argparse
import json
import sys
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument('--api', default='http://127.0.0.1:8000')
parser.add_argument('--web', default='http://127.0.0.1:5173')
args = parser.parse_args()
failures = 0
for name, url in [
    ('API ativa', args.api.rstrip('/') + '/healthz'),
    ('API e banco', args.api.rstrip('/') + '/readyz'),
    ('Frontend', args.web.rstrip('/') + '/'),
    ('Proxy frontend para API', args.web.rstrip('/') + '/api/healthz'),
]:
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            body = response.read().decode()
            if name != 'Frontend':
                if json.loads(body).get('status') != 'ok':
                    raise ValueError('Estado inesperado')
            elif '<div id="root">' not in body:
                raise ValueError('Pagina React nao encontrada')
        print('OK:', name)
    except Exception as error:
        failures += 1
        print('FALHOU:', name, type(error).__name__)
sys.exit(1 if failures else 0)
