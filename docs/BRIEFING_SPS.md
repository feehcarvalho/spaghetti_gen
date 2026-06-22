# Briefing Funcional - IA SPS Scania

## 🎯 Objetivo

Criar uma aplicação inteligente que atua como **analista de engenharia de processos especializado em Lean Manufacturing** para apoiar liderança, engenharia e análise operacional dentro da metodologia **SPS/Lean Manufacturing**.

A IA não é meramente uma descritora de vídeo, mas um **especialista em engenharia de processos** capaz de:
- Decompor operações complexas em microetapas observáveis
- Medir tempos com precisão
- Classificar cada etapa conforme agregação de valor (AV/NAV/D)
- Justificar técnicamente cada classificação
- Identificar padrões de desperdício (8 tipos Lean)
- Sugerir melhorias baseadas em SPS
- Preencher relatório padrão Scania
- Identificar oportunidades de balanceamento e takt time
- Mapear fluxo e spaghetti diagrams

## 📥 Entradas

A IA pode receber:

1. **Vídeo de processo**
   - MP4, AVI, MOV, MKV
   - Resolução mínima HD (1280x720)
   - Duração: típica 5–30 minutos
   - Múltiplos ângulos ou câmeras (futuro)

2. **Descrição textual de processo**
   - Narrativa detalhada de uma célula ou fluxo
   - Documentação de procedimento ou work instruction
   - Relatórios de análise anterior

3. **Dados estruturados JSON** (Fase 2+)
   - Etapas pré-extraídas com timestamps
   - Metadados: departamento, posto, takt, ciclo alvo

4. **Imagens estáticas**
   - Layout de célula ou spaghetti diagram
   - Fotos de setup ou abastecimento

## 📤 Saídas

### Primária: Análise SPS Estruturada (JSON)

```json
{
  "metadata": {
    "department": "string",
    "workstation": "string",
    "takt_time_s": float,
    "target_cycle_s": float,
    "confidence_score": float,
    "analysis_date": "ISO-8601",
    "analyst_notes": "string"
  },
  "summary": {
    "total_cycle_time_s": float,
    "av_time_s": float,
    "nav_time_s": float,
    "d_time_s": float,
    "slack_vs_takt_s": float,
    "av_percentage": float,
    "desperdice_count": int,
    "improvement_opportunities": int
  },
  "steps": [
    {
      "id": int,
      "description": "string",
      "start_s": float,
      "end_s": float,
      "duration_s": float,
      "classification": "AV | NAV | D",
      "justification": "string",
      "observation": "string",
      "confidence": float
    }
  ],
  "wastes": [
    {
      "step_id": int,
      "type": "string",  // "Espera", "Transporte", "Retrabalho", "Movimento", "Superprocessamento", "Inventário", "Superprodução", "Talento"
      "description": "string",
      "duration_s": float,
      "improvement_suggestion": "string",
      "priority": "Alta | Média | Baixa",
      "confidence": float
    }
  ],
  "improvements": [
    {
      "title": "string",
      "description": "string",
      "expected_time_saving_s": float,
      "estimated_investment": "Baixa | Média | Alta",
      "risk_level": "Baixo | Médio | Alto",
      "implementation_effort": "Baixo | Médio | Alto",
      "depends_on": ["string"]
    }
  ],
  "balance_analysis": {
    "bottleneck_step_id": int,
    "bottleneck_duration_s": float,
    "theoretical_capacity": float,
    "balance_opportunities": ["string"]
  },
  "spaghetti_observations": ["string"],
  "low_confidence_flags": ["string"]
}
```

### Secundária: Arquivo Excel Padrão Scania

Preenchimento automático em:
- **Aba ANÁLISE**: etapas, duração, classificação, justificativa
- **Aba MELHORIAS**: desperdícios, sugestões, prioridades
- **Aba Diagrama de Espaguete**: preservação + inserção de mapa gerado (se confirmado)
- **Abas Standard**: manutenção de fórmulas e dados existentes

### Terciária: Artefatos de Suporte

- Frames extraídos do vídeo com anotações
- Spaghetti diagram visual (layout com fluxo traçado)
- Matriz de balanceamento
- Histórico de análise em base de dados

## 🔄 Fluxo Geral

```
┌─────────────┐
│  Entrada    │ (vídeo, texto, JSON, imagem)
└──────┬──────┘
       │
┌──────▼──────┐
│  Extração   │ (decomposição em etapas + timestamps)
└──────┬──────┘
       │
┌──────▼──────┐
│ Classificação│ (AV/NAV/D + justificativa)
└──────┬──────┘
       │
┌──────▼──────┐
│  Análise    │ (desperdício, melhoria, balanceamento)
└──────┬──────┘
       │
┌──────▼──────┐
│  Preenchimento Excel
│  + Relatório │ (planilha padrão Scania)
└──────┬──────┘
       │
┌──────▼──────┐
│ Validação   │ (especialista gemba revisa)
│ & Follow-up │
└─────────────┘
```

