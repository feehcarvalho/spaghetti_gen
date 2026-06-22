# Contrato Sheet2 para app da automacao logistica

## Regra principal

A segunda aba do workbook gerado deve ser sempre `Sheet2`. Ela e tratada como contrato de integracao para o app da automacao logistica.

Nao inserir outra aba antes dela. Quando houver aba consolidada, a ordem esperada e:

1. `STANDARD_CONSOLIDADO`
2. `Sheet2`
3. `ENTENDIMENTO_CONVERSAO`

Quando nao houver consolidado, a primeira aba do template permanece como primeira, e `Sheet2` continua na segunda posicao.

A `Sheet2` deve ser sempre substituida durante a exportacao final. Ela deve ser uma aba tecnica crua: sem cores, imagens, graficos, celulas mescladas, dashboard, metadados, melhorias, percentuais ou colunas de inicio/fim/justificativa.

## Cabecalhos obrigatorios

A primeira linha da `Sheet2` deve manter exatamente:

| Coluna | Cabecalho |
|---|---|
| A | `id_AvNavD` |
| B | `activity` |
| C | `reminder` |
| D | `id_safe_icon` |
| E | `timeOfElement` |
| F | `type_document` |
| G | `id_takt` |
| H | `id_symbol` |
| I | `title` |

A grafia correta do campo e `timeOfElement`.

## Mapeamento AV/NAV/D

- AV = `211` por padrao, configuravel por `SHEET2_ID_AV`
- NAV = `212` por padrao, configuravel por `SHEET2_ID_NAV`
- D = `213` por padrao, configuravel por `SHEET2_ID_D`

## Campos

`activity`: instrucao operacional da microetapa no padrao Scania.

`reminder`: vazio por contrato tecnico. Nao recebe inicio, fim, acumulado, classificacao ou justificativa.

`id_safe_icon`: vazio por padrao, configuravel por `SHEET2_ID_SAFE_ICON`.

`timeOfElement`: tempo individual do elemento em segundos. Nao usar tempo acumulado nesse campo.

`type_document`: `SPS` por padrao, configuravel por `SHEET2_TYPE_DOCUMENT`.

`id_takt`: takt time informado nos metadados.

`id_symbol`: vazio por padrao, configuravel por `SHEET2_ID_SYMBOL`.

`title`: processo informado nos metadados.

## Pendencias de validacao

- Confirmar se o app exige o nome `Sheet2` ou apenas a posicao da aba.
- Confirmar se `id_safe_icon` deve ficar vazio ou receber ID unico.
- Confirmar se `id_symbol` deve ficar vazio, fixo ou variavel.
- Confirmar formalmente o mapeamento AV/NAV/D.
