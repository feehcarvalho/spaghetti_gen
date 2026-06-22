# Status das melhorias para uso real

## O que foi alterado

- `app/analysis/time_auditor.py`: adicionadas funções explícitas para tempo do elemento, tempo acumulado, totais AV/NAV/D e validação de consistência.
- `app/analysis/quality_gate.py`: passou a consultar a auditoria de tempo antes da liberação.
- `app/analysis/operational_investigator.py`: criada camada incremental para reforçar especificidade operacional com base em contexto/memória.
- `app/analysis/video_sps_orchestrator.py`: passou a aplicar investigação operacional na finalização da análise.
- `app/excel/conversion_sheet_writer.py`: criada escrita/validação da `Sheet2` e da aba `ENTENDIMENTO_CONVERSAO`.
- `app/excel/standard_writer.py`: adicionado modo `STANDARD_CONSOLIDADO` sem remover o preenchimento Standard existente.
- `app/excel/template_writer.py`: recalcula tempos antes do Excel e escreve a Sheet2 como segunda aba na cópia gerada.
- `app/ui/streamlit_app.py`: adicionado expander opcional `Contexto operacional adicional` nos metadados e validação de saída compatível com abas novas controladas.
- `tools/generate_excel_from_json.py`: adicionada opção `--standard-consolidado`.
- `README.md`: adicionada seção curta sobre uso real e integração Sheet2.

## O que foi preservado

- Tela de login/responsabilidade.
- Fluxo principal da interface.
- Provider OpenAI.
- Pipeline de vídeo por janelas.
- Uploads de vídeo, layout e memórias.
- Downloads Excel/JSON.
- Template Excel original.
- Preenchimento legado das abas Standard.
- Correção/refazer análise.
- Quality gate e validações existentes.

## Correção de tempo

O Python agora recalcula:

- `duracao_s = fim_s - inicio_s`;
- `tempo_acumulado_s = soma progressiva das durações`;
- totais AV/NAV/D;
- total geral e percentuais.

Tempo negativo ou fim menor que início bloqueiam a auditoria. Inconsistências entram como alerta técnico ou bloqueio conforme severidade.

## Proteção da Sheet2

A `Sheet2` é criada/mantida sempre na segunda posição do workbook gerado. O cabeçalho obrigatório é validado antes do salvamento:

`id_AvNavD, activity, reminder, id_safe_icon, timeOfElement, type_document, id_takt, id_symbol, title`

`timeOfElement` recebe o tempo individual do elemento, não o acumulado.

## Investigação operacional

A nova camada usa contexto/memória para enriquecer microetapas com variante, eixo, lado e nomenclatura como `VR de pneu` ou `parafusadeira pneumática` quando houver confirmação. Quando não houver confirmação, não inventa; marca baixa confiança e validação no gemba/SPS.

## Testes

Executado:

```bat
.venv\Scripts\python.exe -m pytest -q
```

Resultado:

`152 passed, 1 warning in 281.13s`

## Pendências reais

- Confirmar com automação logística se o app exige o nome `Sheet2` ou apenas a segunda posição.
- Confirmar IDs definitivos de `id_safe_icon` e `id_symbol`.
- Validar no gemba/SPS qualquer uso de contexto operacional informado manualmente.
