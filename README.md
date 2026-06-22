# IA SPS Scania

Aplicacao local de apoio a engenharia de processos SPS/Lean. O fluxo gera uma analise estruturada em JSON, permite revisao humana das microetapas e so depois preenche uma copia da planilha padrao Scania.

## Entregavel do MVP

- Tabela da analise do processo antes do Excel.
- Microetapas observaveis com inicio, fim, duracao, tempo acumulado, classificacao AV/NAV/D e justificativa tecnica.
- Resumo AV/NAV/D recalculado pelo Python.
- Lista de desperdicios e melhorias com validacao no gemba/SPS.
- Excel final gerado a partir do template existente, preservando abas, formulas, imagens, graficos e layout.

## Instalacao no Windows

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

O provider `mock` funciona sem chave de API.

Para usar o provider `openai`, crie `.env` a partir de `.env.example` e configure:

```bat
OPENAI_API_KEY=<sua-chave-openai>
OPENAI_MODEL=gpt-4.1-mini
```

Nunca commit `.env`.

## Rodar testes

```bat
pytest -q
```

Ou:

```bat
scripts\run_tests.bat
```

## Rodar interface

```bat
streamlit run app/ui/streamlit_app.py
```

Ou:

```bat
scripts\run_app.bat
```

A interface abre normalmente em `http://localhost:8501`.

## Controle local de acesso

Ao abrir a interface, a aplicacao exibe uma tela obrigatoria de login e aceite de responsabilidade SPS. Os logins autorizados ficam em `data/security/authorized_logins.csv`; somente linhas com `ativo=true` liberam acesso.

Eventos de acesso sao registrados em `data/audit/login_events.csv`. Este controle local nao substitui SSO/Active Directory, mas registra o usuario e o aceite antes da analise.

## Correcao da analise e memoria da IA

A memoria da IA fica em uma area auxiliar na sidebar e pode receber documentos, imagens de referencia ou observacoes de nomenclatura para complementar o RAG local.

Apos gerar a analise, use `Correcao da analise` para orientar a IA e refazer uma nova versao sem apagar a anterior. Observacoes relevantes podem ser salvas em `data/knowledge_raw/feedback_aprendizado/` como memoria de feedback manual pendente de validacao.

## Uso real e integracao Sheet2

Antes do Excel, os tempos das microetapas sao recalculados pelo Python: tempo do elemento = fim - inicio, e tempo acumulado = soma progressiva. O Excel gerado tambem inclui `Sheet2` como segunda aba para integracao com o app da automacao logistica, com o cabecalho tecnico `timeOfElement` preservado conforme contrato.

Veja `docs/USO_REAL_QUALIDADE_PADRAO_SCANIA.md` e `docs/CONTRATO_SHEET2_APP_AUTOMACAO.md`.

## Rodar pipeline mock

```bat
python tools/run_pipeline.py --template data/templates/PMGS_P1_Analise_SPS_CORRIGIDA_2026-03-18.xlsx --output data/outputs/teste_interface_mock.xlsx --posto PMGS.P1 --processo "Pre-montagem da grade superior PMGS" --departamento "FUNCTION AREA 5" --responsavel "TESTE LOCAL" --takt 330 --provider mock --fill-standard
```

Saidas esperadas:

- `data/outputs/teste_interface_mock.xlsx`
- `data/outputs/teste_interface_mock.json`

## Fluxo da interface

1. Selecione ou envie o template Excel.
2. Envie video MP4 se houver. Em mock, video nao e obrigatorio.
3. Preencha departamento, posto, processo, responsavel, data e takt.
4. Selecione provider `mock` para teste local.
5. Clique em `Processar analise SPS`.
6. Revise a `Tabela da analise do processo`.
7. Gere o Excel final revisado.
8. Baixe o Excel e o JSON final.

## Regras criticas

- Nao recriar a planilha Excel do zero.
- Nao modificar o template original.
- Sempre copiar o template para `data/outputs` antes de escrever.
- Nao alterar formulas, imagens, graficos, referencias ou abas fora das celulas mapeadas.
- A IA ou mock deve retornar JSON validado por `OperationalAnalysis`.
- O Python recalcula tempos, percentuais, acumulado, graficos e escrita Excel.
- Nao inventar nomenclatura.
- Nao inventar etapas nao observaveis.
- Sinalizar baixa confianca quando houver incerteza.
- Toda mudanca de processo exige validacao no gemba/SPS.
- O operador nao deve ser responsabilizado sem evidencia.

## Estrutura principal

```text
app/
  main.py
  config.py
  schemas/
  ai/
  video/
  knowledge/
  excel/
  spaghetti/
  ui/
  utils/

data/
  templates/
  videos/
  frames/
  knowledge_raw/
  outputs/
  layouts/

docs/
tests/
tools/
scripts/
```

## Documentacao

- `docs/MANUAL_USUARIO.md`
- `docs/MANUAL_TECNICO.md`
- `docs/GOVERNANCA_E_LIMITES.md`
- `docs/CHECKLIST_VALIDACAO_GEMBA.md`
- `docs/COMO_CADASTRAR_NOVA_POSICAO.md`
- `docs/USO_REAL_QUALIDADE_PADRAO_SCANIA.md`
- `docs/CONTRATO_SHEET2_APP_AUTOMACAO.md`
- `docs/STATUS_FINAL_MVP.md`


## Teste de conexão com a OpenAI

Crie um arquivo `.env` na raiz do projeto com:

```env
OPENAI_API_KEY=sua_chave_aqui
OPENAI_MODEL=gpt-4.1-mini
APP_ENV=local
```

Depois rode no Windows:

```bat
python tools\test_openai_connection.py
```

Ou em Linux/Mac:

```bash
python tools/test_openai_connection.py
```

A chave real deve ficar apenas no `.env`, nunca no código.
