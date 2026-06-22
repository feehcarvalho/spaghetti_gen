# Manual do Usuário

Este manual orienta o uso da aplicação IA SPS Scania por engenharia, liderança e especialistas SPS.

## 1. Abrir a Aplicação

No Windows, abra o terminal na pasta do projeto e execute:

```bat
scripts\run_app.bat
```

Alternativa manual:

```bat
.venv\Scripts\streamlit.exe run app\ui\streamlit_app.py
```

A aplicação abrirá no navegador. O provider padrão é `mock`, indicado para testes sem custo e sem chave de API.

## 2. Carregar Vídeo

1. No campo `Video MP4 opcional`, selecione um arquivo `.mp4`.
2. Marque `Extrair frames do video` quando quiser que a análise use imagens do vídeo.
3. Ajuste `FPS de extracao` conforme o custo aceitável.
4. Ajuste `Max frames` para limitar o envio à IA. Use valores menores para testes.

Se não houver vídeo, o modo `mock` ainda permite testar o fluxo de revisão e Excel.

Importante: o provider `mock` nao analisa video real. Se um video for anexado com provider `mock`, a aplicacao bloqueia a analise para evitar resultado falso de demonstracao. Use provider `openai` com `OPENAI_API_KEY` configurada para analise real de video.

## 3. Informar Dados da Análise

Preencha os campos principais:

- `Departamento`: área responsável.
- `Linha`: opcional.
- `Bloco`: opcional.
- `Posto`: exemplo `PMGS.P1`.
- `Processo`: nome técnico do processo analisado.
- `Responsavel`: pessoa responsável pela análise.
- `Data da analise`: data da observação.
- `Takt time em segundos`: takt vigente para comparação.
- `Observacoes do usuario`: contexto útil para a IA ou para o revisor.

Selecione o provider:

- `mock`: usa análise de exemplo, sem API.
- `openai`: usa a API real, exige `OPENAI_API_KEY`.

Opções adicionais:

- `Preencher abas Standard`: preenche abas Standard existentes.
- `Inserir grafico AV/NAV/D`: insere gráfico de balanceamento.
- `Inserir mapa de espaguete`: exige layout JSON do posto.

## 4. Revisar Microetapas

Depois de clicar em `Processar analise SPS`, a aplicacao mostra a `Tabela da analise do processo` antes de gerar o Excel.

A tabela exibe:

- numero da etapa;
- descricao tecnica detalhada;
- inicio observavel;
- fim observavel;
- duracao;
- tempo acumulado;
- classificacao AV/NAV/D;
- justificativa tecnica;
- confianca;
- observacao/ferramenta.

Campos editáveis:

- `inicio_s`
- `fim_s`
- `duracao_s`
- `classificacao`
- `etapa_detalhada`
- `justificativa_tecnica`
- `ferramenta_observacao`

Após editar, clique em `Gerar Excel final revisado`.

O sistema revalida o JSON com Pydantic e recalcula:

- tempos AV/NAV/D;
- percentuais;
- folga vs takt;
- alertas de validação.

## 5. Gerar Excel

O Excel final só é criado após a revisão humana.

O sistema:

- copia o template;
- preserva abas, fórmulas, imagens e formatação;
- escreve somente células mapeadas;
- salva o JSON final ao lado do Excel.

Use os botões de download para baixar:

- Excel final;
- JSON final.

## 6. Interpretar AV/NAV/D

- `AV`: agrega valor, transforma o produto ou executa montagem/ajuste requerido.
- `NAV`: não transforma o produto, mas é necessário por rastreabilidade, segurança, qualidade, sistema, padrão ou condição atual.
- `D`: desperdício removível ou reduzível, como espera, procura, deslocamento desnecessário, retrabalho ou excesso de movimento.

Toda classificação deve ter justificativa técnica.

## 7. Interpretar Melhorias

As melhorias indicam oportunidades associadas principalmente a etapas `D`.

Antes de implementar:

- valide no gemba;
- envolva segurança, qualidade e liderança quando houver mudança de método;
- confirme se a causa é processo, layout, abastecimento, sistema ou padrão;
- não trate a sugestão como aprovação automática.

Use o arquivo [CHECKLIST_VALIDACAO_GEMBA.md](CHECKLIST_VALIDACAO_GEMBA.md) antes de aceitar mudanças.
