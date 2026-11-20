#!/bin/bash
# Instala no JmLab o leitor de avisos da Fábrica (Telegram).
# Uso (no servidor, dentro desta pasta):  sudo bash instalar-servidor.sh
set -euo pipefail
cd "$(dirname "$0")"
[ "$(id -u)" = 0 ] || { echo "Rode com sudo."; exit 1; }
[ -f /etc/jmlab/telegram.env ] || { echo "Falta /etc/jmlab/telegram.env (o mesmo do alerta SMART)."; exit 1; }
mountpoint -q /srv/nas || { echo "O HD do NAS não está montado em /srv/nas."; exit 1; }

install -d -o jm -g jm -m 0755 /srv/nas/arquivos/fabrica
install -d -o jm -g jm -m 0755 /srv/nas/arquivos/fabrica/_avisos /srv/nas/arquivos/fabrica/_avisos/enviados
install -d -m 0755 /usr/local/lib/jmlab
install -m 0755 fabrica-avisos.py /usr/local/lib/jmlab/fabrica-avisos.py
install -m 0644 fabrica-avisos.service fabrica-avisos.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now fabrica-avisos.timer
echo "✔ Instalado. Teste: na Central, clique em “🏠 Testar JmLab” (chega no Telegram em até 1 minuto)."
echo "  Log: journalctl -u fabrica-avisos -n 20 --no-pager"
