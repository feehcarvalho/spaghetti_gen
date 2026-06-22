# Como Cadastrar Nova Posição

Este guia descreve como preparar uma nova posição/posto para análise SPS.

## 1. Criar Pasta da Posição

Crie a pasta:

```text
data/knowledge_raw/posicoes/{POSTO}/
```

Exemplo:

```text
data/knowledge_raw/posicoes/PMGS.P2/
```

Use o mesmo identificador que será preenchido no campo `Posto`.

## 2. Adicionar Padrão da Posição

Crie:

```text
data/knowledge_raw/posicoes/{POSTO}/padrao_posicao.md
```

Inclua:

- objetivo do posto;
- produto/variante atendida;
- sequência padrão;
- ferramentas principais;
- pontos de qualidade;
- rastreabilidade necessária.

## 3. Adicionar Pontos Críticos

Crie:

```text
data/knowledge_raw/posicoes/{POSTO}/pontos_criticos.md
```

Inclua:

- riscos de segurança;
- riscos de qualidade;
- riscos ergonômicos;
- condições que geram baixa confiança;
- operações que exigem validação gemba.

## 4. Adicionar Dicionário do Posto

Crie:

```text
data/knowledge_raw/posicoes/{POSTO}/dicionario_posto.md
```

Inclua nomenclaturas locais:

- peças;
- ferramentas;
- siglas;
- posições LD/LE;
- dispositivos;
- sistemas;
- nomes usados pela produção.

Não inclua termos não validados.

## 5. Adicionar Exemplos Revisados

Crie:

```text
data/knowledge_raw/posicoes/{POSTO}/exemplos_microetapas.md
```

Inclua exemplos de microetapas revisadas:

- descrição;
- início/fim aproximado, se houver;
- classificação AV/NAV/D;
- justificativa técnica;
- observações de baixa confiança.

## 6. Adicionar Layout JSON

Crie:

```text
data/layouts/{POSTO}.json
```

Formato mínimo:

```json
{
  "layout_id": "POSTO",
  "largura": 10,
  "altura": 8,
  "locais": {
    "produto": {"x": 5, "y": 4, "descricao": "Produto em montagem"},
    "wpo": {"x": 1, "y": 7, "descricao": "Tela WPO/IHM"}
  }
}
```

Regras:

- não inventar coordenadas;
- usar nomes estáveis;
- manter `x` e `y` dentro de `largura` e `altura`;
- validar com o time local.

## 7. Rodar Análise Teste

Execute com provider `mock` para validar Excel/UI:

```bat
scripts\run_pipeline_mock.bat
```

Depois execute com vídeo real e provider desejado.

## 8. Validar no Gemba

Antes de usar a posição em rotina:

- revisar documentos com engenharia/liderança;
- validar nomenclatura;
- revisar exemplos de microetapas;
- confirmar layout;
- gerar análise teste;
- revisar Excel final;
- preencher [CHECKLIST_VALIDACAO_GEMBA.md](CHECKLIST_VALIDACAO_GEMBA.md).

## 9. Manutenção

Atualize a base quando houver:

- mudança de método;
- nova variante;
- nova ferramenta;
- mudança de layout;
- mudança de sistema;
- alteração de takt;
- revisão de padrão SPS.
