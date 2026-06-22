# Configuração do Ambiente e Como Rodar Testes

## 🔧 Requisitos

- **Python 3.10+**
- **pip** (gerenciador de pacotes Python)
- **pytest** (framework de testes)

## 📥 Instalação de Python

### Windows

1. **Desabilitar o atalho Microsoft Store** (se ativo):
   - Acesse: `Settings > Apps > App execution aliases`
   - Desabilite `App Installer` para `python.exe`

2. **Instalar Python**:
   - Baixe de [python.org](https://www.python.org/downloads/)
   - Ou instale via **Chocolatey** ou **Windows Package Manager**
   ```bash
   choco install python  # Se usar Chocolatey
   winget install Python.Python.3.11  # Se usar Windows Package Manager
   ```

3. **Verificar instalação**:
   ```bash
   python --version
   python -m pip --version
   ```

### Linux/macOS

```bash
sudo apt-get install python3.10 python3-pip  # Ubuntu/Debian
brew install python3  # macOS
```

## 📦 Instalar Dependências

```bash
cd ia_sps_scania

# Criar ambiente virtual (recomendado)
python -m venv venv
source venv/bin/activate  # Linux/macOS
# ou
venv\Scripts\activate  # Windows

# Instalar dependências de produção
pip install -r requirements.txt

# Instalar dependências de teste
pip install pytest pytest-cov
```

## 🧪 Rodar Testes

### Rodar todos os testes
```bash
pytest
```

### Rodar com verbosidade
```bash
pytest -v
```

### Rodar testes específicos
```bash
pytest tests/test_time_utils.py -v
pytest tests/test_schemas_analysis.py -v
```

### Rodar com cobertura
```bash
pytest --cov=app --cov=tests
```

### Rodar com output detalhado (traceback completo)
```bash
pytest -vv --tb=long
```

## ✅ Testes Inclusos

### test_time_utils.py
Testa funções de utilidade para manipulação de tempo:
- `seconds_to_mmss()`: Conversão de segundos para mm:ss
- `mmss_to_seconds()`: Conversão de mm:ss para segundos
- `calculate_time_summary()`: Cálculo de resumo de tempos AV/NAV/D

**Cobertura**:
- ✅ Conversão de 0, <60s, =60s, múltiplos minutos
- ✅ Arredondamento de floats
- ✅ Validações de entrada
- ✅ Erros com valores negativos, formatos inválidos, etc.
- ✅ Conversão ida e volta (round-trip)

### test_schemas_analysis.py
Testa schemas Pydantic para análise SPS:
- `AnalysisMetadata`: Metadados da análise
- `MicroStep`: Microetapa individual
- `TimeSummary`: Resumo de tempos
- `SpaghettiData`: Dados de spaghetti diagram
- `ImprovementSuggestion`: Sugestão de melhoria
- `OperationalAnalysis`: Análise completa

**Cobertura**:
- ✅ Validações de campos obrigatórios
- ✅ Validações de ranges (0-1, 0-100, etc)
- ✅ Validações de tipos e literais
- ✅ Validações cruzadas (fim >= inicio, percentuais somam 100%, etc)
- ✅ Erros com dados inválidos
- ✅ Cenários realistas de análise

## 📊 Resultados Esperados

Se tudo estiver configurado corretamente, os testes devem gerar saída similar a:

```
tests/test_time_utils.py::TestSecondsToMMss::test_zero_seconds PASSED
tests/test_time_utils.py::TestSecondsToMMss::test_less_than_one_minute PASSED
tests/test_time_utils.py::TestSecondsToMMss::test_exactly_one_minute PASSED
...
tests/test_schemas_analysis.py::TestAnalysisMetadata::test_valid_metadata PASSED
tests/test_schemas_analysis.py::TestMicroStep::test_valid_av_step PASSED
tests/test_schemas_analysis.py::TestMicroStep::test_fim_less_than_inicio_raises PASSED
...

============= XX passed in Y.XXs =============
```

## 🐛 Troubleshooting

### Erro: "ModuleNotFoundError: No module named 'app'"

**Solução**: Adicione o diretório raiz ao PYTHONPATH
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"  # Linux/macOS
# ou
$env:PYTHONPATH += ";$(Get-Location)"  # PowerShell Windows
```

Ou rode pytest da raiz do projeto:
```bash
cd ia_sps_scania
pytest
```

### Erro: "ModuleNotFoundError: No module named 'pydantic'"

**Solução**: Instale pydantic
```bash
pip install pydantic
```

### Testes falhando com "ValidationError"

Verifique se os dados de teste correspondem aos schemas. Revise:
- Campos obrigatórios vs opcionais
- Tipos (float vs int, str vs Literal)
- Ranges válidos (0-1, 0-100, etc)

## 📈 Métricas de Teste

| Métrica | Target | Atual |
|---------|--------|-------|
| Cobertura Code | >80% | - |
| Testes Passando | 100% | - |
| Tempo Execução | <5s | - |

## 🔗 Referências

- [Pytest Documentation](https://docs.pytest.org/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Python Official](https://www.python.org/)

---

**Status**: Testes prontos, aguardando Python instalado  
**Última atualização**: Maio/2026
