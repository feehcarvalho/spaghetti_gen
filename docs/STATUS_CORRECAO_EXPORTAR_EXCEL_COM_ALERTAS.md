# Status - Exportar Excel com alertas SPS

Data: 2026-06-08

## Onde estava o bloqueio

O bloqueio do Excel acontecia no caminho real do botao da interface:

1. `app/ui/streamlit_app.py::_render_review_editor`
   - Botao: `Gerar planilha Scania (.xlsx) com analise atual`.
   - Chama `_generate_excel_from_review_state`.

2. `app/ui/streamlit_app.py::_generate_excel_from_review_state`
   - Reidrata a analise atual.
   - Chama `assert_analysis_can_generate_excel`.
   - Chama `write_analysis_to_template`.
   - Salva Excel temporario, move para o caminho final e libera `last_excel_path` / `last_json_path`.

3. `app/analysis/sps_validator.py::assert_analysis_can_generate_excel`
   - Antes podia acionar `assert_quality_gate_passed` como bloqueio.

4. `app/analysis/quality_gate.py::assert_quality_gate_passed`
   - Era a origem da mensagem `Excel bloqueado pelo quality gate SPS`.
   - Alertas como `Microetapa D sem melhoria/alerta vinculado`, frase generica e acao na justificativa podiam interromper a exportacao.

5. Mensagem vermelha:
   - `app/ui/streamlit_app.py::_render_review_editor`, no `except`, exibe `st.error("Nao foi possivel gerar a planilha Scania: ...")`.
   - Agora esse erro deve aparecer apenas para erro tecnico fatal, porque alertas SPS nao geram excecao bloqueante.

6. Recovery:
   - `app/ui/streamlit_app.py::_save_failed_export_recovery`.
   - Continua salvando em `data/outputs/recovery/analise_preservada_*.json` se houver falha real.

7. Excel writer:
   - `app/excel/template_writer.py::write_analysis_to_template`.
   - Cria/preenche o workbook, chama `ensure_conversion_sheets`, escreve alertas e salva.

8. Sheet2:
   - `app/excel/conversion_sheet_writer.py::ensure_conversion_sheets`.
   - Mantem `Sheet2` na segunda posicao.

9. Download:
   - `app/ui/streamlit_app.py::_render_downloads`.
   - Libera download do Excel e JSON quando os arquivos existem e passam na validacao basica.

## O que foi alterado

- `QualityGateResult` agora possui `blocking_errors`, `warnings`, `alerts` e `can_export`.
- Alertas SPS revisaveis mantem `can_export=True`.
- Erros tecnicos fatais mantem `can_export=False`.
- `assert_analysis_can_generate_excel` bloqueia apenas:
  - analysis inexistente;
  - lista de microetapas vazia;
  - e, somente se a configuracao permitir, qualidade SPS bloqueante.
- `FORCE_EXCEL_EXPORT_WITH_ALERTS=true` vence qualquer tentativa de bloquear por alerta SPS.
- `write_analysis_to_template` gera a aba final `ALERTAS_VALIDACAO_SPS`.
- `alertas_validacao_sps` foi adicionado ao JSON final como lista estruturada, preservando tambem `alertas_validacao` como lista de textos para compatibilidade.

## Alertas que agora vao para ALERTAS_VALIDACAO_SPS

- Microetapa D sem melhoria/alerta vinculado.
- Acao operacional na justificativa.
- Frase generica ou linguagem burocratica.
- Ferramenta conflitante com metodo manual.
- Baixa confianca.
- Eixo/lado incerto.
- Quantidade incerta.
- Nomenclatura ou evidencia incerta.
- Necessidade de validacao no gemba.
- Tempo/cobertura/janela a revisar.

## Erros que ainda bloqueiam

- `analysis is None`.
- `analysis.microetapas` vazio.
- Template Excel nao encontrado.
- Workbook sem abas obrigatorias.
- Contrato tecnico de `Sheet2` invalido.
- Caminho de output invalido.
- Falha fatal de escrita/salvamento/openpyxl.
- JSON de recovery impossivel de carregar/validar.

## Configuracao

`.env.example` foi atualizado:

```env
QUALITY_GATE_BLOCKS_EXCEL=false
FORCE_EXCEL_EXPORT_WITH_ALERTS=true
```

Com `FORCE_EXCEL_EXPORT_WITH_ALERTS=true`, o Excel nao deve ser bloqueado por alerta SPS.

## Recovery de emergencia

Script criado:

```powershell
python tools\generate_excel_from_recovery.py data\outputs\recovery\analise_preservada_20260608_092721_098423.json
```

Saida padrao:

```text
data\outputs\recovery_excel\
```

O script:

1. carrega o JSON preservado;
2. valida `OperationalAnalysis`;
3. roda o quality gate como alerta;
4. gera Excel com `STANDARD_CONSOLIDADO`, `Sheet2` e `ALERTAS_VALIDACAO_SPS`;
5. imprime o caminho do Excel gerado.

## Testes executados

```text
.venv\Scripts\python.exe -m pytest -q tests/test_force_excel_export_with_alerts.py
10 passed, 1 warning in 252.69s
```

```text
.venv\Scripts\python.exe -m pytest -q tests/test_export_with_quality_alerts.py tests/test_force_excel_export_with_alerts.py
17 passed, 1 warning in 429.77s
```

Tambem foi feito import check sem bytecode:

```text
imports_ok
```

Observacao: `pytest -q` completo coleta 204 testes. Ele nao foi repetido integralmente nesta rodada porque os testes Excel em OneDrive estao muito lentos; na rodada anterior, apenas 24 testes relacionados a Excel/Sheet2/quality gate imprimiram `24 passed` e o wrapper encerrou por timeout apos 47 minutos.

## Excel de teste auditado

Arquivo auditado:

```text
data\outputs\test_force_recovery\337e047d4a4440fca93c4342209d915d\analise_preservada_teste_20260608_103337.xlsx
```

Auditoria:

```text
.venv\Scripts\python.exe tools\audit_generated_excel_contract.py <excel>
Contrato Excel OK
```

## Resultado esperado na UI

Ao clicar em `Gerar planilha Scania (.xlsx) com analise atual`:

- se a analise existe e tem microetapas, o Excel deve ser gerado mesmo com baixa confianca, D sem melhoria, frase generica, ferramenta conflitante ou acao na justificativa;
- a UI deve mostrar sucesso e aviso amarelo;
- o Excel deve ficar disponivel para download;
- os alertas devem estar na ultima aba `ALERTAS_VALIDACAO_SPS`;
- `Sheet2` continua como segunda aba.
