# Roadmap MVP - Fases de Desenvolvimento

## 📅 Visão Geral

O desenvolvimento do **ia_sps_scania** será executado em 8 fases, do MVP básico até a versão corporativa endurecida. Cada fase constrói sobre a anterior, com entregas claras e critérios de sucesso.

---

## 🎯 Fases e Timeline

### Fase 1: Estrutura, Schemas e Mock Manual

**Objetivo**: Estabelecer fundação, documentação e estrutura de dados.

**Tarefas**:
- [x] Criar estrutura de pastas
- [x] Documentação: BRIEFING_SPS, REGRAS_AV_NAV_D, mapeamento Excel
- [x] Schemas Pydantic para Análise, Etapa, Melhoria, Desperdício
- [ ] Arquivo config.py com constantes e variáveis de ambiente
- [ ] Arquivo main.py básico
- [ ] Model mock: simular análise JSON completa
- [ ] Testes unitários para schemas

**Entrega**:
- Estrutura de projeto pronta
- Schemas validando JSON de análise
- Mock que gera JSON conforme especificação

**Sucesso**: Conseguir gerar JSON completo manualmente, sem IA

**Timeline**: Semana 1

---

### Fase 2: Preenchimento Excel Automático

**Objetivo**: Transformar JSON de análise em arquivo Excel padrão Scania.

**Tarefas**:
- [ ] Implementar `excel/writer.py` para escrita em template
- [ ] Copiar template padrão Scania
- [ ] Validar mapeamento JSON → Excel (conforme `docs/TEMPLATE_EXCEL_MAP.md`)
- [ ] Preservação de fórmulas e abas standard
- [ ] Tratamento de erros (arquivo locked, estrutura quebrada)
- [ ] Testes de saída Excel
- [ ] Logging de operações

**Entrega**:
- Arquivo Excel preenchido a partir de JSON
- Relatório validado e formatado
- Preservação de integridade do template

**Sucesso**: Gerar arquivo Excel válido e editável a partir de JSON mock

**Timeline**: Semana 2

---

### Fase 3: Extração de Frames de Vídeo

**Objetivo**: Processar vídeo e extrair frames para análise.

**Tarefas**:
- [ ] Implementar `video/extractor.py` com OpenCV
- [ ] Extração de frames em intervalo configurável (ex: 1 frame/s)
- [ ] Armazenamento em `data/frames/` com metadados
- [ ] Detecção de cena/transição (opcional)
- [ ] Validação de qualidade de vídeo
- [ ] Tratamento de formatos múltiplos (MP4, AVI, MOV, MKV)

**Entrega**:
- Banco de frames extraídos com timestamps
- Metadados indexados (vídeo_id, frame_id, timestamp)
- Pronto para análise IA

**Sucesso**: Extrair frames de vídeo real com qualidade suficiente

**Timeline**: Semana 3

---

### Fase 4: Análise IA via API OpenAI

**Objetivo**: Integrar IA para classificação automática AV/NAV/D.

**Tarefas**:
- [ ] Implementar `ai/orchestrator.py` para orquestração
- [ ] Criar prompt mestre em `docs/PROMPT_MESTRE_ANALISE_SPS.md`
- [ ] Integração com OpenAI API (GPT-4 Vision para imagens)
- [ ] Decomposição em etapas de frames
- [ ] Classificação AV/NAV/D com confiança
- [ ] Identificação de desperdícios
- [ ] Sugestões de melhoria
- [ ] Tratamento de API errors e rate limiting
- [ ] Caching de respostas IA

**Entrega**:
- JSON completo de análise gerado pela IA
- Confiança calculada para cada etapa
- Low confidence flags ativados quando apropriado

**Sucesso**: IA gera análise razoável sem intervenção manual

**Confiança Mínima**: 70% para prosseguir sem validação

**Timeline**: Semana 4

---

### Fase 5: Base de Conhecimento / RAG Local

**Objetivo**: Implementar knowledge base para melhorar precisão da IA.

**Tarefas**:
- [ ] Indexar documentação SPS, manuais, procedimentos padrão
- [ ] Implementar RAG (Retrieval-Augmented Generation)
- [ ] Embeddings locais ou via API (text-embedding-3-small)
- [ ] Banco de conhecimento em `data/knowledge_index/`
- [ ] Integração com prompt IA para contexto adicional
- [ ] Versionamento de conhecimento
- [ ] Interface para adicionar conhecimento novo

**Entrega**:
- IA usa base de conhecimento SPS para contexto
- Precisão melhorada em classificações
- Sugestões mais alinhadas com padrão corporativo

**Sucesso**: IA cita fonte de conhecimento em justificativas

**Timeline**: Semana 5

---

### Fase 6: Interface Streamlit

**Objetivo**: Criar UI interativa para engenheiros e líderes.

**Tarefas**:
- [ ] Implementar `ui/app.py` com Streamlit
- [ ] Upload de vídeo / texto / JSON
- [ ] Visualização de frames com anotações
- [ ] Tabela interativa de etapas com edição
- [ ] Gráficos de AV/NAV/D (pizza, barras)
- [ ] Visualização de desperdícios e melhorias
- [ ] Download de Excel gerado
- [ ] Histórico de análises
- [ ] Validação e correção manual de etapas
- [ ] Integração com backend (Fase 7)

**Entrega**:
- Interface amigável e responsiva
- Fluxo intuitivo para analista
- Exportação de relatórios

**Sucesso**: Engenheiro consegue fazer análise completa sem terminal

**Timeline**: Semana 6

---

### Fase 7: Spaghetti, Balanceamento e Validação

