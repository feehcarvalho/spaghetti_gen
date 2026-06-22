# Manual Técnico

Este manual descreve a arquitetura, configuração e operação técnica do projeto.

## 1. Arquitetura

Fluxo principal:

1. `app/video/frame_extractor.py` extrai frames do vídeo.
2. `app/knowledge/local_retriever.py` recupera contexto SPS local.
3. `app/ai/analyzer.py` executa provider `mock` ou `openai`.
4. `app/schemas/analysis.py` valida o JSON `OperationalAnalysis`.
5. `app/ui/review_editor.py` permite revisão humana e recalcula resumo.
6. `app/excel/template_writer.py` copia o template e escreve o Excel final.
7. `app/excel/balance_chart.py` gera gráfico AV/NAV/D opcional.
8. `app/spaghetti/map_generator.py` gera mapa de espaguete opcional.

## 2. Pastas

- `app/`: código da aplicação.
- `app/ai/`: providers, prompt e chamada OpenAI.
- `app/excel/`: preenchimento do template, Standard, gráficos.
- `app/knowledge/`: base local de conhecimento.
- `app/schemas/`: modelos Pydantic.
- `app/ui/`: interface Streamlit e editor de revisão.
- `app/video/`: extração de frames.
- `data/templates/`: templates Excel.
- `data/knowledge_raw/`: documentos SPS por corporativo/posição.
- `data/layouts/`: layouts JSON para spaghetti.
- `data/outputs/`: Excel, JSON e imagens geradas.
- `docs/`: documentação.
- `tools/`: CLIs utilitários.
- `scripts/`: atalhos Windows.
- `tests/`: testes automatizados.

## 3. Variáveis de Ambiente

Copie `.env.example` para `.env` e ajuste:

```bat
copy .env.example .env
```

Variáveis principais:

- `OPENAI_API_KEY`: chave da OpenAI. Nunca commitar.
- `OPENAI_MODEL`: modelo usado no provider real. Default recomendado: `gpt-4.1-mini`.
- `OPENAI_MAX_FRAMES`: limite de frames enviados.
- `OPENAI_IMAGE_DETAIL`: detalhe das imagens, default `low`.
- `OPENAI_TIMEOUT_S`: timeout da chamada.
- `OPENAI_MAX_OUTPUT_TOKENS`: limite de saída.
- `OPENAI_DEBUG_DIR`: pasta para respostas brutas inválidas.
- `EXCEL_TEMPLATE_PATH`: caminho padrão do template.

## 4. Instalação Windows

```bat
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 5. Rodar a UI

```bat
scripts\run_app.bat
```

Ou:

```bat
.venv\Scripts\streamlit.exe run app\ui\streamlit_app.py
```

## 6. Rodar Testes

```bat
scripts\run_tests.bat
```

Ou:

```bat
.venv\Scripts\python.exe -m pytest
```

## 7. Provider Mock e OpenAI

Provider mock:

- não exige API;
- usa `data/outputs/sample_analysis_pmgs_p1.json`;
- indicado para testes de UI, Excel e revisão.

Provider OpenAI:

- exige `OPENAI_API_KEY`;
- usa Responses API;
- valida retorno com schema Pydantic;
- tenta correção automática uma vez se o JSON vier inválido;
- salva resposta bruta em `data/outputs/debug` se a correção falhar.

Exemplo:

```bat
scripts\run_pipeline_mock.bat
```

## 8. Atualizar Template Excel

1. Coloque o novo `.xlsx` em `data/templates/`.
2. Não edite o template pelo código.
3. Rode:

```bat
.venv\Scripts\python.exe tools\inspect_excel_template.py data\templates\NOME_DO_TEMPLATE.xlsx
```

4. Atualize mapeamentos em `app/excel/template_writer.py` ou `app/excel/standard_writer.py` somente se necessário.
5. Rode testes.

Regra crítica: nunca recriar o workbook. Sempre copiar o template e editar somente células mapeadas.

## 9. Diagnóstico de Erro

Erros comuns:

- API key ausente: configurar `OPENAI_API_KEY` ou usar `mock`.
- SDK OpenAI ausente/desatualizado: reinstalar `requirements.txt`.
- Template sem aba obrigatória: rodar `tools/inspect_excel_template.py`.
- Vídeo inválido: confirmar que o arquivo é `.mp4` e abre localmente.
- JSON inválido: rodar `tools/validate_analysis_json.py`.
- Layout spaghetti inválido: validar `data/layouts/{POSTO}.json`.

Comandos úteis:

```bat
.venv\Scripts\python.exe tools\validate_analysis_json.py data\outputs\sample_analysis_pmgs_p1.json
.venv\Scripts\python.exe tools\retrieve_context.py "analisar PMGS.P1 VR farol" --position PMGS.P1
.venv\Scripts\python.exe tools\extract_frames.py data\videos\exemplo.mp4 data\frames\exemplo --fps 1 --max-frames 120
```
