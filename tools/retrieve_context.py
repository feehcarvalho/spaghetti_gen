"""CLI para recuperar contexto da base de conhecimento local."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.knowledge.bootstrap_docs import bootstrap_docs
from app.knowledge.local_retriever import retrieve_context


DEFAULT_ROOT = REPO_ROOT / "data" / "knowledge_raw"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Recupera trechos relevantes da base local de conhecimento SPS."
    )
    parser.add_argument("query", help="Consulta textual.")
    parser.add_argument("--position", default=None, help="ID da posicao, exemplo: PMGS.P1.")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="Raiz da base local.")
    parser.add_argument("--top-k", type=int, default=8, help="Quantidade maxima de documentos.")
    parser.add_argument(
        "--bootstrap",
        action="store_true",
        help="Cria documentos iniciais ausentes antes de consultar.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.bootstrap:
        created = bootstrap_docs(args.root)
        print(f"Bootstrap: {len(created)} documento(s) criado(s).")

    context = retrieve_context(
        query=args.query,
        root_dir=str(args.root),
        position_id=args.position,
        top_k=args.top_k,
    )
    print(context)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
