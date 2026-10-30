"""
Configurações da aplicação, lidas do arquivo `backend/.env` (ver `.env.example`).
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND_DIR / ".env")


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    app_name: str = "Respostas de Nimb API"
    version: str = "0.4.0"
    # Swagger em /docs. Desligado por padrão: ligue só localmente (ENABLE_DOCS=true)
    enable_docs: bool = _bool("ENABLE_DOCS", False)

    host: str = os.getenv("API_HOST", "0.0.0.0")
    port: int = int(os.getenv("API_PORT", "8000"))

    # Banco local (SQLite) para conexões LLM e histórico de sessões
    database_path: Path = Path(
        os.getenv("DATABASE_PATH", str(BACKEND_DIR / "data" / "nimb.db"))
    )

    # 5500 -> protótipo estático | 3000 -> front React/Vite (frontend/V2 - front Studio)
    cors_origins: list[str] = field(
        default_factory=lambda: _csv(
            os.getenv(
                "CORS_ORIGINS",
                "http://localhost:3000,http://127.0.0.1:3000,"
                "http://localhost:5500,http://127.0.0.1:5500",
            )
        )
    )

    # Tempo máximo (segundos) de espera pela resposta da LLM. Abaixo dos ~100 s
    # em que o Cloudflare encerra a requisição (erro 524).
    llm_timeout: float = float(os.getenv("LLM_TIMEOUT", "90"))
    # Quantidade de mensagens anteriores da sessão enviadas como contexto
    history_limit: int = int(os.getenv("HISTORY_LIMIT", "10"))

    # Níveis de caos (Baixo, Médio, Alto, Louco), ver app/services/chaos.py:
    # limite (%) da regra de alucinação e voltas de revisão (harness) de cada nível
    chaos_hallucination_chances: list[float] = field(
        default_factory=lambda: [float(v) for v in _csv(os.getenv("CHAOS_HALLUCINATION_CHANCES", "5,15,30,50"))]
    )
    chaos_harness_rounds: list[int] = field(
        default_factory=lambda: [int(v) for v in _csv(os.getenv("CHAOS_HARNESS_ROUNDS", "0,1,2,3"))]
    )
    # Fuso do "registro" (data e hora) usado na regra de alucinação
    chaos_timezone: str = os.getenv("CHAOS_TIMEZONE", "America/Sao_Paulo")
    # Tempo total (s) da pergunta, da busca à última chamada à LLM. Cada chamada recebe
    # só o tempo que resta, então a requisição termina antes dos ~100 s do Cloudflare
    answer_time_budget: float = float(os.getenv("ANSWER_TIME_BUDGET", "85"))

    # Conexão LLM padrão (opcional). Se o banco estiver vazio na subida da API e
    # LLM_DEEPSEEK_API estiver definida, uma conexão DeepSeek é criada com estes valores.
    default_llm_provider: str | None = os.getenv("LLM_PROVIDER") or "deepseek"
    default_llm_model: str | None = os.getenv("LLM_MODEL") or None
    default_llm_api_key: str | None = os.getenv("LLM_DEEPSEEK_API") or None
    default_llm_base_url: str | None = os.getenv("LLM_BASE_URL") or None

    # ------------------------------------------------------------------
    # Autenticação
    # ------------------------------------------------------------------
    # Chave usada para criptografar as API keys das LLMs no banco. Se vazia,
    # uma chave é gerada e salva em data/secret.key (fora do Git).
    app_secret_key: str | None = os.getenv("APP_SECRET_KEY") or None

    # Cookie de sessão (HttpOnly). Em produção com HTTPS use COOKIE_SECURE=true.
    session_cookie_name: str = os.getenv("SESSION_COOKIE_NAME", "nimb_session")
    cookie_secure: bool = _bool("COOKIE_SECURE", False)
    session_ttl_hours: int = int(os.getenv("SESSION_TTL_HOURS", "8"))
    remember_me_days: int = int(os.getenv("REMEMBER_ME_DAYS", "7"))

    # Login com Google (Google Identity Services). Vazio = botão desativado.
    google_client_id: str | None = os.getenv("GOOGLE_CLIENT_ID") or None

    # Contas são criadas no primeiro login com Google. Com false, só entram
    # usuários que já existem no banco.
    registration_enabled: bool = _bool("REGISTRATION_ENABLED", True)
    # E-mails administradores: viram admin ao criar a conta e a cada login
    admin_emails: list[str] = field(
        default_factory=lambda: [e.lower() for e in _csv(os.getenv("ADMIN_EMAILS", ""))]
    )
    # A primeira conta criada vira administradora. Desligado por padrão: num
    # domínio público, quem entrar primeiro ganharia o papel de admin
    first_user_is_admin: bool = _bool("FIRST_USER_IS_ADMIN", False)
    # Lista de acesso: só entram os e-mails cadastrados pelos administradores
    # (Minha conta → E-mails com acesso). Administradores entram sempre.
    allowlist_enabled: bool = _bool("ALLOWLIST_ENABLED", True)

    # Limite de requisições por minuto, por IP, na rota de login
    auth_rate_limit_per_minute: int = int(os.getenv("AUTH_RATE_LIMIT_PER_MINUTE", "20"))

    # ------------------------------------------------------------------
    # Livros e banco vetorial
    # ------------------------------------------------------------------
    # Pasta do banco vetorial, construído à parte por `python -m vector_builder`.
    # Contém `catalog.json` (livros permitidos) e `books/<id>/` (Chroma).
    vector_store_dir: Path = Path(
        os.getenv("VECTOR_STORE_DIR", str(BACKEND_DIR.parent / "vector_store"))
    )
    # Provedor de embeddings padrão do construtor: sentence-transformers ou ollama.
    # Modelo vazio = padrão do provedor (BAAI/bge-m3 ou bge-m3 no Ollama).
    embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "ollama").strip().lower()
    embedding_model: str | None = os.getenv("EMBEDDING_MODEL") or None
    # Servidor local do Ollama (embeddings e, se configurado na tela, a LLM do chat)
    ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    # Tempo que o Ollama mantém o modelo de embeddings na memória ("-1" = sempre, "30m", "24h").
    # Carregar o bge-m3 de novo leva ~6 s na pergunta seguinte.
    ollama_keep_alive: str = os.getenv("OLLAMA_KEEP_ALIVE", "-1")
    # Tamanho máximo do PDF enviado para validação. O plano grátis do Cloudflare
    # recusa requisições acima de 100 MB; 95 MB deixa margem para o multipart.
    # Mantenha igual a MAX_UPLOAD_MB do front (PdfUploadModal.tsx).
    book_upload_max_mb: int = int(os.getenv("BOOK_UPLOAD_MAX_MB", "95"))
    # Validações de livro por minuto, por IP (ler PDF consome CPU)
    book_upload_rate_per_minute: int = int(os.getenv("BOOK_UPLOAD_RATE_PER_MINUTE", "5"))
    # Busca nos livros: trechos enviados à LLM e similaridade mínima (0 a 1) para um trecho contar
    rag_top_k: int = int(os.getenv("RAG_TOP_K", "5"))
    # Calibrado com `python -m vector_builder evaluate` (24/10/2026): 0.45 mantém 100% das perguntas
    # do livro e barra metade das fora do tema antes da LLM; o resto a LLM recusa.
    rag_min_similarity: float = float(os.getenv("RAG_MIN_SIMILARITY", "0.45"))
    # Busca híbrida (vetores + palavras/BM25, combinados por RRF), candidatos de cada busca e
    # peso das palavras no RRF (0.5 deu o melhor 1º lugar; 1.0 piora a ordem)
    rag_hybrid: bool = _bool("RAG_HYBRID", True)
    rag_candidates: int = int(os.getenv("RAG_CANDIDATES", "20"))
    rag_lexical_weight: float = float(os.getenv("RAG_LEXICAL_WEIGHT", "0.5"))

    # Sorteio de tesouro: cópia própria das tabelas de tesouro e das criaturas de cada livro
    # (`<livro>.sqlite`), refeita pela API sempre que o banco do livro é reconstruído
    treasure_dir: Path = Path(os.getenv("TREASURE_DIR", str(BACKEND_DIR / "data" / "tesouro")))


settings = Settings()
