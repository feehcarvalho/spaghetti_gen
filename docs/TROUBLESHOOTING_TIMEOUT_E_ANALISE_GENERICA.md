# Timeout e analise generica

## Erro de timeout

Se aparecer "A analise excedeu o tempo limite", a chamada OpenAI demorou mais que o limite configurado. O pipeline tenta reduzir o tamanho da chamada analisando por janelas menores, sem fingir uma analise concluida.

Configuracao recomendada no `.env`:

```env
OPENAI_TIMEOUT_SECONDS=300
OPENAI_MAX_RETRIES=2
OPENAI_WINDOW_SECONDS=15
OPENAI_MAX_FRAMES_PER_WINDOW=10
OPENAI_IMAGE_DETAIL_WINDOW=auto
```

## Dividir e melhor que degradar

Reduzir todos os frames ou usar sempre baixa qualidade pode esconder acoes SPS importantes. A estrategia correta e dividir o video em janelas, analisar cada trecho e consolidar depois. Use qualidade baixa apenas no overview; a analise por janela deve ficar em `auto` ou `high` quando houver baixa confianca.

## Modos da interface

- Rapida: janelas de 20s, 6 frames por janela, `detail=low`. Use para triagem.
- Equilibrada: janelas de 15s, 10 frames por janela, `detail=auto`. Use como padrao.
- Detalhada: janelas de 10s, 14 frames por janela, `detail=high`. Use quando o processo tem muitas acoes curtas, oclusao ou baixa confianca.

## Analise generica ou repetida

Se a validacao detectar descricoes repetidas, exatamente a mesma lista de etapas para videos diferentes, mencao a PMGS sem contexto do usuario, descricoes vagas como "realiza operacao" ou timestamps incoerentes, a analise e bloqueada com:

```text
A análise retornou conteúdo genérico ou repetido. Reprocessar com mais frames/contexto.
```

Nesse caso, use modo Equilibrada ou Detalhada, reduza documentos anexados irrelevantes, confirme que o video cobre o ciclo completo e valide no gemba quando a camera nao mostrar a acao.
