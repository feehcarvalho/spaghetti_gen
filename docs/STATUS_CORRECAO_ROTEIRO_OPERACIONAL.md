# Status - Correcao de Roteiro Operacional

Data: 2026-05-28

## Problema encontrado

A analise ja exportava Excel/Sheet2, mas ainda deixava microetapas com texto de baixa utilidade operacional, por exemplo "ponto necessario", "recurso de apoio", "ferramenta indicada" e "conforme necessidade da operacao". Tambem havia risco de repetir observacoes soltas como pegar/movimentar/levar o mesmo pneu em linhas diferentes, sem formar um roteiro de execucao do posto.

## Correcao aplicada

Foi criada a camada `app/analysis/operational_script_builder.py`, executada dentro de `prepare_analysis_for_export` antes da consolidacao final. Ela monta um roteiro operacional resumido, repara frases genericas, preserva linguagem direta e devolve as instrucoes para as microetapas sem alterar tempos, classificacao ou evidencias.

O fluxo atual de preparo ficou:

1. Reparar atividade/justificativa.
2. Aplicar investigacao operacional com memoria/contexto quando fornecido.
3. Montar roteiro operacional.
4. Aplicar o roteiro nas microetapas.
5. Consolidar repeticoes reais.
6. Recalcular tempos pelo auditor.
7. Executar quality gate de texto, ferramenta/metodo e tempo.

## Repeticao e granularidade

O consolidator passou a agrupar tambem microetapas consecutivas que, apos o roteiro, viram a mesma instrucao operacional. Isso reduz casos como pegar/movimentar/levar o mesmo pneu quando a intencao e uma so.

Etapas essenciais continuam separadas: alinhar, encaixar, colocar porcas, instalar, fixar, apertar, conferir e retirar nao sao misturadas quando representam objetivos operacionais diferentes.

## Ferramenta, Green Box e quantidade

O quality gate foi reforcado para alertar claims sem suporte de:

- parafusadeira pneumatica;
- apertadeira;
- VR;
- Bluebox;
- Green Box / caixa verde;
- eixo/lado/8x2;
- duas/oito/10 porcas;
- valvula/bico de ar.

Quando o contexto indica Green Box/caixa verde, o roteiro substitui Bluebox por Green Box/caixa verde e marca validacao se necessario. Quantidades como "duas porcas" e "oito porcas restantes" so sao preservadas quando ha confirmacao por memoria, usuario ou evidencia.

## Frases genericas bloqueadas

Foram adicionadas regras em `operational_language_repair` e `quality_gate` para detectar/reparar:

- ponto necessario para continuidade da operacao;
- ponto de abastecimento indicado;
- componente conforme necessidade;
- recurso de apoio;
- ferramenta indicada;
- peca no conjunto;
- conforme necessidade da operacao;
- ponto de trabalho indicado.

Quando ha detalhe real no contexto, a frase e reescrita. Quando nao ha, o texto remove o sufixo generico e mantem instrucao conservadora sem inventar eixo, ferramenta ou quantidade.

## Memoria e prompt

O prompt foi atualizado para exigir roteiro mental do processo antes das microetapas finais, evitar repeticao de pegar/levar o mesmo pneu, nao trocar Green Box por Bluebox, nao inventar pneumática, eixo, lado ou quantidade, e evitar frases genericas sem especificar o recurso real.

## Excel e Sheet2

O roteiro entra antes da escrita do Excel. Assim, a primeira aba Standard e a Sheet2 continuam recebendo `get_microstep_activity_text`, ja com a instrucao operacional reparada.

Validacao feita no arquivo:

`data/outputs/real_video_checks/oitao_xt_8x2_rafael/analise_real_5_2_6_2026-05-28_operational_script.xlsx`

Resultado:

`Contrato Excel OK`

## Testes

Novos testes adicionados:

- `tests/test_operational_script_builder.py`
- `tests/test_microstep_repetition_balance.py`
- `tests/test_manual_vs_tool_claim.py`
- `tests/test_greenbox_terminology.py`
- `tests/test_quantity_claims.py`
- `tests/test_generic_phrase_blocker.py`

Suite completa executada durante a correcao: 184 passaram e 1 falhou inicialmente por permitir export de analise artificial generica; o bloqueio foi corrigido em `app/analysis/sps_validator.py`.

Comando final executado apos esta documentacao:

`python -m pytest -q --basetemp data/outputs/pytest_tmp_full_operational_script_final`

Resultado final:

`185 passed, 1 warning`

## Auditoria

Para auditar um Excel gerado:

`python tools/audit_generated_excel_contract.py caminho_do_excel.xlsx`

O script agora tambem verifica frases genericas, repeticao excessiva, Bluebox versus Green Box, claims de pneumática sem evidencia, layout Scania, Sheet2 e tempos.
