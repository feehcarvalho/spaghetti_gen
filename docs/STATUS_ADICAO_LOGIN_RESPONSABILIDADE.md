# Status - Adicao de Login e Responsabilidade

Data: 2026-05-21

## Arquivos novos

- `app/security/authorized_users.py`
- `app/security/audit_logger.py`
- `app/ui/auth.py`
- `app/ui/assets/.gitkeep`
- `data/security/authorized_logins.csv`
- `data/audit/login_events.csv`
- `docs/CONTROLE_ACESSO_E_RESPONSABILIDADE.md`
- `docs/STATUS_ADICAO_LOGIN_RESPONSABILIDADE.md`
- `tests/test_authorized_users.py`
- `tests/test_audit_logger.py`
- `tests/test_streamlit_auth_import.py`
- `tests/test_analysis_metadata_user.py`

## Arquivos existentes alterados

- `app/ui/streamlit_app.py`: adicionada barreira de login antes da interface principal, identificacao discreta do usuario na sidebar, botao `Sair` e valor padrao do responsavel com o usuario logado.
- `app/schemas/analysis.py`: adicionados campos opcionais de usuario e aceite em `AnalysisMetadata`, sem tornar nenhum campo obrigatorio.
- `README.md`: adicionada secao curta sobre controle local de acesso.

## Natureza da alteracao

A alteracao foi incremental e isolada. A interface principal so aparece depois de login autorizado e aceite de responsabilidade.

## Nao alterado

- Analise de video.
- Provider OpenAI.
- RAG/memorias.
- Geracao de Excel.
- Logica de microetapas.
- Prompts de analise.
- Downloads.
- Template padrao Scania.

## Resultado do pytest

- `python -m pytest -q`: suite completa chegou ao resumo `118 passed, 1 warning in 620.75s`; o wrapper do terminal encerrou logo depois por timeout operacional.
- Testes da nova camada e import da interface: `12 passed, 1 warning in 2.29s`.

## Como cadastrar novo login

Editar:

```text
data/security/authorized_logins.csv
```

Adicionar uma linha com `ativo=true`:

```csv
login,nome,area,perfil,ativo
m123456,Nome Sobrenome,Engenharia de Processos,user,true
```

Para bloquear, alterar `ativo` para `false`.

## Imagem de fundo

Colocar a imagem em um dos caminhos:

```text
app/ui/assets/login_background.png
app/ui/assets/login_background.jpg
app/ui/assets/login_background.jpeg
```

Logo opcional:

```text
app/ui/assets/logo.png
```

Se nao houver imagem, a tela usa fundo azul escuro simples.

## Como rodar

```bat
streamlit run app/ui/streamlit_app.py
```
