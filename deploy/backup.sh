#!/usr/bin/env bash
# Backup do banco (usuários, conversas, livros liberados, conexão DeepSeek) e da
# secret.key, que abre as API keys criptografadas. Sem ela, a API key do DeepSeek
# precisa ser cadastrada de novo.
#
#   bash deploy/backup.sh                    grava em ~/backups/nimb-AAAAMMDD-HHMM.tar.gz
#   bash deploy/backup.sh s3://meu-bucket    também envia para o S3 (exige aws cli configurado)
#
# Agendar todo dia às 3h:  crontab -e  →  0 3 * * * bash $HOME/PAC-Resposta-de-Nimb/deploy/backup.sh
set -euo pipefail
cd "$(dirname "$0")"

DEST="$HOME/backups"
STAMP="$(date +%Y%m%d-%H%M)"
mkdir -p "$DEST"

# Cópia consistente do SQLite com a API no ar (API de backup do sqlite3)
docker compose exec -T api python -c "
import sqlite3
src = sqlite3.connect('/app/data/nimb.db')
dst = sqlite3.connect('/app/data/backup.db')
src.backup(dst)
dst.close(); src.close()
"
docker compose cp api:/app/data/backup.db "$DEST/nimb-$STAMP.db"
docker compose cp api:/app/data/secret.key "$DEST/secret-$STAMP.key" 2>/dev/null || true
docker compose exec -T api rm -f /app/data/backup.db

FILES=("nimb-$STAMP.db")
[[ -f "$DEST/secret-$STAMP.key" ]] && FILES+=("secret-$STAMP.key")
tar -czf "$DEST/nimb-$STAMP.tar.gz" -C "$DEST" "${FILES[@]}"
rm -f "$DEST/nimb-$STAMP.db" "$DEST/secret-$STAMP.key"
chmod 600 "$DEST/nimb-$STAMP.tar.gz"
echo "Backup: $DEST/nimb-$STAMP.tar.gz"

if [[ $# -gt 0 ]]; then
  aws s3 cp "$DEST/nimb-$STAMP.tar.gz" "$1/"
fi

# Mantém os 14 backups mais recentes
ls -1t "$DEST"/nimb-*.tar.gz | tail -n +15 | xargs -r rm -f
