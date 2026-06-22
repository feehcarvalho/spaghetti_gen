@echo off
setlocal
cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
    echo ERRO: Ambiente .venv nao encontrado.
    echo Execute:
    echo   py -3 -m venv .venv
    echo   .venv\Scripts\python.exe -m pip install -r requirements.txt
    exit /b 1
)

set "TEMPLATE=data\templates\PMGS_P1_Analise_SPS_CORRIGIDA_2026-03-18.xlsx"
if not exist "%TEMPLATE%" (
    set "TEMPLATE=PMGS_P1_Analise_SPS_CORRIGIDA_2026-03-18.xlsx"
)

if not exist "%TEMPLATE%" (
    echo ERRO: Template Excel nao encontrado.
    echo Esperado em data\templates ou na raiz do projeto.
    exit /b 1
)

".venv\Scripts\python.exe" tools\run_pipeline.py ^
  --template "%TEMPLATE%" ^
  --output data\outputs\analise_pipeline_mock.xlsx ^
  --posto PMGS.P1 ^
  --processo "Pre montagem da grade superior (PMGS)" ^
  --departamento "FUNCTION AREA 5" ^
  --responsavel "MARIANE" ^
  --takt 330 ^
  --provider mock ^
  --fill-standard ^
  --insert-charts ^
  --insert-spaghetti ^
  --layout data\layouts\PMGS.P1.json

exit /b %ERRORLEVEL%
