"""Cria .env local sem sobrescrever configuracoes existentes."""
from pathlib import Path
import secrets

root = Path(__file__).resolve().parents[1]
target = root / '.env'
if target.exists():
    print('.env ja existe; arquivo preservado.')
else:
    content = (root / '.env.example').read_text(encoding='utf-8')
    content = content.replace('POSTGRES_PASSWORD=\n', 'POSTGRES_PASSWORD=' + secrets.token_urlsafe(24) + '\n')
    target.write_text(content, encoding='utf-8')
    target.chmod(0o600)
    print('.env criado com senha local aleatoria. Nao envie esse arquivo ao GitHub.')
