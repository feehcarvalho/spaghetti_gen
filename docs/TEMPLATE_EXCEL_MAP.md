# Mapeamento da Planilha Excel Padrão Scania

## 📋 Visão Geral

O arquivo de saída da análise SPS deve preencher a planilha padrão Scania de análise de processo:

**Localização do Arquivo Template**:
```
data/templates/PMGS_P1_Analise_SPS_CORRIGIDA_2026-03-18.xlsx
```

A aplicação deve:
- ✅ Preencher automaticamente campos de análise
- ✅ Preservar fórmulas existentes
- ✅ Nunca apagar dados padrão da Scania
- ✅ Permitir múltiplas análises no mesmo arquivo
- ✅ Manter rastreabilidade de atualizações

---

## 📑 Abas da Planilha

### 1. Aba "ANÁLISE"

Esta é a aba principal onde os dados da análise são preenchidos.

#### Cabeçalho (Linhas 1–5)

| Célula | Campo | Tipo | Descrição | Exemplo |
|:---:|---|---|---|---|
| A1 | Título | Text | Título geral da análise | "Análise de Processo - Posto P1.2" |
| A3:B3 | Departamento | Text | Sigla ou nome | "PAC" ou "Seção de Montagem" |
| D3:E3 | Emitido por | Text | Nome do analista / IA | "IA SPS Bot" ou "João Silva" |
| G3:H3 | Data | Date | Data da análise | "2026-05-05" |
| A4:B4 | Posto | Text | Código do posto de trabalho | "P1.2" ou "Montagem Chassis" |
| D4:E4 | Processo | Text | Nome do processo | "Montagem Frontal" |
| G4:H4 | Takt | Number | Takt time em segundos | 120 (s) |
| A5:B5 | Ciclo observado | Number | Tempo de ciclo medido (s) | 115.5 (s) |
| D5:E5 | AV | Number | Tempo total em AV (s) | 95.0 (s) |
| F5:G5 | NAV | Number | Tempo total em NAV (s) | 18.5 (s) |
| H5:I5 | D | Number | Tempo total em D (s) | 2.0 (s) |

**Fórmulas Sugeridas** (se não existirem):
- D5:E5 (AV) = `SUMIF(tabela_etapas, "AV", duração_coluna)`
- F5:G5 (NAV) = `SUMIF(tabela_etapas, "NAV", duração_coluna)`
- H5:I5 (D) = `SUMIF(tabela_etapas, "D", duração_coluna)`

#### Tabela de Etapas (A partir da linha 6)

**Linha 6: Cabeçalho da Tabela**
```
A6: Nº
B6: Etapa detalhada
C6: Início (s)
D6: Fim (s)
E6: Duração (s)
F6: Duração (%)
G6: Classificação
H6: Justificativa técnica
I6: Ferramenta / observação
```

**Linhas 7 em diante: Dados das Etapas**

| Coluna | Campo | Tipo | Descrição |
|:---:|---|---|---|
| A | Nº | Integer | Sequência: 1, 2, 3, ... |
| B | Etapa detalhada | Text | Descrição clara e observável da ação |
| C | Início (s) | Number | Timestamp de início em segundos (ex: 0.0, 12.5, 45.3) |
| D | Fim (s) | Number | Timestamp de fim em segundos |
| E | Duração (s) | Number | Duração = Fim - Início |
| F | Duração (%) | Percentage | % = Duração / Ciclo Total |
| G | Classificação | Text | "AV" ou "NAV" ou "D" |
| H | Justificativa técnica | Text | Por que AV/NAV/D (1–2 frases) |
| I | Ferramenta / observação | Text | Ferramenta usada ou observação especial |

**Exemplo de Preenchimento**:
```
Nº  | Etapa detalhada                              | Início | Fim  | Dur. (s) | Dur. (%) | Class | Justificativa                    | Ferramenta
1   | Pegar parafuso do kit                        | 0.0    | 2.5  | 2.5      | 2.2%     | AV    | Montagem de componente           | Manual
2   | Posicionar parafuso no ponto de encaixe      | 2.5    | 5.0  | 2.5      | 2.2%     | AV    | Montagem de componente           | Manual
3   | Apertar com chave pneumática                 | 5.0    | 8.0  | 3.0      | 2.6%     | AV    | Fixação, transforma produto      | Chave Pneumática
4   | Apontar conclusão no sistema                 | 8.0    | 10.0 | 2.0      | 1.7%     | NAV   | Necessário para rastreabilidade  | Terminal MES
5   | Procurar próximo parafuso (desorganizado)    | 10.0   | 12.5 | 2.5      | 2.2%     | D     | Poderia ser eliminado com 5S     | -
```

