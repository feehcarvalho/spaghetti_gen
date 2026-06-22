# Analise real de video SPS

Esta aplicacao nao usa PMGS como resposta padrao para videos reais. O provider OpenAI nao carrega `sample_analysis_pmgs_p1.json`; esse arquivo permanece apenas como demonstracao offline do provider `mock`, que e bloqueado quando existe video anexado.

## Como o pipeline funciona

1. O video e lido com metadados tecnicos: duracao, FPS, resolucao, quantidade de frames e tamanho.
2. Frames JPEG representativos sao extraidos ao longo de todo o video, mantendo timestamp real.
3. O video inteiro e dividido em janelas temporais, normalmente de 15 segundos, sem limitar a quantidade final de microetapas.
4. A IA faz um overview visual para entender processo aparente, objetos, ferramentas, ciclo completo/parcial e limitacoes da camera.
5. Cada janela e analisada separadamente. A IA deve gerar somente acoes observaveis naquela janela.
6. O Python consolida as janelas, ordena por tempo, renumera, remove duplicidades obvias, corrige pequenas sobreposicoes e recalcula duracao, acumulado, totais e percentuais AV/NAV/D.
7. A validacao SPS bloqueia conteudo generico, repetido ou com cara de template.
8. Toda etapa D gera melhoria ou alerta com validacao obrigatoria no gemba.
9. A planilha Scania so e gerada depois de uma `OperationalAnalysis` valida.

## Microetapas dinamicas

A lista final nao tem quantidade fixa. Se o video mostrar duas acoes distintas, a analise pode ter duas microetapas. Se mostrar quinze acoes distintas, pode ter quinze. A decisao vem da evidencia visual: pegar, transportar, posicionar, montar, apertar, inspecionar, apontar, aguardar, procurar e retrabalhar sao acoes separadas quando observaveis.

## Confianca e gemba

Quando uma acao nao esta clara, a microetapa recebe baixa confianca e alerta. Quando nao ha evidencia visual suficiente, o resultado deve registrar: "não conclusivo pelo vídeo; requer validação no gemba". A analise por IA representa a condicao observada no video, nao um padrao oficial aprovado.

## Timeout sem perder qualidade

Timeout nao e tratado por uma reducao agressiva do video inteiro. O sistema usa janelas, poucas imagens por chamada, retry controlado e, quando necessario, subdivide a janela que falhou. Janelas de baixa confianca podem ser reprocessadas com `detail="high"` e contexto mais focado.
