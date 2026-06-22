#!/usr/bin/env python
from dotenv import load_dotenv
from pathlib import Path
import os

# Check if .env exists
env_path = Path('.env')
print(f"Arquivo .env existe: {env_path.exists()}")
print(f"Caminho absoluto: {env_path.resolve()}")

# Load the .env file
load_dotenv(env_path)

# Check the API key
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    print(f"OPENAI_API_KEY carregada: {api_key[:20]}...")
else:
    print("OPENAI_API_KEY NÃO ENCONTRADA!")

# Check other vars
print(f"APP_ENV: {os.getenv('APP_ENV')}")
print(f"OPENAI_MODEL: {os.getenv('OPENAI_MODEL')}")