**Objetivo**: Análises avançadas de fluxo e otimização.

**Tarefas**:
- [ ] Implementar `spaghetti/analyzer.py` para mapeamento de fluxo
- [ ] Extração de coordenadas (manual ou via imagem + ML)
- [ ] Cálculo de distância percorrida
- [ ] Geração de spaghetti diagram visual
- [ ] Análise de balanceamento entre postos
- [ ] Sugestões de layout otimizado
- [ ] Validação de takt vs ciclo
- [ ] Relatório de capacidade e folga
- [ ] Integração com análise de desperdício

**Entrega**:
- Mapa visual de fluxo com distâncias
- Análise de desbalanceamento
- Recomendações de rebalanceamento

**Sucesso**: Identificar desbalanceamento em linha multi-posto

**Timeline**: Semana 7

---

### Fase 8: Endurecimento para Uso Corporativo

**Objetivo**: Preparar para produção com governança, auditoria e suporte.

**Tarefas**:
- [ ] Implementar FastAPI backend (produção)
- [ ] Autenticação e autorização (LDAP/OAuth)
- [ ] Auditoria: log de todas as análises
- [ ] Versionamento de análises (histórico completo)
- [ ] Aprovação de mudanças (workflow SPS)
- [ ] Integração com sistema de gestão (MES, ERP)
- [ ] Backup automático
- [ ] Monitoramento e alertas
- [ ] Documentação de deployment
- [ ] Treinamento de usuários
- [ ] SLA e suporte

**Entrega**:
- Aplicação pronta para ambiente corporativo
- Auditória completa
- Integração com sistemas Scania

**Sucesso**: Primeira análise em produção realizada com sucesso

**Timeline**: Semana 8+

---

## 📊 Dependências Entre Fases

```
Fase 1 (Estrutura)
    ↓
Fase 2 (Excel) ← usa schemas da Fase 1
    ↓
Fase 3 (Vídeo) ← fornece frames para Fase 4
    ↓
Fase 4 (IA) ← gera JSON que Fase 2 converte em Excel
    ↓
Fase 5 (Knowledge) ← melhora Fase 4
    ↓
Fase 6 (UI) ← integra Fases 2, 3, 4, 5
    ↓
Fase 7 (Avançado) ← análise adicional de Fase 6
    ↓
Fase 8 (Produção) ← integra tudo com governança
```

---

## 🎯 Critérios de Sucesso por Fase

| Fase | Critério | Métrica |
|:---:|---|---|
| 1 | Schemas validam 100% de JSON teste | pytest passando |
| 2 | Excel gerado = template intacto + dados preenchidos | Excel válido, fórmulas funcionando |
| 3 | Frames extraídos com qualidade | 98%+ frames legíveis |
| 4 | IA classifica etapas com confiança média > 80% | Validação manual confirma 90% |
| 5 | RAG reduz erros de classificação em 15% | Comparação antes/depois |
| 6 | UI consegue fazer análise completa | Teste com 3 usuários |
| 7 | Desbalanceamento detectado em 95% dos casos | Validação com especialista |
| 8 | 0 crashes em produção por 30 dias | Monitoramento |

---

## 🚀 Velocidade e Milestones

### MVP Rápido (4 semanas)
**Fases 1–3**: Estrutura + Excel + Vídeo
- Resultado: Análise manual em arquivo Excel

### MVP Funcional (8 semanas)
**Fases 1–5**: Tudo acima + IA + Knowledge
- Resultado: Análise automática com IA

### MVP com UI (10 semanas)
**Fases 1–6**: Tudo acima + Streamlit
- Resultado: Aplicação interativa e usável

### Produção (12+ semanas)
**Fases 1–8**: Tudo + robustez e governança
- Resultado: Aplicação corporativa pronta

---

## 🔄 Iterações e Feedback

Após cada fase:
1. **Review com stakeholders**: Especialista SPS, liderança
2. **Feedback**: Ajustes necessários
3. **Ajustes**: Implementar antes de próxima fase
4. **Go/No-Go**: Decisão de prosseguir

---

## 📈 Métricas de Progresso

- **Linhas de código**: Target 10k–15k para MVP completo
- **Cobertura de testes**: Target > 80%
- **Documentação**: Target 100% de código produção documentado
- **Performance**: Análise de 30min vídeo em < 5 minutos
- **Acurácia IA**: Target > 85% AV/NAV/D corretos

---

## 🛠️ Stack Técnico

- **Backend**: Python 3.10+, FastAPI (Fase 8)
- **Processamento**: OpenCV, NumPy, Pandas
- **IA**: OpenAI API, LangChain
- **Excel**: OpenPyXL
- **UI**: Streamlit (Fase 6+)
- **BD**: SQLAlchemy (Fase 8+)
- **Testing**: Pytest

---

## 📞 Responsabilidades por Fase

| Fase | Engenheiro | QA | Product |
|:---:|---|---|---|
| 1 | Design schemas | Validar | Aprovar estrutura |
| 2 | Escrita Excel | Testar saída | - |
| 3 | Extração vídeo | Validar frames | - |
| 4 | Integração IA | Validar confiança | Tunning prompt |
| 5 | Knowledge base | Testar RAG | Adicionar docs |
| 6 | UI Streamlit | UX testing | Feedback usuário |
| 7 | Análise avançada | Validar matemática | Aprovação |
| 8 | Deployment | Segurança | Go-live |

---

**Versão**: 1.0  
**Data Inicio**: Maio/2026  
**Data Esperada MVP**: Junho/2026  
**Próxima Revisão**: Fim de cada fase
