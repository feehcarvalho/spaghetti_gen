"""
Testes para funções de utilidade de tempo.
"""

import pytest
from app.schemas.analysis import MicroStep, TimeSummary
from app.utils.time_utils import (
    apply_cumulative_times,
    calculate_time_summary,
    mmss_to_seconds,
    seconds_to_mmss,
)


class TestSecondsToMMss:
    """Testes para conversão de segundos para mm:ss."""
    
    def test_zero_seconds(self):
        """Testar conversão de 0 segundos."""
        assert seconds_to_mmss(0) == "00:00"
    
    def test_less_than_one_minute(self):
        """Testar conversão de segundos < 60."""
        assert seconds_to_mmss(30) == "00:30"
        assert seconds_to_mmss(45) == "00:45"
        assert seconds_to_mmss(59) == "00:59"
    
    def test_exactly_one_minute(self):
        """Testar conversão de exatamente 1 minuto."""
        assert seconds_to_mmss(60) == "01:00"
    
    def test_multiple_minutes(self):
        """Testar conversão de múltiplos minutos."""
        assert seconds_to_mmss(90) == "01:30"
        assert seconds_to_mmss(120) == "02:00"
        assert seconds_to_mmss(150) == "02:30"
        assert seconds_to_mmss(3661) == "61:01"  # 1h 1min 1s
    
    def test_float_seconds_rounding(self):
        """Testar arredondamento de segundos float."""
        assert seconds_to_mmss(2.5) == "00:02"
        assert seconds_to_mmss(2.7) == "00:03"
        assert seconds_to_mmss(90.5) == "01:30"
    
    def test_negative_seconds_raises(self):
        """Testar erro com segundos negativos."""
        with pytest.raises(ValueError, match="negativo"):
            seconds_to_mmss(-1)
        with pytest.raises(ValueError, match="negativo"):
            seconds_to_mmss(-10.5)


class TestMMssToSeconds:
    """Testes para conversão de mm:ss para segundos."""
    
    def test_zero_time(self):
        """Testar conversão de 00:00."""
        assert mmss_to_seconds("00:00") == 0.0
    
    def test_less_than_one_minute(self):
        """Testar conversão de mm:ss < 1 minuto."""
        assert mmss_to_seconds("00:30") == 30.0
        assert mmss_to_seconds("00:45") == 45.0
        assert mmss_to_seconds("00:59") == 59.0
    
    def test_exactly_one_minute(self):
        """Testar conversão de 01:00."""
        assert mmss_to_seconds("01:00") == 60.0
    
    def test_multiple_minutes(self):
        """Testar conversão de múltiplos minutos."""
        assert mmss_to_seconds("01:30") == 90.0
        assert mmss_to_seconds("02:00") == 120.0
        assert mmss_to_seconds("02:30") == 150.0
    
    def test_whitespace_handling(self):
        """Testar remoção de espaço em branco."""
        assert mmss_to_seconds("  01:30  ") == 90.0
    
    def test_invalid_format_raises(self):
        """Testar erro com formato inválido."""
        with pytest.raises(ValueError, match="Formato inválido"):
            mmss_to_seconds("1:30:00")  # HH:MM:SS
        with pytest.raises(ValueError, match="Formato inválido"):
            mmss_to_seconds("130")  # Sem dois pontos
        with pytest.raises(ValueError, match="Formato inválido"):
            mmss_to_seconds("01-30")  # Hífen em vez de dois-pontos
    
    def test_non_integer_raises(self):
        """Testar erro com não-inteiros."""
        with pytest.raises(ValueError, match="inteiros"):
            mmss_to_seconds("01:30.5")
        with pytest.raises(ValueError, match="inteiros"):
            mmss_to_seconds("1.5:30")
    
    def test_non_string_raises(self):
        """Testar erro com tipo não-string."""
        with pytest.raises(ValueError, match="string"):
            mmss_to_seconds(90)  # type: ignore
        with pytest.raises(ValueError, match="string"):
            mmss_to_seconds(None)  # type: ignore
    
    def test_negative_values_raises(self):
        """Testar erro com valores negativos."""
        with pytest.raises(ValueError, match="não podem ser negativos"):
            mmss_to_seconds("-01:30")
        with pytest.raises(ValueError, match="não podem ser negativos"):
            mmss_to_seconds("01:-30")
    
    def test_seconds_greater_or_equal_60_raises(self):
        """Testar erro quando segundos >= 60."""
        with pytest.raises(ValueError, match="menor que 60"):
            mmss_to_seconds("01:60")
        with pytest.raises(ValueError, match="menor que 60"):
            mmss_to_seconds("02:90")


class TestRoundTrip:
    """Testes de conversão ida e volta."""
    
    def test_seconds_to_mmss_to_seconds(self):
        """Testar conversão de segundos para mm:ss e volta."""
        original_values = [0, 30, 59, 60, 90, 120, 150, 300, 3661]
        for seconds in original_values:
            mmss = seconds_to_mmss(seconds)
            recovered = mmss_to_seconds(mmss)
            assert recovered == seconds, f"Mismatch for {seconds}s: {mmss} -> {recovered}"


