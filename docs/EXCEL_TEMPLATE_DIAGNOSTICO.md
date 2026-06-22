# Diagnóstico Técnico do Template Excel

- Gerado em: 2026-05-05 13:44:45
- Arquivo inspecionado: `PMGS_P1_Analise_SPS_CORRIGIDA_2026-03-18.xlsx`
- Modo de leitura: `openpyxl.load_workbook(..., data_only=False, keep_links=True)`
- Garantia operacional: o script não chama `save()` e não modifica o template.

> Observação: Arquivo padrao data\templates\PMGS_P1_Analise_SPS_CORRIGIDA_2026-03-18.xlsx nao encontrado; usando fallback PMGS_P1_Analise_SPS_CORRIGIDA_2026-03-18.xlsx.

## Abas Existentes

| Aba | Dimensao usada | Mesclas | Formulas L1-L20 | Graficos | Imagens | Links |
| --- | --- | --- | --- | --- | --- | --- |
| Standard (1-10) | A1:AS66 | 93 | 84 | 0 | 0 | 0 |
| Standard (2-10) | A1:AO91 | 106 | 107 | 0 | 0 | 0 |
| Standard (3-10) | A1:AO91 | 105 | 107 | 0 | 0 | 0 |
| Standard (4-10) | A1:AO91 | 105 | 107 | 0 | 0 | 0 |
| Standard (5-10) | A1:AO91 | 105 | 107 | 0 | 0 | 0 |
| Standard (6-10) | A1:AO91 | 105 | 107 | 0 | 0 | 0 |
| Standard (8-10) | A1:AO91 | 105 | 107 | 0 | 0 | 0 |
| Worktable | A1:AAE505 | 17 | 11294 | 0 | 0 | 0 |
| Gráfico Balanceamento x Volume | A1:R3 | 13 | 5 | 1 | 0 | 0 |
| Gráfico Workload | A1:Q63 | 13 | 5 | 1 | 0 | 0 |
| Diagrama de Espaguete | A1:X65 | 138 | 5 | 0 | 0 | 0 |
| E.S._Avix Produção | A1:R36 | 39 | 0 | 0 | 0 | 0 |
| E.S._Avix Logística | A1:P37 | 27 | 0 | 0 | 0 | 0 |
| E.S. Rotas Log. | A1:AD136 | 338 | 0 | 0 | 0 | 0 |
| Validação | A1:R95 | 300 | 0 | 0 | 0 | 0 |
| ANÁLISE | A1:I59 | 1 | 0 | 0 | 0 | 0 |
| MELHORIAS | A1:H18 | 7 | 0 | 0 | 0 | 0 |

## Abas Candidatas a Preenchimento Automático

| Aba | Prioridade | Uso candidato | Restricao |
| --- | --- | --- | --- |
| ANÁLISE | Alta | Cabecalho, tabela de microetapas, totais AV/NAV/D. | Escrever apenas celulas mapeadas e preservar formatacao. |
| MELHORIAS | Alta | Tabela de desperdicios, sugestoes e recomendacoes gerais. | Limitar escrita aos campos de dados e nao mexer em estruturas. |
| Diagrama de Espaguete | Media | Possivel insercao futura de imagem/rota spaghetti. | Exige cuidado por alta quantidade de celulas mescladas. |
| Standard*, Worktable, graficos e validacao | Baixa/nao escrever | Abas de apoio, padrao e calculos existentes. | Preservar integralmente ate haver mapeamento especifico. |

## Mapeamento Inicial da Aba ANÁLISE

| Celula/faixa | Campo candidato | Valor observado |
| --- | --- | --- |
| A1 | Titulo da analise | ANÁLISE DETALHADA DO VÍDEO – PMGS.P1 |
| B3 | Departamento/area | FUNCTION AREA 5 |
| E3 | Emitido por/responsavel | MARIANE |
| H3 | Data | 2026-03-18 00:00:00 |
| B4 | Posto | PMGS.P1 |
| E4 | Processo | Pré montagem da grade superior (PMGS) |
| H4 | Takt | 330s (05:30) |
| B5 | Ciclo observado | 330s (05:30) |
| E5 | Total AV | 107s (32.4%) |
| G5 | Total NAV | 192s (58.2%) |
| I5 | Total D | 31s (9.4%) |
| A6:I6 | Cabecalho da tabela de microetapas | Nº, etapa, inicio, fim, duracao, classificacao, justificativa, ferramenta |
| A7:I59 | Dados atuais de microetapas | Faixa observada no template; escrever somente apos copia do arquivo. |

