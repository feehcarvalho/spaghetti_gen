"""Audit an OperationalAnalysis JSON before Excel generation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.analysis.language_normalizer import is_imperative_language
from app.analysis.quality_gate import validate_analysis_quality
from app.analysis.schema_compat import normalize_analysis_payload_for_current_schema
from app.schemas.analysis import OperationalAnalysis


def main() -> int:
    parser = argparse.ArgumentParser(description="Auditoria de qualidade de analysis.json SPS.")
    parser.add_argument("analysis_json", help="Caminho do JSON da analise")
    args = parser.parse_args()

    path = Path(args.analysis_json)
    if not path.exists():
        raise SystemExit(f"Arquivo nao encontrado: {path}")

    analysis = OperationalAnalysis.model_validate(
        normalize_analysis_payload_for_current_schema(json.loads(path.read_text(encoding="utf-8")))
    )
    gate = validate_analysis_quality(analysis, None, None)
    low_confidence = [step.numero for step in analysis.microetapas if step.confianca < 0.7 or step.baixa_confianca_motivo]
    missing_justification = [step.numero for step in analysis.microetapas if not step.justificativa_tecnica.strip()]
    non_imperative = [
        step.numero
        for step in analysis.microetapas
        if not is_imperative_language(step.instrucao_padrao or step.etapa_detalhada)
    ]
    classifications = {"AV": 0, "NAV": 0, "D": 0}
    for step in analysis.microetapas:
        classifications[step.classificacao] += 1

    print("Auditoria de qualidade SPS")
    print(f"arquivo: {path}")
    print(f"microetapas: {len(analysis.microetapas)}")
    print(f"classificacoes_qtd: {classifications}")
    print(f"tempo_total_s: {analysis.resumo_tempos.total_s}")
    print(f"tempos_s: AV={analysis.resumo_tempos.av_s} NAV={analysis.resumo_tempos.nav_s} D={analysis.resumo_tempos.d_s}")
    print(f"baixa_confianca: {low_confidence}")
    print(f"sem_justificativa: {missing_justification}")
    print(f"linguagem_fora_padrao: {non_imperative}")
    print(f"quality_gate_passou: {gate.passed}")
    print(f"pode_exportar_excel: {gate.can_export}")
    print(f"erros_criticos: {gate.critical_errors}")
    print(f"alertas: {gate.warnings}")
    return 0 if gate.can_export else 2


if __name__ == "__main__":
    raise SystemExit(main())