class TestCalculateTimeSummary:
    """Testes para cálculo de resumo de tempos."""
    
    def create_microstep(self, numero, duracao, classificacao):
        """Criar um microstep simulado para testes."""
        class MockMicroStep:
            def __init__(self, numero, duracao, classificacao):
                self.numero = numero
                self.duracao_s = duracao
                self.classificacao = classificacao
        
        return MockMicroStep(numero, duracao, classificacao)
    
    def test_single_av_step(self):
        """Testar resumo com única etapa AV."""
        steps = [self.create_microstep(1, 10.0, "AV")]
        result = calculate_time_summary(steps)
        
        assert isinstance(result, TimeSummary)
        assert result["av_s"] == 10.0
        assert result["nav_s"] == 0.0
        assert result["d_s"] == 0.0
        assert result["total_s"] == 10.0
        assert result["av_percent"] == 100.0
        assert result["nav_percent"] == 0.0
        assert result["d_percent"] == 0.0
    
    def test_mixed_classification(self):
        """Testar resumo com mix de AV/NAV/D."""
        steps = [
            self.create_microstep(1, 95.0, "AV"),
            self.create_microstep(2, 18.5, "NAV"),
            self.create_microstep(3, 2.0, "D"),
        ]
        result = calculate_time_summary(steps)
        
        assert result["av_s"] == 95.0
        assert result["nav_s"] == 18.5
        assert result["d_s"] == 2.0
        assert result["total_s"] == 115.5
        assert abs(result["av_percent"] - 82.2) < 0.2
        assert abs(result["nav_percent"] - 16.0) < 0.2
        assert abs(result["d_percent"] - 1.7) < 0.2
    
    def test_percentuais_sum_100(self):
        """Validar que percentuais somam 100%."""
        steps = [
            self.create_microstep(1, 50.0, "AV"),
            self.create_microstep(2, 30.0, "NAV"),
            self.create_microstep(3, 20.0, "D"),
        ]
        result = calculate_time_summary(steps)
        
        total_percent = result["av_percent"] + result["nav_percent"] + result["d_percent"]
        assert abs(total_percent - 100.0) < 0.1
    
    def test_with_takt_time(self):
        """Testar cálculo de folga vs takt."""
        steps = [
            self.create_microstep(1, 95.0, "AV"),
            self.create_microstep(2, 18.5, "NAV"),
            self.create_microstep(3, 2.0, "D"),
        ]
        
        # Ciclo é 115.5s, Takt é 120s → folga é 4.5s
        result = calculate_time_summary(steps, takt_time_s=120.0)
        assert result["folga_vs_takt_s"] == 4.5
        
        # Ciclo é 115.5s, Takt é 110s → folga é -5.5s (over takt)
        result = calculate_time_summary(steps, takt_time_s=110.0)
        assert result["folga_vs_takt_s"] == -5.5
    
    def test_empty_list_raises(self):
        """Testar erro com lista vazia."""
        with pytest.raises(ValueError, match="não pode estar vazia"):
            calculate_time_summary([])
    
    def test_invalid_classification_raises(self):
        """Testar erro com classificação inválida."""
        steps = [self.create_microstep(1, 10.0, "INVALID")]
        with pytest.raises(ValueError, match="inválida"):
            calculate_time_summary(steps)
    
    def test_zero_total_returns_revisable_summary(self):
        """Permitir resumo zerado para analises que precisam de revisao manual."""
        steps = [self.create_microstep(1, 0.0, "NAV")]

        result = calculate_time_summary(steps, takt_time_s=120.0)

        assert result["total_s"] == 0.0
        assert result["av_percent"] == 0.0
        assert result["nav_percent"] == 0.0
        assert result["d_percent"] == 0.0
        assert result["folga_vs_takt_s"] is None
    
    def test_rounding_precision(self):
        """Testar arredondamento de resultados."""
        steps = [
            self.create_microstep(1, 33.333, "AV"),
            self.create_microstep(2, 33.334, "NAV"),
            self.create_microstep(3, 33.333, "D"),
        ]
        result = calculate_time_summary(steps)
        
        # Verificar que resultados são arredondados a 2 casas decimais
        assert len(str(result["av_s"]).split(".")[-1]) <= 2
        assert len(str(result["av_percent"]).split(".")[-1]) <= 1

    def test_apply_cumulative_times(self):
        """Validar tempo acumulado por microetapa."""
        steps = [
            MicroStep(
                numero=1,
                inicio_s=0.0,
                fim_s=5.0,
                duracao_s=5.0,
                inicio_formatado="00:00",
                fim_formatado="00:05",
                duracao_formatada="00:05",
                etapa_detalhada="Aplicar componente no produto",
                classificacao="AV",
                justificativa_tecnica="Transforma diretamente o produto",
                confianca=0.95,
            ),
            MicroStep(
                numero=2,
                inicio_s=5.0,
                fim_s=8.0,
                duracao_s=3.0,
                inicio_formatado="00:05",
                fim_formatado="00:08",
                duracao_formatada="00:03",
                etapa_detalhada="Apontar conclusao no sistema",
                classificacao="NAV",
                justificativa_tecnica="Necessario para rastreabilidade",
                confianca=0.9,
            ),
        ]

        updated = apply_cumulative_times(steps)

        assert updated[0].tempo_acumulado_s == 5.0
        assert updated[0].tempo_acumulado_formatado == "00:05"
        assert updated[1].tempo_acumulado_s == 8.0
        assert updated[1].tempo_acumulado_formatado == "00:08"
