# Status da Correcao - Tempo, Sheet2, Atividade, Repeticao e Linguagem

Data: 2026-05-27

## Investigacao

- Resposta OpenAI -> `OperationalAnalysis`: `app/ai/window_analyzer.py` gera `WindowAnalysis`; `app/analysis/consolidator.py` converte para `MicroStep` e `OperationalAnalysis`.
- Consolidacao de microetapas: antes estava em `app/analysis/consolidator.py` com remocao apenas de duplicidade obvia entre janelas.
- Normalizacao de linguagem: `app/analysis/language_normalizer.py`.
- Memoria/RAG no prompt: `app/knowledge/knowledge_orchestrator.py`, `app/knowledge/local_retriever.py`, `app/ai/video_overview.py`, `app/ai/window_analyzer.py` e `app/ai/prompt_builder.py`.
- Leitura de `.xlsx` de memoria: corrigida em `app/knowledge/xlsx_memory_reader.py` e ligada ao orchestrator.
- Tempos: `app/analysis/time_auditor.py` agora e a fonte unica antes de exportar.
- Aba principal Excel: `app/excel/template_writer.py`.
- Standard consolidado: `app/excel/standard_writer.py`.
- Sheet2: `app/excel/conversion_sheet_writer.py`.
- JSON final: `app/main.py` e `app/ui/streamlit_app.py`.
- Download Excel/JSON: `app/ui/streamlit_app.py`.
- Quality gate: `app/analysis/quality_gate.py` e `app/analysis/sps_validator.py`.
- Correcao/refazer analise: `app/analysis/correction_flow.py` e painel em `app/ui/streamlit_app.py`.

## Causa Raiz

O erro de tempo vinha de pontos do fluxo que aceitavam `tempo_acumulado_s` vindo da IA ou de calculos anteriores. Em saidas reais antigas foi observado acumulado com comportamento de timestamp de fim, por exemplo acumulados acompanhando `fim_s`. A regra correta agora fica concentrada em `time_auditor`: `duracao_s = fim_s - inicio_s` e `tempo_acumulado_s = soma progressiva das duracoes`.

A justificativa podia virar texto principal porque os writers buscavam diretamente campos como `instrucao_padrao`, `descricao_tecnica_detalhada` ou `etapa_detalhada`, sem uma funcao unica de prioridade e sem bloqueio explicito contra `justificativa_tecnica`.

A repeticao excessiva ocorria porque a consolidacao removia duplicidade quase identica, mas nao agrupava sequencias consecutivas com a mesma intencao operacional, como pegar, movimentar e levar o mesmo objeto.

Ferramenta/metodo inventado era tratado principalmente por prompt. Agora ha validacao local para termos como parafusadeira pneumatica, apertadeira, VR, Bluebox, WPO, eixo/lado/variante/quantidade sem evidencia, memoria ou contexto.

A linguagem podia ser burocratizada pelo normalizador ao tentar melhorar texto que ja estava bom. A correcao preserva instrucoes diretas e so repara linguagem generica, burocratica ou coloquial inadequada.

## Correcoes

- Criado `app/analysis/activity_text.py` com `get_microstep_activity_text(microstep)`. Writers e Sheet2 usam essa funcao. A justificativa nunca e fonte de `activity`.
- Criado `app/analysis/operational_language_repair.py` para separar activity/justificativa, preservar frases boas e reescrever casos ruins.
- Criado `app/analysis/microstep_consolidator.py` para agrupar repeticoes consecutivas sem mudar classificacao, ferramenta, peca, eixo, lado, risco ou objetivo operacional real.
- Criado `app/analysis/export_preparer.py` para preparar a analise antes de UI/JSON/Excel: reparo de linguagem, investigacao operacional quando ha contexto, consolidacao, auditoria de tempo e quality gate.
- Atualizado `app/analysis/time_auditor.py` com `audit_and_recalculate_times` e `validate_time_columns_for_export`.
- Atualizado `app/excel/conversion_sheet_writer.py`: `Sheet2` sempre na segunda posicao, cabecalho exato, `activity` por instrucao operacional e `timeOfElement` como tempo individual.
- Atualizado `app/excel/standard_writer.py`: coluna D recebe instrucao operacional, E recebe lembrete curto, G tempo do elemento e H acumulado auditado.
- Atualizado `app/excel/template_writer.py`, `app/main.py` e `app/ui/streamlit_app.py` para preparar a analise antes do Excel/JSON.
- Atualizado `app/knowledge/xlsx_memory_reader.py`: planilhas de memoria leem varias abas, nomes de abas, celulas relevantes, regras de mapeamento/conversao, exemplos e avisos.
- Atualizado prompt em `app/ai/prompt_builder.py` para reforcar analise de processo real, nao repeticao, nao invencao, uso de memoria e preservacao do tom operacional.
- Criado `tools/audit_generated_excel_contract.py` para auditar workbook gerado.

## Resultado dos Testes

- `python -m pytest -q --basetemp data/outputs/pytest_tmp_full2`
- Resultado: 160 passed, 1 warning.

## Auditoria do Excel

Geracao usada:

`python tools/generate_excel_from_json.py data/outputs/sample_analysis_pmgs_p1.json data/templates/PMGS_P1_Analise_SPS_CORRIGIDA_2026-03-18.xlsx data/outputs/audit_contract_generated.xlsx --fill-standard --standard-consolidado`

Auditoria:

`python tools/audit_generated_excel_contract.py data/outputs/audit_contract_generated.xlsx`

Resultado esperado:

`Contrato Excel OK`

## Garantias Operacionais

Login/autorizacao, tela inicial, upload, OpenAI, fluxo real por video, memorias, Excel, Sheet2, downloads, template original, JSON, historico/correcao e testes existentes foram preservados. O template original nao foi alterado; a escrita continua acontecendo em copia gerada.
