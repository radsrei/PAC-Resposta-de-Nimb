#!/usr/bin/env bash
# Prepara um servidor Ubuntu (EC2) novo para o Respostas de Nimb.
# Rode uma vez, logado por SSH:   bash deploy/server-setup.sh
# Instala Docker + Compose, cria swap (máquinas com pouca RAM) e ativa updates de segurança.
set -euo pipefail

echo "==> Atualizando pacotes"
sudo apt-get update -y
sudo apt-get upgrade -y

echo "==> Docker"
if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sudo sh
fi
sudo usermod -aG docker "$USER"
sudo systemctl enable --now docker

echo "==> Swap (evita falta de memória no build e no upload de PDFs grandes)"
if ! swapon --show | grep -q /swapfile; then
  sudo fallocate -l 2G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi

echo "==> Atualizações automáticas de segurança"
sudo apt-get install -y unattended-upgrades
sudo dpkg-reconfigure -f noninteractive unattended-upgrades

echo
echo "Pronto. Saia e entre de novo no SSH para usar o docker sem sudo:"
echo "  exit"
docker --version || true
