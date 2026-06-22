# Status - Ajuste de Layout e Correção Pós-Análise

Data: 2026-05-21

## O que foi alterado

- A seção `Memória da IA` saiu do fluxo principal numerado.
- A memória foi movida para área auxiliar na sidebar: `Memória da IA / adicionar conhecimento`.
- A tela principal foi reorganizada para o fluxo operacional:
  1. Vídeo da operação
  2. Layout do posto para mapa de espaguete
  3. Opções da análise
  4. Metadados
  5. Processamento
  6. Resultado da análise
- Parâmetros técnicos de janela, frames e qualidade foram ocultados do usuário final.
- A análise roda por padrão em `Máxima qualidade / produção`.
- Foi adicionada a área `Correção da análise` após o resultado.
- O botão `Refazer análise com observações` gera uma nova versão sem apagar a anterior.
- Observações podem ser salvas como memória interna pendente de validação.

## O que foi preservado

- Tela inicial de login/autorização.
- Mensagem de responsabilidade SPS.
- Registro de usuário logado e logs de acesso.
- Upload e processamento de vídeo.
- Provider OpenAI.
- Pipeline SPS por janelas.
- RAG/memórias internas.
- Microetapas, tempos, AV/NAV/D e melhorias.
- Geração e downloads de Excel/JSON.
- Template Excel padrão Scania.

## Onde fica a memória da IA

A memória auxiliar fica na sidebar, em:

```text
Memória da IA / adicionar conhecimento
```

Ela aceita documentos, imagens de referência e uma observação curta de nomenclatura/processo. Esse conhecimento complementa o RAG local; não treina o modelo OpenAI.

## Como refazer análise com observações

Após gerar o resultado, use `Correção da análise`:

1. Escreva a observação.
2. Marque, se desejar, `Salvar observação como memória interna pendente de validação`.
3. Clique em `Refazer análise com observações`.

A aplicação usa o vídeo original salvo, a análise anterior, as memórias internas, os anexos da sessão e a observação do usuário como contexto.

## Como salvar observação como memória interna

As observações de correção são salvas em:

```text
data/knowledge_raw/feedback_aprendizado/
```

Status registrado:

```text
pendente de validação
```

## Onde ficam versões corrigidas

As versões corrigidas são salvas em `data/outputs/` com sufixo semelhante a:

```text
analise_x_v2_corrigida_YYYYMMDD_HHMMSS.xlsx
analise_x_v2_corrigida_YYYYMMDD_HHMMSS.json
```

Arquivos antigos não são apagados.

## Resultado dos testes

- `python -m pytest -q`: `131 passed, 1 warning in 180.22s`.

## Pendências reais

- Integração futura recomendada com SSO/Active Directory/Microsoft Entra ID.
- Validação formal das memórias de feedback antes de promover conhecimento como padrão aprovado.