Mesclas relevantes na aba: 1 intervalo(s). A escrita deve mirar a celula superior esquerda de cada mescla quando aplicavel.

## Mapeamento Inicial da Aba MELHORIAS

| Celula/faixa | Campo candidato | Valor observado |
| --- | --- | --- |
| A1 | Titulo da aba | MELHORIAS – OPORTUNIDADES DE KAIZEN |
| B3 | Ciclo observado | 330s (05:30) |
| E3 | Takt | 330s (05:30) |
| H3 | Folga vs takt | +0s |
| B4 | Tempo D | 31s (9.4%) |
| E4 | Leitura/diagnostico | Desperdício concentrado em deslocamento para abastecimento (caixas) dentro do ciclo e espera por apontamento/liberação após posicionamento do suporte de barra. |
| A6:H6 | Cabecalho da tabela de melhorias | Etapa, inicio, fim, duracao, desperdicio, tipo, sugestao, prioridade |
| A7:H13 | Dados atuais de melhorias | Faixa inicial para sugestoes relacionadas a desperdicios. |
| A14:H18 | Recomendacoes gerais | Bloco textual ja existente no template. |

Mesclas relevantes na aba: 7 intervalo(s). Evitar inserir linhas antes de confirmar impacto visual.

## Riscos Técnicos

- Fórmulas: abrir com `data_only=False` preserva as fórmulas carregadas. Foram encontradas fórmulas nas primeiras 20 linhas em 11 aba(s): Standard (1-10), Standard (2-10), Standard (3-10), Standard (4-10), Standard (5-10), Standard (6-10), Standard (8-10), Worktable, Gráfico Balanceamento x Volume, Gráfico Workload, Diagrama de Espaguete.
- Células mescladas: há mesclas em várias abas; escrever fora da célula superior esquerda de uma mescla pode falhar ou corromper o layout.
- Abas com muitas mesclas: Standard (1-10) (93), Standard (2-10) (106), Standard (3-10) (105), Standard (4-10) (105), Standard (5-10) (105), Standard (6-10) (105), Standard (8-10) (105), Worktable (17), Gráfico Balanceamento x Volume (13), Gráfico Workload (13), Diagrama de Espaguete (138), E.S._Avix Produção (39), E.S._Avix Logística (27), E.S. Rotas Log. (338), Validação (300), ANÁLISE (1), MELHORIAS (7).
- Gráficos: Gráfico Balanceamento x Volume, Gráfico Workload.
- Imagens: nenhuma imagem carregada pelo openpyxl.
- Links externos: file:///\\brsafs01\chassis2$\SPS%20Office\SPS\03_Treinamentos\26_Kaizen\Kaizen%202019\Materiais%20de%20apoio%20Kaizen%202019\Templates%20para%20as%20funções\Padrão,%20Work%20Table,%20Espaguete%20-%203%20folhas.xlsx, file:///\\brsafs01\chassis2$\SPS%20Office\SPS\000_SPS_2019\10_KAIZEN\03_DOCUMENTOS\Standard_2019_Sequência,%20Espaguete,%20Workload,%20E.S.%20-%203%20folhas%20V1%20(backup).xlsx, file:///\\brsafs01\chassis2$\SPS%20Office\SPS\03_Treinamentos\26_Kaizen\Kaizen%202019\Padrão,%20Work%20Table,%20Grafico,%20Espaguete,%20E.S.%20-%203%20folhas.xlsx.
- Hyperlinks em células: nenhum hyperlink detectado.
- Nomes definidos: nenhum nome definido detectado.
- Referências quebradas: Standard (1-10) (7), Standard (2-10) (8), Standard (8-10) (8), Worktable (4). O inspetor não altera nem recalcula fórmulas.

## Recomendação de Implementação

- Nunca recriar o workbook do zero.
- Sempre copiar o template para `data/outputs/` e editar somente a cópia.
- Escrever apenas células/faixas mapeadas nas abas `ANÁLISE` e `MELHORIAS`.
- Preservar fórmulas, células mescladas, gráficos, estilos, validações, imagens e abas de apoio.
- Não usar pandas para escrita Excel neste fluxo; usar `openpyxl` sobre uma cópia do template.
- Validar o JSON com `OperationalAnalysis` antes de qualquer preenchimento.
