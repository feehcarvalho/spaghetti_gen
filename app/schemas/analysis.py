"""Schemas Pydantic centrais para a analise operacional SPS."""

from __future__ import annotations

from datetime import datetime
from math import isclose
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


DEFAULT_CAUSA_NAO_CONCLUSIVA = (
    "Causa nao conclusiva pelo video/entrada analisada; requer validacao no gemba."
)


class AnalysisMetadata(BaseModel):
    """Metadados que identificam o contexto da analise."""

    model_config = ConfigDict(extra="forbid")

    empresa: str = "Scania"
    departamento: str
    linha: str | None = None
    bloco: str | None = None
    posto: str
    processo: str
    responsavel: str
    data_analise: str
    takt_time_s: float | None = Field(default=None, ge=0)
    ciclo_observado_s: float | None = Field(default=None, ge=0)
    fonte_video: str | None = None
    observacoes_gerais: str | None = None
    inicio_esperado_processo: str | None = None
    fim_esperado_processo: str | None = None
    foco_do_processo: str | None = None
    usuario_login: str | None = None
    usuario_nome: str | None = None
    usuario_area: str | None = None
    aceite_responsabilidade_em: str | None = None

    @field_validator("data_analise")
    @classmethod
    def validate_data_analise(cls, value: str) -> str:
        try:
            datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("data_analise deve estar em formato ISO-8601") from exc
        return value


class MicroStep(BaseModel):
    """Microetapa observada no video/processo."""

    model_config = ConfigDict(extra="forbid")

    numero: int = Field(..., ge=1)
    inicio_s: float = Field(..., ge=0)
    fim_s: float = Field(..., ge=0)
    duracao_s: float = Field(..., ge=0)
    inicio_formatado: str
    fim_formatado: str
    duracao_formatada: str
    tempo_acumulado_s: float | None = Field(default=None, ge=0)
    tempo_acumulado_formatado: str | None = None
    instrucao_operacional: str | None = None
    etapa_detalhada: str
    descricao_tecnica_detalhada: str | None = None
    instrucao_padrao: str | None = None
    observacao_visual_bruta: str | None = None
    evidencia_observavel: str | None = None
    interpretacao_de_processo: str | None = None
    objetivo_da_etapa: str | None = None
    classificacao: Literal["AV", "NAV", "D"]
    justificativa_tecnica: str
    ferramenta_observacao: str | None = None
    peca_componente: str | None = None
    dispositivo: str | None = None
    sistema: str | None = None
    tipo_movimento: str | None = None
    tipo_desperdicio: str | None = None
    local_inicio: str | None = None
    local_fim: str | None = None
    lado: str | None = None
    eixo: str | None = None
    variante: str | None = None
    quantidade: str | None = None
    quantidade_confirmada_por: str | None = None
    evidencia_visual: str | None = None
    memoria_utilizada: list[str] = Field(default_factory=list)
    nomenclatura_utilizada: list[str] = Field(default_factory=list)
    confianca: float = Field(..., ge=0, le=1)
    baixa_confianca_motivo: str | None = None
    requer_validacao_gemba: bool = False

    @field_validator("etapa_detalhada", "justificativa_tecnica")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("campo textual obrigatorio nao pode ser vazio")
        return text

    @model_validator(mode="after")
    def validate_time_consistency(self) -> MicroStep:
        if self.fim_s < self.inicio_s:
            raise ValueError("fim_s não pode ser menor que inicio_s")

        expected_duration = self.fim_s - self.inicio_s
        if not isclose(self.duracao_s, expected_duration, abs_tol=0.1):
            raise ValueError("duracao_s deve ser aproximadamente fim_s - inicio_s")

        if self.confianca < 0.7:
            self.requer_validacao_gemba = True
            if not self.baixa_confianca_motivo:
                self.baixa_confianca_motivo = (
                    "Aviso: confiança abaixo do limite recomendado. Validar esta etapa no gemba antes de decisão definitiva."
                )

        if self.descricao_tecnica_detalhada is None:
            self.descricao_tecnica_detalhada = self.etapa_detalhada
        if self.instrucao_operacional is None:
            self.instrucao_operacional = self.instrucao_padrao or self.descricao_tecnica_detalhada
        if self.instrucao_padrao is None:
            self.instrucao_padrao = self.descricao_tecnica_detalhada
        if self.observacao_visual_bruta is None:
            self.observacao_visual_bruta = self.evidencia_visual or self.evidencia_observavel
        if self.evidencia_observavel is None and self.evidencia_visual:
            self.evidencia_observavel = self.evidencia_visual
        if self.interpretacao_de_processo is None:
            self.interpretacao_de_processo = self.descricao_tecnica_detalhada
        if self.confianca < 0.7 or self.baixa_confianca_motivo:
            self.requer_validacao_gemba = True

        return self


