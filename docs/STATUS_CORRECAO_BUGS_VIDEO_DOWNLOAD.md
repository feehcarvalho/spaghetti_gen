# Status da Correcao de Bugs de Video e Download

Data/hora: 2026-05-05 15:43:50 -03:00

## 1. Causa do erro de PMGS repetido

O fluxo permitia usar provider `mock` mesmo quando havia video anexado. Como o mock usa `data/outputs/sample_analysis_pmgs_p1.json`, a aplicacao podia retornar uma analise demonstrativa PMGS para um video que nao era PMGS.

## 2. O que impede analise falsa

- `app/main.py` agora bloqueia `provider_name="mock"` quando `video_path` existe.
- `MockAnalysisProvider` tambem rejeita requisicoes com frames.
- O JSON mock recebe alerta: `Análise gerada em modo mock/demonstração. Não representa vídeo real.`
- Provider `openai` exige `OPENAI_API_KEY` e video anexado.
- Se uma analise real retornar exatamente o sample demonstrativo, o pipeline bloqueia com erro.

## 3. Upload de video

- A UI salva `UploadedFile` em `data/videos/uploads/{timestamp}_{nome}.ext`.
- Extensoes permitidas: `.mp4`, `.mov`, `.avi`, `.mkv`.
- O arquivo salvo e validado por existencia e tamanho antes de ser enviado ao OpenCV.
- A UI exibe nome, tamanho e caminho salvo.
- A opcao de extrair frames cria uma previa tecnica de ate 5 frames com timestamp.

## 4. Download da planilha

- O download so aparece se o Excel e o JSON existirem e tiverem tamanho maior que zero.
- Os bytes sao lidos com `open(..., "rb")`.
- A UI guarda em `st.session_state`:
  - `last_excel_path`
  - `last_json_path`
  - `last_analysis`
- Se a planilha nao existir, a UI mostra: `Planilha nao foi gerada. Verifique erros no pipeline.`

## 5. Resultado do pytest

Comando:

```bat
pytest -q
```

Resultado:

- 78 testes aprovados.
- 0 falhas.
- 1 aviso residual de cache do pytest por permissao no Windows.

## 6. Resultado do teste mock sem video

Comando:

```bat
python tools/run_pipeline.py --template data/templates/PMGS_P1_Analise_SPS_CORRIGIDA_2026-03-18.xlsx --output data/outputs/teste_mock_sem_video.xlsx --posto PMGS.P1 --processo "Pre-montagem da grade superior PMGS" --departamento "FUNCTION AREA 5" --responsavel "TESTE LOCAL" --takt 330 --provider mock --fill-standard
```

Resultado:

- Excel gerado: `data/outputs/teste_mock_sem_video.xlsx`
- JSON gerado: `data/outputs/teste_mock_sem_video.json`
- JSON validado com sucesso.
- Alerta de demonstracao presente no JSON.

## 7. Resultado do teste video + mock

Resultado esperado e confirmado:

```text
ValueError: Modo mock não analisa vídeo real. Use provider openai para analisar o vídeo.
```

Nenhuma analise PMGS falsa foi gerada.

## 8. Resultado do teste video + openai sem API key

Resultado esperado e confirmado:

```text
ValueError: OPENAI_API_KEY não configurada. Configure a chave para análise real de vídeo.
```

Nenhuma planilha falsa foi gerada.

## 9. Como rodar a interface

```bat
streamlit run app/ui/streamlit_app.py
```

Ou:

```bat
scripts\run_app.bat
```

URL local validada:

```text
http://localhost:8501
```

## 10. Pendencias reais

- A analise real de video depende do provider `openai` configurado.
- O modo mock e apenas demonstracao e nao interpreta video.
- Nao foi feita chamada OpenAI real nesta correcao.
- Validacao visual do Excel ainda deve ser feita por engenharia/lideranca.
