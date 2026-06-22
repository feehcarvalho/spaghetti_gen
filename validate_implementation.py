#!/usr/bin/env python
"""
validate_implementation.py

Script para validar a implementação dos schemas e utilitários SPS
sem depender de pytest estar instalado.

Execução:
    python validate_implementation.py
"""

import sys
from pathlib import Path

# Adicionar raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))


def print_section(title):
    """Imprimir seção formatada."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def test_imports():
    """Validar que todos os módulos podem ser importados."""
    print_section("1. VALIDAÇÃO DE IMPORTS")
    
    tests_passed = 0
    tests_failed = 0
    
    modules_to_test = [
        ("app.config", "Configurações"),
        ("app.utils.time_utils", "Utilidades de Tempo"),
        ("app.schemas.analysis", "Schemas de Análise"),
    ]
    
    for module_name, description in modules_to_test:
        try:
            __import__(module_name)
            print(f"  ✅ {description:40} ({module_name})")
            tests_passed += 1
        except ImportError as e:
            print(f"  ❌ {description:40} ERRO: {e}")
            tests_failed += 1
    
    return tests_passed, tests_failed


def test_time_utils():
    """Validar funções de utilidade de tempo."""
    print_section("2. VALIDAÇÃO DE TIME_UTILS")
    
    from app.utils.time_utils import seconds_to_mmss, mmss_to_seconds, calculate_time_summary
    
    tests_passed = 0
    tests_failed = 0
    
    # Test seconds_to_mmss
    test_cases = [
        (0, "00:00"),
        (30, "00:30"),
        (60, "01:00"),
        (90, "01:30"),
        (150, "02:30"),
    ]
    
    for seconds, expected in test_cases:
        result = seconds_to_mmss(seconds)
        if result == expected:
            print(f"  ✅ seconds_to_mmss({seconds:3}) = {result}")
            tests_passed += 1
        else:
            print(f"  ❌ seconds_to_mmss({seconds:3}) = {result}, esperado {expected}")
            tests_failed += 1
    
    # Test mmss_to_seconds
    test_cases_reverse = [
        ("00:00", 0.0),
        ("00:30", 30.0),
        ("01:00", 60.0),
        ("01:30", 90.0),
        ("02:30", 150.0),
    ]
    
    for mmss, expected in test_cases_reverse:
        result = mmss_to_seconds(mmss)
        if result == expected:
            print(f"  ✅ mmss_to_seconds('{mmss}') = {result}")
            tests_passed += 1
        else:
            print(f"  ❌ mmss_to_seconds('{mmss}') = {result}, esperado {expected}")
            tests_failed += 1
    
    # Test calculate_time_summary
    print("\n  Testando calculate_time_summary:")
    
    class MockStep:
        def __init__(self, duracao, classificacao):
            self.duracao_s = duracao
            self.classificacao = classificacao
    
    steps = [
        MockStep(95.0, "AV"),
        MockStep(18.5, "NAV"),
        MockStep(2.0, "D"),
    ]
    
    summary = calculate_time_summary(steps, takt_time_s=120.0)
    
    checks = [
        ("av_s", 95.0, summary["av_s"]),
        ("nav_s", 18.5, summary["nav_s"]),
        ("d_s", 2.0, summary["d_s"]),
        ("total_s", 115.5, summary["total_s"]),
        ("folga_vs_takt_s", 4.5, summary["folga_vs_takt_s"]),
    ]
    
    for field, expected, actual in checks:
        if abs(actual - expected) < 0.1:
            print(f"  ✅ {field:20} = {actual:8.2f} (esperado {expected})")
            tests_passed += 1
        else:
            print(f"  ❌ {field:20} = {actual:8.2f} (esperado {expected})")
            tests_failed += 1
    
    return tests_passed, tests_failed


def test_schemas():
    """Validar schemas Pydantic."""
    print_section("3. VALIDAÇÃO DE SCHEMAS")
    
    from app.schemas.analysis import (
        AnalysisMetadata,
        MicroStep,
        TimeSummary,
        SpaghettiPoint,
        SpaghettiMove,
        SpaghettiData,
        ImprovementSuggestion,
        OperationalAnalysis,
    )
    from pydantic import ValidationError
    
    tests_passed = 0
    tests_failed = 0
    
    # Test AnalysisMetadata
    print("\n  AnalysisMetadata:")
    try:
        metadata = AnalysisMetadata(
            departamento="PAC",
            posto="P1.2",
            processo="Montagem Frontal",
            responsavel="João Silva",
            data_analise="2026-05-05"
        )
        print(f"    ✅ Criação válida")
        tests_passed += 1
    except Exception as e:
        print(f"    ❌ Erro: {e}")
        tests_failed += 1
    
    # Test MicroStep - válido
    print("\n  MicroStep (válido):")
    try:
        step = MicroStep(
            numero=1,
            inicio_s=0.0,
            fim_s=2.5,
            duracao_s=2.5,
            inicio_formatado="00:00",
            fim_formatado="00:02",
            duracao_formatada="00:02",
            etapa_detalhada="Pegar parafuso do kit",
            classificacao="AV",
            justificativa_tecnica="Transformação direta",
            confianca=0.95
        )
        print(f"    ✅ Criação válida")
        tests_passed += 1
    except Exception as e:
        print(f"    ❌ Erro: {e}")
        tests_failed += 1
    
    # Test MicroStep - invalid (fim < inicio)
    print("\n  MicroStep (fim < inicio):")
    try:
        step = MicroStep(
            numero=1,
            inicio_s=5.0,
            fim_s=2.5,  # Inválido
            duracao_s=2.5,
            inicio_formatado="00:05",
            fim_formatado="00:02",
            duracao_formatada="00:02",
            etapa_detalhada="Etapa inválida",
            classificacao="AV",
            justificativa_tecnica="Justificativa",
            confianca=0.95
        )
        print(f"    ❌ Deveria ter lançado ValidationError")
        tests_failed += 1
    except ValidationError as e:
        print(f"    ✅ Corretamente rejeitado")
        tests_passed += 1
    
    # Test TimeSummary - válido
    print("\n  TimeSummary (válido):")
    try:
        summary = TimeSummary(
            av_s=95.0,
            nav_s=18.5,
            d_s=2.0,
            total_s=115.5,
            av_percent=82.2,
            nav_percent=16.0,
            d_percent=1.7
        )
        print(f"    ✅ Criação válida")
        tests_passed += 1
    except Exception as e:
        print(f"    ❌ Erro: {e}")
        tests_failed += 1
    
    # Test TimeSummary - invalid (percentuais != 100)
    print("\n  TimeSummary (percentuais != 100):")
    try:
        summary = TimeSummary(
            av_s=95.0,
            nav_s=18.5,
            d_s=2.0,
            total_s=115.5,
            av_percent=50.0,  # Inválido
            nav_percent=30.0,
            d_percent=15.0
        )
        print(f"    ❌ Deveria ter lançado ValidationError")
        tests_failed += 1
    except ValidationError as e:
        print(f"    ✅ Corretamente rejeitado")
        tests_passed += 1
    
    # Test SpaghettiData
    print("\n  SpaghettiData:")
    try:
        spaghetti = SpaghettiData()
        print(f"    ✅ Criação válida (vazio)")
        tests_passed += 1
    except Exception as e:
        print(f"    ❌ Erro: {e}")
        tests_failed += 1
    
    # Test ImprovementSuggestion
    print("\n  ImprovementSuggestion:")
    try:
        suggestion = ImprovementSuggestion(
            descricao_desperdicio="Operador procura parafuso",
            tipo_desperdicio="Movimento",
            sugestao_pratica="Implementar quadro visual 5S com compartimentos",
            prioridade="Alta"
        )
        print(f"    ✅ Criação válida")
        tests_passed += 1
    except Exception as e:
        print(f"    ❌ Erro: {e}")
        tests_failed += 1
    
    # Test OperationalAnalysis
    print("\n  OperationalAnalysis (válida):")
    try:
        analysis = OperationalAnalysis(
            metadata=metadata,
            microetapas=[step],
            resumo_tempos=summary
        )
        print(f"    ✅ Criação válida")
        tests_passed += 1
    except Exception as e:
        print(f"    ❌ Erro: {e}")
        tests_failed += 1
    
    return tests_passed, tests_failed


def main():
    """Executar todas as validações."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 10 + "IA SPS SCANIA - VALIDAÇÃO DE IMPLEMENTAÇÃO" + " " * 15 + "║")
    print("╚" + "=" * 68 + "╝")
    
    total_passed = 0
    total_failed = 0
    
    try:
        # Test 1: Imports
        passed, failed = test_imports()
        total_passed += passed
        total_failed += failed
        
        # Test 2: Time Utils
        passed, failed = test_time_utils()
        total_passed += passed
        total_failed += failed
        
        # Test 3: Schemas
        passed, failed = test_schemas()
        total_passed += passed
        total_failed += failed
        
    except Exception as e:
        print(f"\n❌ ERRO FATAL: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Summary
    print_section("RESUMO")
    print(f"  ✅ Testes Passados: {total_passed}")
    print(f"  ❌ Testes Falhados: {total_failed}")
    print(f"  📊 Total:           {total_passed + total_failed}")
    
    if total_failed == 0:
        print(f"\n  🎉 TODOS OS TESTES PASSARAM! 🎉")
        print_section("")
        return 0
    else:
        print(f"\n  ⚠️  {total_failed} teste(s) falhado(s)")
        print_section("")
        return 1


if __name__ == "__main__":
    sys.exit(main())
