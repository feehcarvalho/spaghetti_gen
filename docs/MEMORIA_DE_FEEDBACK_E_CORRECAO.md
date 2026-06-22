# Memoria de Feedback e Correcao

Data: 2026-05-28

## Objetivo

As observacoes manuais feitas apos uma analise agora sao salvas como memoria operacional pendente de validacao. A intencao e fazer com que a proxima reanalise e analises futuras usem a correcao do usuario como contexto de alta prioridade, sem transformar automaticamente a informacao em padrao oficial.

## Onde o feedback e salvo

Modulo principal:

`app/knowledge/feedback_memory.py`

Diretorio padrao:

`data/knowledge_raw/feedback_aprendizado/`

Nome do arquivo:

`feedback_{timestamp}_{posto}_{processo}_{usuario}.md`

Cada memoria registra:

- data/hora;
- usuario/login;
- posto;
- processo;
- video;
- analysis_id;
- status;
- escopo;
- texto da correcao;
- regras gerais extraidas;
- observacao de validacao SPS/gemba.

## Status

O status inicial e:

`pending_validation`

Isso significa que a memoria pode orientar a IA, mas ainda requer validacao SPS/gemba antes de virar padrao oficial.

## Escopos

`process_specific`

Usado para feedback especifico de posto/processo. Exemplo: "Nesse processo, o operador pega as porcas na Green Box/caixa verde antes de montar o pneu."

Esse tipo de memoria so entra quando o posto/processo e igual ou claramente relacionado.

`general_language_rule`

Usado para regra geral de escrita, granularidade ou qualidade de microetapas. Exemplo: "Nao repetir varias linhas para pegar e movimentar o mesmo pneu; consolidar quando for a mesma intencao operacional."

O sistema tambem extrai regras gerais simples mesmo quando o feedback inteiro e salvo como `process_specific`.

## Como entra na reanalise

O fluxo de correcao cria uma nota em:

`data/outputs/corrections/session_context/`

Essa nota contem uma secao no topo:

`CORRECAO DO USUARIO — PRIORIDADE ALTA`

Na reanalise, a OpenAI recebe essa observacao junto com a analise anterior e as memorias. A instrucao e reprocessar o video, preservar o que estava correto e corrigir sequencia, nomenclatura, granularidade e tempos quando necessario.

## Como entra nas proximas analises

`build_sps_context_for_analysis` agora carrega feedbacks relacionados e adiciona uma secao:

`MEMORIAS DE FEEDBACK MANUAL PENDENTES DE VALIDACAO`

Essas memorias entram depois das regras corporativas e antes dos trechos documentais selecionados. Feedback especifico nao contamina processos sem relacao; regra geral de linguagem pode ser reutilizada em outros processos.

## Quality gate

Foi adicionada a funcao:

`validate_feedback_was_applied(analysis, feedback_text)`

Ela verifica se a nova analise ainda desobedece a correcao, por exemplo:

- Green Box/caixa verde ainda virou Bluebox;
- metodo manual ainda virou parafusadeira pneumatica;
- repeticao apontada pelo usuario continua;
- ferramenta/metodo/detalhe sem evidencia continua.

No fluxo "Refazer analise com observacoes", se a validacao falhar, o Excel e bloqueado antes da geracao.

Mensagem esperada:

`A análise não incorporou a correção do usuário. Reprocessar antes de gerar Excel.`

## Aprovacao futura

Hoje o feedback nasce como `pending_validation`. Para virar padrao oficial, a memoria deve ser revisada por SPS/gemba e entao marcada futuramente como validada. Ate la, a IA deve usar como orientacao e registrar validacao quando aplicar informacao especifica do processo.

## Testes

Cobertura adicionada:

`tests/test_feedback_memory_application.py`

Valida:

- salvamento da memoria;
- status `pending_validation`;
- associacao a posto/processo/video/usuario;
- entrada no contexto;
- prompt de reanalise com prioridade alta;
- bloqueio quando feedback nao foi aplicado;
- Green Box versus Bluebox;
- manual versus pneumatica;
- reducao de repeticao;
- isolamento de processo;
- reaproveitamento de regra geral de linguagem.
