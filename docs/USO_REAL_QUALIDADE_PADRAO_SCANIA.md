# Uso real com qualidade de padrão Scania

## Objetivo

A aplicação apoia criação e revisão de padrão operacional SPS a partir de vídeo real, memórias internas, documentos anexados e validação humana. A IA não aprova padrão automaticamente.

## Investigação operacional

Para cada microetapa, a análise deve investigar ação, peça, ferramenta, dispositivo, sistema, local, lado, eixo, variante, ponto de montagem e quantidade quando houver evidência visual ou memória.

Se o detalhe estiver no vídeo, nas memórias ou no contexto operacional informado, ele pode ser usado na instrução. Se não estiver confirmado, a microetapa deve manter termo técnico genérico, registrar baixa confiança e marcar validação no gemba/SPS.

## Uso de memória

As memórias ficam em `data/knowledge_raw/` e podem incluir SPS, regras AV/NAV/D, dicionário do posto, fotos de referência, padrões, pontos críticos, uploads da sessão e feedback manual pendente.

Use o campo `Memória da IA / adicionar conhecimento` para anexar material novo. Use `Contexto operacional adicional` para orientar variante, eixo, lado, início/fim esperado e nomenclatura. Esses campos orientam a análise, mas não substituem evidência e validação.

## Linguagem

As microetapas finais devem ser instruções operacionais, não narração de vídeo.

Exemplos adequados:

- `Alinhar o pneu aos prisioneiros do cubo do segundo eixo, lado LD.`
- `Pegar a parafusadeira pneumática para executar o aperto conforme sequência do método.`
- `Deslocar o VR de pneu até o ponto de montagem informado.`

Evitar:

- `operador pega a peça`
- `pessoa movimenta`
- `posiciona ferramenta no ponto indicado`
- `realiza processo`

## Tempo

O Python é a fonte única da verdade para tempo:

- tempo do elemento = `fim_s - inicio_s`;
- tempo acumulado = soma progressiva dos tempos individuais;
- totais AV/NAV/D = soma dos tempos auditados;
- percentuais = cálculo do Python sobre o total auditado.

Valores vindos da IA são recalculados antes do quality gate e antes do Excel.

## Validação

Antes de usar o padrão:

- revisar microetapas no editor;
- validar nomenclatura no gemba/SPS;
- confirmar eixo, lado, variante e quantidade quando houver baixa confiança;
- confirmar classificações AV/NAV/D;
- validar melhorias com liderança/SPS quando houver alteração de método.

## Correção/refazer análise

Após a análise, use `Correção da análise` para informar ajustes de nomenclatura, início/fim do processo ou aderência ao método. A nova versão é salva sem apagar a anterior. Correções podem ser salvas como memória pendente de validação em `data/knowledge_raw/feedback_aprendizado/`.
