"""
Linha de comando do construtor (rode dentro de `backend/`):

    python -m vector_builder register LIVRO.pdf --id t20-basico --title "Tormenta20 - Livro Básico"
    python -m vector_builder build    LIVRO.pdf --id t20-basico --title "Tormenta20 - Livro Básico"
    python -m vector_builder build    LIVRO.pdf --id t20-basico --provider ollama --model bge-m3
    python -m vector_builder build    LIVRO.pdf --id t20-basico --dry-run
    python -m vector_builder check    COPIA.pdf
    python -m vector_builder list
"""

import argparse
import sys
import time
from pathlib import Path

from app.core.config import settings
from app.core.exceptions import AppError
from app.services import book_catalog
from app.services.book_fingerprint import fingerprint_pdf
from app.services.book_validator import find_best_match, match_book


def _pdf(value: str) -> Path:
    path = Path(value)
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"arquivo não encontrado: {value}")
    return path


def _register(args) -> dict:
    from vector_builder.register import build_entry, parse_manual_probe

    title = args.title or (book_catalog.get_book(args.id) or {}).get("title")
    if not title:
        raise SystemExit("Informe --title (livro novo no catálogo).")
    manual = [parse_manual_probe(p) for p in args.probe] if args.probe else None
    print(f"Lendo impressão digital de {args.pdf.name}...")
    entry, warnings = build_entry(args.pdf, args.id, title, args.probes, manual)
    book_catalog.upsert_book(entry)
    print(f"Catálogo: '{entry['id']}' ({entry['title']}) — {entry['page_count']} páginas, "
          f"{len(entry['probes'])} frases de controle.")
    for probe in entry["probes"]:
        print(f"  p.{probe['page']:>4}: {probe['text'][:90]}")
    for warning in warnings:
        print(f"AVISO: {warning}")
    print(f"Gravado em {book_catalog.catalog_path()}")
    return entry


def cmd_register(args) -> int:
    _register(args)
    return 0


def _load_profile(args):
    import pymupdf
    from vector_builder.profile import auto_profile, find_profile, load_profile

    path = find_profile(args.id, args.profile)
    if path:
        return load_profile(path)
    print("AVISO: livro sem perfil em vector_builder/profiles/; usando o perfil automático.")
    with pymupdf.open(args.pdf) as doc:
        return auto_profile(doc)


def _report(extraction, chunks) -> None:
    from collections import Counter
    from vector_builder.extract import EMAIL

    sizes = sorted(len(c.text) for c in chunks) or [0]
    print(f"{len(chunks)} trechos | mediana {sizes[len(sizes) // 2]} | maior {sizes[-1]} caracteres | "
          f"{len(extraction.skipped)} páginas ignoradas")
    print("Por tipo: " + ", ".join(f"{k} {v}" for k, v in Counter(c.kind for c in chunks).most_common()))
    if len(extraction.empty) > extraction.page_count * 0.3:
        print(f"AVISO: {len(extraction.empty)} páginas sem texto. O PDF precisa de OCR antes de indexar.")
    if not any(extraction.printed.values()):
        print("AVISO: número impresso das páginas não encontrado; as fontes citarão a página do arquivo.")
    leaked = [c.index for c in chunks if EMAIL.search(c.text)]
    if leaked:
        raise SystemExit(f"Trechos com e-mail (marca d'água?): {leaked[:10]}. Ajuste o perfil antes de indexar.")


def cmd_build(args) -> int:
    from vector_builder.chunking import chunk_book, embedding_text
    from vector_builder.extract import extract
    from vector_builder.store import write_book_store, write_chunks_jsonl

    book = _register(args) if not args.skip_register else book_catalog.get_book(args.id)
    if book is None:
        raise SystemExit(f"Livro '{args.id}' não está no catálogo. Rode sem --skip-register.")

    started = time.monotonic()
    profile = _load_profile(args)
    print(f"Extraindo texto com o perfil '{profile.name}'...")
    extraction = extract(args.pdf, profile)
    chunks = chunk_book(extraction, profile, args.chunk_size, args.overlap, args.min_chars)
    _report(extraction, chunks)

    if args.dry_run:
        out = settings.vector_store_dir / "preview" / f"{book['id']}.chunks.jsonl"
        write_chunks_jsonl(out, chunks)
        print(f"Simulação: trechos gravados em {out} (nenhum embedding gerado).")
        return 0

    from vector_builder.embeddings import create_embedder

    embedder = create_embedder(args.provider, args.model, batch_size=args.batch_size,
                               device=args.device, ollama_url=args.ollama_url)
    print(f"Gerando embeddings: {embedder.provider} / {embedder.model_name}...")
    vectors = embedder.embed_passages([embedding_text(book["title"], c) for c in chunks])

    path = write_book_store(
        book, chunks, vectors, embedder.info,
        params={"chunk_size": args.chunk_size, "overlap": args.overlap, "min_chars": args.min_chars,
                "strategy": "entry", "context_header": True},
        source_sha256=fingerprint_pdf(args.pdf.read_bytes()).sha256,
        page_count=extraction.page_count,
        profile=profile.describe(),
    )
    print(f"Banco vetorial pronto em {path} ({time.monotonic() - started:.0f}s).")
    return 0


