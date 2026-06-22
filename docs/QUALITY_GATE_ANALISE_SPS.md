# Quality gate da analise SPS

O quality gate decide se a analise pode seguir para Excel. Ele nao aprova mudanca de metodo; apenas valida se o JSON esta consistente para preencher a planilha padrao.

## Bloqueia Excel

O Excel e bloqueado quando houver:

- Analise generica ou repetida.
- Vazamento de PMGS em video sem contexto/metadados PMGS.
- Timestamps invalidos ou duracoes incoerentes.
- Microetapas vazias.
- Microetapas sem justificativa tecnica.
- Etapa D sem melhoria ou alerta.
- Provider mock/demonstracao usado com video real.
- Maioria das microetapas fora do modo imperativo/instrucional.

## Gera alerta

Gera alerta quando houver:

- Quantidade de microetapas que aparenta padrao fixo.
- Termo interno sem evidencia/contexto suficiente.
- Microetapa generica ou narrativa.
- AV sem transformacao clara.
- Janela nao analisada, timeout parcial ou checkpoint incompleto.
- Baixa cobertura temporal do video.
- Baixa confianca ou nomenclatura nao confirmada.

## Quando reprocessar

Reprocessar em `Maxima qualidade / producao` quando houver analise generica, muitas etapas com baixa confianca, janelas falhadas, timeout parcial ou cobertura temporal insuficiente.

## Quando validar no gemba

Validar no gemba/SPS sempre que houver incerteza visual, proposta de mudanca de metodo, layout, abastecimento, ferramenta, sequencia, padrao de trabalho, balanceamento ou classificacao AV/NAV/D duvidosa.
