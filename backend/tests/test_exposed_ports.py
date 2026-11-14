"""
CI-08 Validação de portas expostas (análise estática da infraestrutura).

Garante, a cada PR, que a configuração de deploy não abre nada além do previsto:
- só o `web` (Caddy) publica portas no host, e só 80/443;
- API (8000) e Ollama (11434) ficam apenas na rede interna do Docker;
- nenhum serviço usa `network_mode: host` ou `privileged`;
- a API roda sem root e o Swagger fica desligado no exemplo de produção;
- segredos (.env, .pem, banco) não entram na imagem nem no Git.

A checagem em execução (containers de pé, varredura de portas) fica no CI, em
deploy/ci/check-exposed-ports.sh.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = yaml.safe_load((ROOT / "deploy" / "docker-compose.yml").read_text(encoding="utf-8"))
SERVICES = COMPOSE["services"]

ALLOWED_PUBLISHED = {"web": {80, 443}}
INTERNAL_ONLY = ["api", "ollama", "cloudflared"]


def _published_ports(service: dict) -> set[int]:
    ports = set()
    for entry in service.get("ports", []):
        if isinstance(entry, dict):
            ports.add(int(entry["published"]))
            continue
        spec = str(entry).split("/")[0]          # "443:443/udp" -> "443:443"
        parts = spec.split(":")
        if len(parts) == 1:
            pytest.fail(f"Porta sem mapeamento explícito (publica porta aleatória): {entry}")
        ports.add(int(parts[-2]))                # [ip:]host:container
    return ports


def test_somente_o_web_publica_portas():
    publishing = {name for name, svc in SERVICES.items() if svc.get("ports")}
    assert publishing == set(ALLOWED_PUBLISHED), f"Serviços publicando portas: {publishing}"


def test_web_publica_apenas_80_e_443():
    assert _published_ports(SERVICES["web"]) == ALLOWED_PUBLISHED["web"]


@pytest.mark.parametrize("name", INTERNAL_ONLY)
def test_servicos_internos_sem_porta_no_host(name):
    service = SERVICES[name]
    assert "ports" not in service, f"{name} não pode publicar portas no host"
    assert service.get("network_mode") != "host"


@pytest.mark.parametrize("name", list(SERVICES))
def test_nenhum_servico_privilegiado_ou_na_rede_do_host(name):
    service = SERVICES[name]
    assert not service.get("privileged", False)
    assert service.get("network_mode") != "host"
    assert "cap_add" not in service


def test_caddy_encaminha_api_so_pela_rede_interna():
    caddyfile = (ROOT / "deploy" / "Caddyfile").read_text(encoding="utf-8")
    assert re.findall(r"reverse_proxy\s+(\S+)", caddyfile) == ["api:8000"]
    assert "max_size 128KB" in caddyfile and "max_size 100MB" in caddyfile


def test_imagem_da_api_expoe_so_8000_e_roda_sem_root():
    dockerfile = (ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")
    assert re.findall(r"^EXPOSE\s+(.+)$", dockerfile, re.M) == ["8000"]
    users = re.findall(r"^USER\s+(\S+)$", dockerfile, re.M)
    assert users and users[-1] not in ("root", "0")
    assert "--workers\", \"1\"" in dockerfile


def test_exemplo_de_producao_mantem_swagger_desligado():
    env_example = (ROOT / "backend" / ".env.example").read_text(encoding="utf-8")
    assert re.search(r"^ENABLE_DOCS=false$", env_example, re.M)
    assert re.search(r"^FIRST_USER_IS_ADMIN=false$", env_example, re.M)
    assert re.search(r"^ALLOWLIST_ENABLED=true$", env_example, re.M)


@pytest.mark.parametrize("pattern", ["backend/.env", "deploy/.env", "*.pem", "backend/data", "vector_store", ".git"])
def test_segredos_e_dados_fora_da_imagem(pattern):
    lines = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    assert pattern in [line.strip() for line in lines]


@pytest.mark.skipif(shutil.which("git") is None, reason="git não instalado")
def test_nenhum_segredo_versionado_no_git():
    try:
        tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True,
                                 check=True).stdout.splitlines()
    except subprocess.CalledProcessError:
        pytest.skip("fora de um repositório git")
    forbidden = [
        f for f in tracked
        if f.endswith((".pem", ".key", ".db", ".sqlite"))
        or re.search(r"(^|/)\.env$", f)
        or f.startswith(("backend/data/", "vector_store/"))
    ]
    assert forbidden == [], f"Arquivos sensíveis versionados: {forbidden}"