def cmd_check(args) -> int:
    books = book_catalog.load_catalog()
    if not books:
        raise SystemExit("Catálogo vazio.")
    fp = fingerprint_pdf(args.pdf.read_bytes())
    print(f"{args.pdf.name}: {fp.page_count} páginas, {fp.size_bytes} bytes, sha256 {fp.sha256[:16]}...")
    targets = [book_catalog.get_book(args.id)] if args.id else books
    if None in targets:
        raise SystemExit(f"Livro '{args.id}' não está no catálogo.")
    best = find_best_match(fp, targets)
    for book in targets:
        match = best if best and best.book is book else match_book(fp, book)
        status = "ACEITO" if match.accepted else "recusado"
        print(f"\n[{status}] {book['id']} — pontuação {match.score:.2f} (mínimo {book['min_score']})")
        for check in match.checks:
            print(f"  {'ok ' if check.passed else 'X  '} {check.name:<10} +{check.score:.2f}  {check.detail}")
    return 0 if best and best.accepted else 1


def cmd_list(_args) -> int:
    books = book_catalog.load_catalog()
    if not books:
        print(f"Catálogo vazio ({book_catalog.catalog_path()}).")
        return 0
    for book in books:
        manifest = book_catalog.vector_manifest(book["id"])
        emb = manifest["embedding"] if manifest else {}
        vector = (f"banco pronto: {manifest['chunks']} trechos, "
                  f"{emb.get('provider', 'sentence-transformers')}/{emb['model']}"
                  if manifest else "banco não construído")
        print(f"{book['id']:<24} {book['title']:<40} {book.get('page_count', '?')} p. | "
              f"{len(book['probes'])} frases | {vector}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    from vector_builder.embeddings import DEFAULT_MODELS, PROVIDERS

    parser = argparse.ArgumentParser(prog="python -m vector_builder", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    def add_register_args(p):
        p.add_argument("pdf", type=_pdf, help="PDF original do livro")
        p.add_argument("--id", required=True, help="identificador: minúsculas, números, - e _")
        p.add_argument("--title", help="título exibido (obrigatório para livro novo)")
        p.add_argument("--probes", type=int, default=8, help="quantidade de frases de controle (padrão 8)")
        p.add_argument("--probe", action="append", metavar="PAGINA:TEXTO",
                       help="frase de controle escolhida à mão (repita para várias); substitui as automáticas")

    p = sub.add_parser("register", help="cadastra/atualiza o livro no catálogo (só a impressão digital)")
    add_register_args(p)
    p.set_defaults(func=cmd_register)

    p = sub.add_parser("build", help="cadastra o livro e constrói o banco vetorial dele")
    add_register_args(p)
    p.add_argument("--skip-register", action="store_true", help="não atualiza a entrada do catálogo")
    p.add_argument("--profile", type=Path, default=None,
                   help="perfil tipográfico (padrão: vector_builder/profiles/<id>.json, ou automático)")
    p.add_argument("--chunk-size", type=int, default=2400, help="tamanho máximo do trecho em caracteres")
    p.add_argument("--overlap", type=int, default=300,
                   help="parágrafo final repetido no trecho seguinte, se couber neste tamanho")
    p.add_argument("--min-chars", type=int, default=120, help="entradas menores são unidas à anterior")
    p.add_argument("--provider", choices=PROVIDERS, default=None,
                   help=f"quem gera os embeddings (padrão: EMBEDDING_PROVIDER do .env, "
                        f"ou {settings.embedding_provider})")
    p.add_argument("--model", default=None,
                   help="modelo de embeddings (padrão: EMBEDDING_MODEL do .env, ou "
                        + ", ".join(f"{k}: {v}" for k, v in DEFAULT_MODELS.items()) + ")")
    p.add_argument("--ollama-url", default=None, help=f"servidor do Ollama (padrão {settings.ollama_url})")
    p.add_argument("--device", default=None, help="sentence-transformers: cpu, cuda... (padrão: automático)")
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument("--dry-run", action="store_true", help="só gera os trechos para revisão, sem embeddings")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("check", help="testa um PDF contra o catálogo e mostra cada verificação")
    p.add_argument("pdf", type=_pdf)
    p.add_argument("--id", help="compara só com este livro")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("list", help="lista o catálogo e o estado dos bancos")
    p.set_defaults(func=cmd_list)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (AppError, ValueError) as exc:
        print(f"Erro: {getattr(exc, 'message', exc)}", file=sys.stderr)
        return 2