## 🎓 Contexto SPS/Lean Manufacturing

### Conceitos-Chave

**Takt Time**: Ritmo de produção necessário para atender à demanda.
- Fórmula: `Takt = Tempo Disponível (s) / Demanda (unidades)`
- Exemplo: Se temos 8h úteis por dia (28.800s) e demanda de 240 peças, Takt = 120s/peça

**Ciclo Observado**: Tempo real medido do processo na produção.

**AV (Agregação de Valor)**:
- Etapa que transforma diretamente o produto
- Do ponto de vista do cliente
- Exemplos: montar, soldar, pintar, apertar, furar

**NAV (Não Agrega Valor)**:
- Necessário por processo, qualidade, segurança ou sistema
- Não transforma o produto, mas precisa existir
- Exemplos: apontar, conferir, inspecionar, abastecer, reposicionar

**D (Desperdício)**:
- Não agrega valor e não é necessário
- Pode ser eliminado imediatamente ou através de melhoria
- Exemplos: esperar, procurar, caminhar desnecessariamente, retrabalhar

**Os 8 Desperdícios (Muda)**:
1. **Espera**: Máquina/peça aguardando próxima ação
2. **Transporte**: Movimento de material desnecessário
3. **Retrabalho**: Correção de erro ou defeito
4. **Movimento**: Deslocamento do operador sem propósito
5. **Superprocessamento**: Mais do que necessário ou com tecnologia inadequada
6. **Inventário**: Estoque em excesso ou desnecessário
7. **Superprodução**: Produzir mais ou antes do necessário
8. **Talento Não Utilizado**: Não aproveitar conhecimento/criatividade do operador

### Trabalho Padronizado

O padrão SPS define:
- Sequência clara de etapas
- Takt time esperado
- Tempo de ciclo máximo
- Indicadores de qualidade
- Instruções visuais (work instruction)
- Follow-up periódico

## ⚠️ Limites e Restrições

### NÃO FAZER

❌ **Validação formal de mudanças de processo**
- A IA recomenda, mas não aprova
- Precisa de engenheiro/especialista SPS

❌ **Substituir liderança, especialista ou validação gemba**
- A análise é apoio, não decisão final
- Gemba é fonte de verdade

❌ **Inventar nomenclatura**
- Usar apenas termos padrão SPS/Scania
- Não criar categorias ou classificações não reconhecidas

❌ **Inferir o que não é observável**
- Se o vídeo não mostra, não afirmar
- Sinalizar baixa confiança quando apropriado

❌ **Responsabilizar operador sem evidência**
- Nunca culpar pessoa por desvios
- Focar em processo, não indivíduo

❌ **Aprovar alteração de método sem governança**
- Recomendações passam por comitê SPS
- Validação técnica é obrigatória

### SEMPRE

✅ **Sinalizar baixa confiança**
- Quando vídeo é de má qualidade
- Quando há ambiguidade sobre etapa
- Quando faltam dados para conclusão segura
- Campo `low_confidence_flags` no JSON

✅ **Manter rastreabilidade**
- Cada conclusão deve ter justificativa observável
- Timestamps são registrados
- Fontes de dados são claras

✅ **Respeitar governança SPS**
- Seguir padrão Scania
- Conformidade com processo de mudança
- Aprovação apropriada antes de implementação

## 📊 Casos de Uso Iniciais

### MVP: Análise Manual de Vídeo
1. Engenheiro fornece vídeo de célula
2. IA extrai frames e etapas
3. Especialista valida etapas
4. IA classifica AV/NAV/D
5. Relatório Excel é preenchido
6. Follow-up agendado

### Fase 2: Análise Automática
1. Vídeo enviado via API
2. Pipeline completo sem intervenção
3. Relatório gerado em minutos
4. Especialista valida saída

### Fase 3+: Integração Contínua
- Monitoramento de células
- Alertas de desvio de takt
- Rastreamento de melhorias
- Dashboard de KPIs

## 🔗 Relacionamento com Outras Ferramentas

- **Kanban System**: Takt time alimenta cálculos de kanban
- **5S**: Observações de layout informam spaghetti
- **PDCA**: Melhoria segue ciclo Plan-Do-Check-Act
- **SMED**: Análise de setup se detectada
- **Poka-Yoke**: Sugestões de à prova de erro
- **Kaizen**: Envolvimento de operador confirmado

## 📅 Próximos Passos

1. **Fase 1 (em progresso)**: Estrutura e documentação
2. **Fase 2**: Implementar schemas e mock manual
3. **Fase 3**: Preenchimento Excel automático
4. **Fase 4**: Integração com OpenAI API
5. **Fase 5+**: Recursos avançados

---

**Documento válido de: Maio/2026**  
**Última revisão: [data]**  
**Revisor: Engenharia de Processos**
