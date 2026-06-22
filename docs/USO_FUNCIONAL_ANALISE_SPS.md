# Uso funcional da analise SPS por video

Este fluxo processa video real de operacao para apoiar engenharia de processos, lideranca e SPS/Lean Manufacturing. O objetivo nao e descrever imagens; e transformar evidencia visual em microetapas de processo, classificar AV/NAV/D, auditar tempos e gerar dados para a planilha padrao Scania.

## Como rodar video real

1. Abra a interface Streamlit da aplicacao.
2. Anexe o video da operacao.
3. Anexe memorias SPS, padroes de posto, nomenclaturas ou documentos da sessao quando existirem.
4. Preencha departamento, linha, bloco, posto, processo, responsavel e takt medio.
5. Use a opcao padrao `Maxima qualidade / producao`.
6. Processe a analise, revise as microetapas e gere o Excel apenas se a validacao SPS passar.

## Por que processar por janelas

Videos medios e longos nao devem ser enviados em uma chamada unica. A aplicacao cria um indice temporal do video inteiro, extrai frames representativos e pontos de mudanca visual, divide o video em janelas adaptativas e analisa cada trecho separadamente. Isso preserva qualidade, reduz risco de timeout e permite retomada por checkpoint.

## Por que a quantidade de microetapas varia

Nao existe numero fixo de microetapas. O total depende do processo observado. Acoes distintas como deslocar, pegar, selecionar, posicionar, fixar, apertar, conectar, inspecionar, apontar, aguardar, procurar e retornar devem ser separadas quando forem observaveis.

## Como a IA usa memorias

Antes da analise, o sistema monta um contexto SPS compacto com regras AV/NAV/D, regras SPS, nomenclatura Scania, dicionario do posto, padrao da posicao, pontos criticos, exemplos revisados e documentos anexados. Termos internos sao usados apenas quando houver memoria ou evidencia visual/contextual suficiente.

## Como a linguagem e normalizada

As microetapas finais sao escritas como instrucao de processo, no modo imperativo/instrucional. Exemplo: `O operador pega a peca` deve virar `Pegar a peca no ponto indicado`. Se a nomenclatura correta nao estiver confirmada, a analise usa termo tecnico generico e marca baixa confianca.

## Como tempos sao auditados

O Python recalcula duracao, tempo acumulado, totais AV/NAV/D e percentuais. Buracos temporais, sobreposicoes e divergencias com a duracao do video geram alertas antes da planilha.

## Como timeout e tratado

Timeout de janela gera retry. Se persistir, a janela e subdividida. O sistema salva debug sem API key e checkpoint por janela. Uma janela falhada nao gera microetapa falsa; ela gera alerta para validacao.

## Validacao no gemba

Analise por video e amostra observada. Mudancas de metodo, layout, abastecimento, ferramenta, sequencia ou padrao exigem validacao SPS/gemba/lideranca antes de aplicacao.