**Fórmulas Recomendadas** (nas linhas de dados):
- Coluna E (Duração em s): `=D7-C7`
- Coluna F (Duração em %): `=E7/$E$5` (referência absoluta ao total)

**Validações**:
- Coluna G: List de "AV", "NAV", "D" (Data Validation)
- Coluna C, D, E: Number format com 1 casa decimal
- Coluna F: Percentage format com 1 casa decimal

---

### 2. Aba "MELHORIAS"

Contém análise de desperdícios e sugestões de melhoria.

#### Cabeçalho (Linhas 1–5)

| Célula | Campo | Tipo | Descrição |
|:---:|---|---|---|
| A1 | Título | Text | "MELHORIAS E DESPERDÍCIOS" |
| A3:B3 | Ciclo observado | Number | Mesmo valor da aba ANÁLISE (A5:B5) |
| D3:E3 | Takt | Number | Mesmo valor da aba ANÁLISE (G4:H4) |
| G3:H3 | Folga vs Takt | Number | = Takt - Ciclo (negativo = over takt) |
| A4:B4 | Tempo D | Number | Tempo total de desperdício (soma de D) |
| D4:E4 | Leitura | Text | "Sobre capacidade" ou "Desbalanceada" ou "Otimizada" |

**Fórmula Sugerida**:
- G3:H3 (Folga): `=G_takt - A_ciclo` (referência da aba anterior)
- A4:B4 (Tempo D): `=ANÁLISE!H5:I5` (referência ao total D da aba ANÁLISE)

#### Tabela de Desperdícios (A partir da linha 6)

**Linha 6: Cabeçalho**
```
A6: Etapa
B6: Início (s)
C6: Fim (s)
D6: Duração (s)
E6: Descrição do desperdício
F6: Tipo
G6: Sugestão prática de melhoria
H6: Prioridade
```

**Linhas 7 em diante: Dados de Desperdício**

| Coluna | Campo | Tipo | Descrição |
|:---:|---|---|---|
| A | Etapa | Text | Descrição breve da etapa (ou nº referência) |
| B | Início (s) | Number | Timestamp de início |
| C | Fim (s) | Number | Timestamp de fim |
| D | Duração (s) | Number | Duração do desperdício |
| E | Descrição do desperdício | Text | O que está sendo desperdiçado (2–3 frases) |
| F | Tipo | Text | Um dos 8 tipos: Espera, Transporte, Retrabalho, Movimento, Superprocessamento, Inventário, Superprodução, Talento |
| G | Sugestão prática de melhoria | Text | O que fazer para eliminar (concreta, não teórica) |
| H | Prioridade | Text | "Alta" / "Média" / "Baixa" |

**Exemplo de Preenchimento**:
```
Etapa | Início | Fim | Dur. (s) | Descrição | Tipo | Sugestão | Prioridade
5     | 10.0   | 12.5| 2.5      | Procura de parafuso desorganizado | Movimento | Implementar quadro visual 5S para parafusos | Alta
7     | 18.0   | 22.0| 4.0      | Aguarda aval do supervisor | Espera | Utilizar kanban pull automático | Média
10    | 35.0   | 40.0| 5.0      | Retrabalho de junta mal executada | Retrabalho | Treinamento de tecnica + poka-yoke | Alta
```

#### Recomendações Gerais (A partir da linha 14)

A partir de linha 14, é permitido adicionar texto livre com recomendações gerais da análise.

| Linha | Conteúdo | Descrição |
|:---:|---|---|
| 14 | "RECOMENDAÇÕES GERAIS:" | Cabeçalho |
| 15+ | Texto livre | Observações de balanceamento, takt time, padrões SPS a implementar, etc. |

**Exemplo**:
```
15: • Ciclo está 4% acima do takt time (115.5s vs 120s). Implementar sugestões de melhoria pode recuperar 5s.
16: • Operador tem baixa confiança nos tempos de aparafusamento. Validar técnica e poka-yoke.
17: • Linha desbalanceada: próximo posto está com 95s. Rebalancear após implementação.
18: • Agendar follow-up em 2 semanas para validação.
```

---

### 3. Aba "Diagrama de Espaguete"

Esta aba é preservada conforme existe na planilha padrão.

**O que preservar**:
- ✅ Layout visual existente
- ✅ Imagens e gráficos padrão
- ✅ Anotações manuais

**O que pode ser adicionado** (MVP):
- Inserir imagem gerada do mapa de fluxo (sem quebrar layout)
- Preencher tabela de pontos/passos se layout permitir
- Nunca apagar elementos originais

