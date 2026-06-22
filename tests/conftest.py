"""
conftest.py - Configuração do Pytest para ia_sps_scania

Este arquivo configura fixtures e configurações globais para os testes.
"""

import pytest
import sys
from pathlib import Path

# Adicionar diretório raiz ao path para importações
sys.path.insert(0, str(Path(__file__).parent))


@pytest.fixture
def sample_metadata():
    """Fixture com metadados de análise válidos para testes."""
    from app.schemas.analysis import AnalysisMetadata
    
    return AnalysisMetadata(
        departamento="PAC",
        posto="P1.2",
        processo="Montagem Frontal",
        responsavel="Engenheiro de Processos",
        data_analise="2026-05-05",
        takt_time_s=120.0,
        ciclo_observado_s=115.5
    )


@pytest.fixture
def sample_microstep():
    """Fixture com microetapa válida para testes."""
    from app.schemas.analysis import MicroStep
    
    return MicroStep(
        numero=1,
        inicio_s=0.0,
        fim_s=2.5,
        duracao_s=2.5,
        inicio_formatado="00:00",
        fim_formatado="00:02",
        duracao_formatada="00:02",
        etapa_detalhada="Pegar parafuso do kit",
        classificacao="AV",
        justificativa_tecnica="Transformação direta do produto",
        confianca=0.95
    )


@pytest.fixture
def sample_time_summary():
    """Fixture com resumo de tempos válido para testes."""
    from app.schemas.analysis import TimeSummary
    
    return TimeSummary(
        av_s=95.0,
        nav_s=18.5,
        d_s=2.0,
        total_s=115.5,
        av_percent=82.2,
        nav_percent=16.0,
        d_percent=1.7,
        folga_vs_takt_s=4.5
    )


def pytest_configure(config):
    """Hook para configuração inicial do pytest."""
    print("\n" + "="*60)
    print("IA SPS Scania - Test Suite")
    print("="*60)
    print("Iniciando testes de validação...")
    print()


def pytest_collection_modifyitems(config, items):
    """Hook para modificar itens coletados (adicionar markers, etc)."""
    for item in items:
        if "test_" in item.nodeid:
            # Categorizar testes
            if "time_utils" in item.nodeid:
                item.add_marker(pytest.mark.unit)
            elif "schemas" in item.nodeid:
                item.add_marker(pytest.mark.schema)