class TimeSummary(BaseModel):
    """Resumo agregado dos tempos por classificacao."""

    model_config = ConfigDict(extra="forbid")

    av_s: float = Field(..., ge=0)
    nav_s: float = Field(..., ge=0)
    d_s: float = Field(..., ge=0)
    total_s: float = Field(..., ge=0)
    av_percent: float = Field(..., ge=0, le=100)
    nav_percent: float = Field(..., ge=0, le=100)
    d_percent: float = Field(..., ge=0, le=100)
    folga_vs_takt_s: float | None = None

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    @model_validator(mode="after")
    def validate_percent_total(self) -> TimeSummary:
        percent_total = self.av_percent + self.nav_percent + self.d_percent
        all_zero = (
            self.total_s == 0
            and self.av_percent == 0
            and self.nav_percent == 0
            and self.d_percent == 0
        )

        if not all_zero and not isclose(percent_total, 100.0, abs_tol=0.2):
            raise ValueError("Percentuais devem somar 100%")

        return self


class SpaghettiPoint(BaseModel):
    """Ponto de referencia no layout do spaghetti diagram."""

    model_config = ConfigDict(extra="forbid")

    nome: str
    x: float | None = None
    y: float | None = None
    descricao: str | None = None


class SpaghettiMove(BaseModel):
    """Movimento entre dois pontos do spaghetti diagram."""

    model_config = ConfigDict(extra="forbid")

    ordem: int = Field(..., ge=1)
    origem: str
    destino: str
    passos_estimados: int | None = Field(default=None, ge=0)
    distancia_m: float | None = Field(default=None, ge=0)
    inicio_s: float | None = Field(default=None, ge=0)
    fim_s: float | None = Field(default=None, ge=0)
    motivo: str | None = None
    microetapa_numero: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_time_order(self) -> SpaghettiMove:
        if self.inicio_s is not None and self.fim_s is not None and self.fim_s < self.inicio_s:
            raise ValueError("fim_s não pode ser menor que inicio_s")
        return self


class SpaghettiData(BaseModel):
    """Dados estruturados para desenho e calculo de spaghetti."""

    model_config = ConfigDict(extra="forbid")

    layout_id: str | None = None
    pontos: list[SpaghettiPoint] = Field(default_factory=list)
    movimentos: list[SpaghettiMove] = Field(default_factory=list)
    total_passos_estimados: int | None = Field(default=None, ge=0)
    distancia_total_m: float | None = Field(default=None, ge=0)


class ImprovementSuggestion(BaseModel):
    """Sugestao de melhoria derivada da analise."""

    model_config = ConfigDict(extra="forbid")

    microetapa_numero: int | None = Field(default=None, ge=1)
    inicio_formatado: str | None = None
    fim_formatado: str | None = None
    duracao_s: float | None = Field(default=None, ge=0)
    descricao_desperdicio: str
    tipo_desperdicio: str
    causa_observavel: str = DEFAULT_CAUSA_NAO_CONCLUSIVA
    sugestao_pratica: str
    impacto_esperado: str | None = None
    prioridade: Literal["Baixa", "Média", "Alta"]
    requer_validacao_gemba: bool = True

    @field_validator("descricao_desperdicio", "tipo_desperdicio", "causa_observavel", "sugestao_pratica")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("campo textual obrigatorio nao pode ser vazio")
        return text


class OperationalAnalysis(BaseModel):
    """Analise operacional completa, validada e pronta para exportacao."""

    model_config = ConfigDict(extra="forbid")

    metadata: AnalysisMetadata
    microetapas: list[MicroStep] = Field(..., min_length=1)
    resumo_tempos: TimeSummary
    spaghetti: SpaghettiData | None = None
    melhorias: list[ImprovementSuggestion] = Field(default_factory=list)
    recomendacoes_gerais: list[str] = Field(default_factory=list)
    alertas_validacao: list[str] = Field(default_factory=list)
    alertas_validacao_sps: list[dict[str, Any]] = Field(default_factory=list)
    roteiro_operacional: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_d_steps_have_improvement_or_alert(self) -> OperationalAnalysis:
        d_step_numbers = {
            step.numero
            for step in self.microetapas
            if step.classificacao == "D"
        }
        if not d_step_numbers:
            return self

        improved_step_numbers = {
            suggestion.microetapa_numero
            for suggestion in self.melhorias
            if suggestion.microetapa_numero is not None
        }

        for step_number in sorted(d_step_numbers - improved_step_numbers):
            message = (
                f"Microetapa {step_number} classificada como D sem sugestao de melhoria "
                "vinculada; requer validacao no gemba/SPS."
            )
            if message not in self.alertas_validacao:
                self.alertas_validacao.append(message)

        return self