**Implementação Fase 3+**:
- Extrair layout real da célula
- Gerar spaghetti diagram com fluxo de material
- Integrar com análise de distância percorrida

---

### 4. Abas "Standard", "Produções", "KPIs", etc.

Estas abas são **preservadas integralmente**. A aplicação:
- ✅ Não apaga dados existentes
- ✅ Não modifica fórmulas
- ✅ Pode ler dados para contexto
- ❌ Nunca escreve sem aprovação explícita

---

## 🔧 Estratégia de Preenchimento

### Validações Antes de Escrever

1. **Verificar integridade do arquivo**
   - Arquivo é .xlsx válido
   - Abas ANÁLISE e MELHORIAS existem
   - Estrutura base está preservada

2. **Validar dados de entrada (JSON)**
   - Todas as etapas têm timestamps
   - Classificações são AV/NAV/D
   - Somas fazem sentido (ciclo = AV + NAV + D)

3. **Detectar conflitos**
   - Se análise anterior existe, perguntar: sobrescrever ou nova linha?
   - Preservar histórico se houver coluna de data

### Ordem de Preenchimento

1. Cabeçalho da aba ANÁLISE (metadados)
2. Tabela de etapas (linhas 7+)
3. Cabeçalho da aba MELHORIAS
4. Tabela de desperdícios (linhas 7+)
5. Recomendações gerais (linha 14+)
6. Validar somas e fórmulas
7. Salvar arquivo com nome único (timestamp ou ID)

### Tratamento de Erros

- **Arquivo não existe**: Copiar template, depois preencher
- **Estrutura quebrada**: Reportar e aguardar correção manual
- **Dados inconsistentes**: Sinalizar no relatório, marcar como `low_confidence`
- **Fórmulas conflitam**: Preservar fórmulas, apenas adicionar dados

---

## 📊 Mapeamento JSON → Excel

A saída JSON da IA deve ser transformada para o Excel conforme mapa:

```json
{
  "metadata": {
    "department": "PAC",
    "workstation": "P1.2",
    "takt_time_s": 120,
    "target_cycle_s": 120,
    "analyst": "IA SPS Bot",
    "analysis_date": "2026-05-05"
  }
  // → Linhas 1–5 da aba ANÁLISE
}
```

```json
{
  "steps": [
    {
      "id": 1,
      "description": "Pegar parafuso do kit",
      "start_s": 0.0,
      "end_s": 2.5,
      "duration_s": 2.5,
      "classification": "AV",
      "justification": "Transformação direta",
      "observation": "Chave manual"
    }
    // → Linha 7+ da tabela de etapas
  ]
}
```

```json
{
  "wastes": [
    {
      "step_id": 5,
      "type": "Movimento",
      "description": "Procura desorganizada",
      "duration_s": 2.5,
      "improvement_suggestion": "Quadro visual 5S",
      "priority": "Alta"
    }
    // → Linha 7+ da tabela de desperdícios
  ]
}
```

---

## 🚀 Fases de Implementação

### MVP (Fase 2)
- [x] Preenchimento manual via JSON
- [ ] Validação de dados
- [ ] Escrita em Excel template existente

### Fase 3
- [ ] Extração automática de tempos
- [ ] Integração com vídeo
- [ ] Cálculos automáticos

### Fase 4+
- [ ] Histórico de análises
- [ ] Comparação de melhorias
- [ ] Dashboard em Streamlit

---

## 📝 Checklist de Preenchimento

Antes de gerar o arquivo Excel final:

- [ ] Todos os timestamps estão preenchidos e válidos
- [ ] Todas as etapas têm classificação AV/NAV/D
- [ ] Soma de tempos = Ciclo observado
- [ ] Ciclo observado está razoável vs Takt
- [ ] Pelo menos um desperdício foi identificado (se houver D)
- [ ] Sugestões de melhoria são práticas e específicas
- [ ] Prioridades estão definidas
- [ ] Arquivo template foi copiado (não sobrescrito)
- [ ] Arquivo novo tem nome com timestamp ou ID
- [ ] Fórmulas não foram apagadas
- [ ] Abas standard estão intactas

---

## 📞 Suporte

Para dúvidas sobre estrutura do Excel:
- Consulte arquivo template em `data/templates/`
- Revise exemplos em `docs/`
- Contate especialista SPS para validação

---

**Versão**: 1.0  
**Data**: Maio/2026  
**Template Válido**: PMGS_P1_Analise_SPS_CORRIGIDA_2026-03-18.xlsx
