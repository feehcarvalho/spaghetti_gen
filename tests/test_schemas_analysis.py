"""
Testes para schemas Pydantic de análise SPS.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError
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


class TestAnalysisMetadata:
    """Testes para schema AnalysisMetadata."""
    
    def test_valid_metadata(self):
        """Testar criação de metadados válidos."""
        metadata = AnalysisMetadata(
            departamento="PAC",
            posto="P1.2",
            processo="Montagem Frontal",
            responsavel="João Silva",
            data_analise="2026-05-05"
        )
        assert metadata.empresa == "Scania"
        assert metadata.departamento == "PAC"
        assert metadata.posto == "P1.2"
    
    def test_invalid_data_format_raises(self):
        """Testar erro com data em formato inválido."""
        with pytest.raises(ValidationError, match="ISO-8601"):
            AnalysisMetadata(
                departamento="PAC",
                posto="P1.2",
                processo="Montagem",
                responsavel="João",
                data_analise="05/05/2026"  # Formato inválido
            )
    
    def test_optional_fields(self):
        """Testar campos opcionais."""
        metadata = AnalysisMetadata(
            departamento="PAC",
            posto="P1.2",
            processo="Montagem Frontal",
            responsavel="João Silva",
            data_analise="2026-05-05",
            linha=None,
            bloco=None,
            takt_time_s=None
        )
        assert metadata.linha is None
        assert metadata.takt_time_s is None


class TestMicroStep:
    """Testes para schema MicroStep."""
    
    def test_valid_av_step(self):
        """Testar criação de microetapa AV válida."""
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
            justificativa_tecnica="Transformação direta do produto",
            confianca=0.95
        )
        assert step.numero == 1
        assert step.classificacao == "AV"
        assert step.confianca == 0.95
    
    def test_fim_less_than_inicio_raises(self):
        """Testar erro quando fim_s < inicio_s."""
        with pytest.raises(ValidationError, match="não pode ser menor"):
            MicroStep(
                numero=1,
                inicio_s=5.0,
                fim_s=2.5,  # Menor que inicio_s
                duracao_s=2.5,
                inicio_formatado="00:05",
                fim_formatado="00:02",
                duracao_formatada="00:02",
                etapa_detalhada="Etapa inválida",
                classificacao="AV",
                justificativa_tecnica="Justificativa",
                confianca=0.95
            )
    
    def test_duracao_mismatch_raises(self):
        """Testar erro quando duracao_s não corresponde a fim - inicio."""
        with pytest.raises(ValidationError, match="deve ser aproximadamente"):
            MicroStep(
                numero=1,
                inicio_s=0.0,
                fim_s=2.5,
                duracao_s=5.0,  # Não corresponde a 2.5 - 0.0
                inicio_formatado="00:00",
                fim_formatado="00:02",
                duracao_formatada="00:05",
                etapa_detalhada="Etapa inválida",
                classificacao="AV",
                justificativa_tecnica="Justificativa",
                confianca=0.95
            )
    
    def test_invalid_classification_raises(self):
        """Testar erro com classificação inválida."""
        with pytest.raises(ValidationError, match="AV"):
            MicroStep(
                numero=1,
                inicio_s=0.0,
                fim_s=2.5,
                duracao_s=2.5,
                inicio_formatado="00:00",
                fim_formatado="00:02",
                duracao_formatada="00:02",
                etapa_detalhada="Etapa válida",
                classificacao="INVALID",  # Classificação inválida
                justificativa_tecnica="Justificativa",
                confianca=0.95
            )
    
    def test_low_confidence_sets_default_warning_reason(self):
        """Testar que confiança < 0.7 gera aviso sem bloquear a criacao do modelo."""
        step = MicroStep(
            numero=1,
            inicio_s=0.0,
            fim_s=2.5,
            duracao_s=2.5,
            inicio_formatado="00:00",
            fim_formatado="00:02",
            duracao_formatada="00:02",
            etapa_detalhada="Etapa com baixa confiança",
            classificacao="AV",
            justificativa_tecnica="Justificativa",
            confianca=0.65,
        )
        assert step.confianca == 0.65
        assert step.baixa_confianca_motivo is not None
        assert "confiança abaixo do limite recomendado" in step.baixa_confianca_motivo.lower()
        assert step.requer_validacao_gemba is True
    
    def test_confianca_out_of_range_raises(self):
        """Testar erro quando confiança fora de [0, 1]."""
        with pytest.raises(ValidationError, match="greater than or equal"):
            MicroStep(
                numero=1,
                inicio_s=0.0,
                fim_s=2.5,
                duracao_s=2.5,
                inicio_formatado="00:00",
                fim_formatado="00:02",
                duracao_formatada="00:02",
                etapa_detalhada="Etapa válida",
                classificacao="AV",
                justificativa_tecnica="Justificativa",
                confianca=-0.5  # Inválido
            )


class TestTimeSummary:
    """Testes para schema TimeSummary."""
    
    def test_valid_time_summary(self):
        """Testar resumo de tempos válido."""
        summary = TimeSummary(
            av_s=95.0,
            nav_s=18.5,
            d_s=2.0,
            total_s=115.5,
            av_percent=82.2,
            nav_percent=16.0,
            d_percent=1.7,
            folga_vs_takt_s=4.5
        )
        assert summary.total_s == 115.5
        assert summary.av_percent == 82.2
    
    def test_percentuais_not_100_raises(self):
        """Testar erro quando percentuais não somam 100%."""
        with pytest.raises(ValidationError, match="100%"):
            TimeSummary(
                av_s=95.0,
                nav_s=18.5,
                d_s=2.0,
                total_s=115.5,
                av_percent=50.0,  # Soma não é 100%
                nav_percent=30.0,
                d_percent=15.0,
                folga_vs_takt_s=4.5
            )
    
    def test_negative_time_raises(self):
        """Testar erro com tempo negativo."""
        with pytest.raises(ValidationError):
            TimeSummary(
                av_s=-95.0,  # Negativo
                nav_s=18.5,
                d_s=2.0,
                total_s=115.5,
                av_percent=82.2,
                nav_percent=16.0,
                d_percent=1.7
            )
    
    def test_percentual_out_of_range_raises(self):
        """Testar erro quando percentual fora de [0, 100]."""
        with pytest.raises(ValidationError):
            TimeSummary(
                av_s=95.0,
                nav_s=18.5,
                d_s=2.0,
                total_s=115.5,
                av_percent=150.0,  # Inválido
                nav_percent=16.0,
                d_percent=1.7
            )


class TestSpaghettiData:
    """Testes para schema SpaghettiData."""
    
    def test_empty_spaghetti_valid(self):
        """Testar dados spaghetti vazios são válidos."""
        spaghetti = SpaghettiData()
        assert len(spaghetti.pontos) == 0
        assert len(spaghetti.movimentos) == 0
    
    def test_with_points_and_moves(self):
        """Testar dados spaghetti com pontos e movimentos."""
        point = SpaghettiPoint(
            nome="Kit",
            x=0.0,
            y=0.0,
            descricao="Abastecimento"
        )
        move = SpaghettiMove(
            ordem=1,
            origem="Kit",
            destino="P1",
            distancia_m=1.5
        )
        spaghetti = SpaghettiData(
            pontos=[point],
            movimentos=[move],
            distancia_total_m=1.5
        )
        assert len(spaghetti.pontos) == 1
        assert len(spaghetti.movimentos) == 1


class TestImprovementSuggestion:
    """Testes para schema ImprovementSuggestion."""
    
    def test_valid_improvement_suggestion(self):
        """Testar sugestão de melhoria válida."""
        suggestion = ImprovementSuggestion(
            descricao_desperdicio="Operador procura parafuso desorganizado",
            tipo_desperdicio="Movimento",
            sugestao_pratica="Implementar quadro visual 5S com compartimentos etiquetados",
            prioridade="Alta",
            requer_validacao_gemba=True
        )
        assert suggestion.prioridade == "Alta"
        assert suggestion.requer_validacao_gemba is True
    
    def test_invalid_priority_raises(self):
        """Testar erro com prioridade inválida."""
        with pytest.raises(ValidationError):
            ImprovementSuggestion(
                descricao_desperdicio="Descrição",
                tipo_desperdicio="Movimento",
                sugestao_pratica="Sugestão muito específica e detalhada",
                prioridade="Urgente"  # Inválido
            )


class TestOperationalAnalysis:
    """Testes para schema OperationalAnalysis (análise completa)."""
    
    def test_valid_operational_analysis(self):
        """Testar análise operacional completa válida."""
        metadata = AnalysisMetadata(
            departamento="PAC",
            posto="P1.2",
            processo="Montagem Frontal",
            responsavel="João Silva",
            data_analise="2026-05-05"
        )
        
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
            justificativa_tecnica="Transformação direta do produto",
            confianca=0.95
        )
        
        summary = TimeSummary(
            av_s=2.5,
            nav_s=0.0,
            d_s=0.0,
            total_s=2.5,
            av_percent=100.0,
            nav_percent=0.0,
            d_percent=0.0
        )
        
        analysis = OperationalAnalysis(
            metadata=metadata,
            microetapas=[step],
            resumo_tempos=summary
        )
        
        assert analysis.metadata.departamento == "PAC"
        assert len(analysis.microetapas) == 1
        assert analysis.resumo_tempos.av_s == 2.5
    
    def test_empty_microetapas_raises(self):
        """Testar erro quando lista de microetapas está vazia."""
        metadata = AnalysisMetadata(
            departamento="PAC",
            posto="P1.2",
            processo="Montagem Frontal",
            responsavel="João Silva",
            data_analise="2026-05-05"
        )
        
        summary = TimeSummary(
            av_s=0.0,
            nav_s=0.0,
            d_s=0.0,
            total_s=0.0,
            av_percent=0.0,
            nav_percent=0.0,
            d_percent=0.0
        )
        
        with pytest.raises(ValidationError, match="at least 1 item"):
            OperationalAnalysis(
                metadata=metadata,
                microetapas=[],  # Vazio
                resumo_tempos=summary
            )


class TestValidationExample:
    """Testes de exemplo de validação completa."""
    
    def test_realistic_analysis_scenario(self):
        """Testar cenário realista de análise completa."""
        # Criar análise realista de Montagem Frontal
        metadata = AnalysisMetadata(
            departamento="PAC",
            linha="L1",
            bloco="B1",
            posto="P1.2",
            processo="Montagem Frontal",
            responsavel="Engenheiro de Processos",
            data_analise="2026-05-05",
            takt_time_s=120.0,
            ciclo_observado_s=115.5,
            fonte_video="video_montagem_001.mp4"
        )
        
        steps = [
            MicroStep(
                numero=1,
                inicio_s=0.0,
                fim_s=2.5,
                duracao_s=2.5,
                inicio_formatado="00:00",
                fim_formatado="00:02",
                duracao_formatada="00:02",
                etapa_detalhada="Pegar parafuso do kit",
                classificacao="AV",
                justificativa_tecnica="Montagem de componente, transformação direta",
                ferramenta_observacao="Manual",
                confianca=0.95
            ),
            MicroStep(
                numero=2,
                inicio_s=2.5,
                fim_s=5.0,
                duracao_s=2.5,
                inicio_formatado="00:02",
                fim_formatado="00:05",
                duracao_formatada="00:02",
                etapa_detalhada="Apertar parafuso com chave pneumática",
                classificacao="AV",
                justificativa_tecnica="Montagem de componente, transformação direta",
                ferramenta_observacao="Chave Pneumática",
                confianca=0.98
            ),
            MicroStep(
                numero=3,
                inicio_s=5.0,
                fim_s=7.0,
                duracao_s=2.0,
                inicio_formatado="00:05",
                fim_formatado="00:07",
                duracao_formatada="00:02",
                etapa_detalhada="Apontar conclusão no MES",
                classificacao="NAV",
                justificativa_tecnica="Necessário por rastreabilidade",
                confianca=0.90
            ),
        ]
        
        summary = TimeSummary(
            av_s=5.0,
            nav_s=2.0,
            d_s=0.0,
            total_s=7.0,
            av_percent=71.4,
            nav_percent=28.6,
            d_percent=0.0,
            folga_vs_takt_s=113.0
        )
        
        analysis = OperationalAnalysis(
            metadata=metadata,
            microetapas=steps,
            resumo_tempos=summary,
            recomendacoes_gerais=[
                "Processo está abaixo de takt, operador experiente",
                "Sem desperdícios identificados"
            ]
        )
        
        # Validações
        assert analysis.metadata.processo == "Montagem Frontal"
        assert len(analysis.microetapas) == 3
        assert analysis.resumo_tempos.av_percent > 0
        assert analysis.resumo_tempos.d_s == 0.0
