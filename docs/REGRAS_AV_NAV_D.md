# Regras de Classificação: AV, NAV e D

## 🎯 Objetivo

Estabelecer critérios precisos e objetivos para classificar cada etapa de um processo conforme sua relação com agregação de valor, necessidade operacional e desperdício, dentro da metodologia Lean Manufacturing / SPS Scania.

---

## 📌 Definições Fundamentais

### AV (Agrega Valor)

**Definição**: Etapa que transforma diretamente o produto de forma visível e esperada pelo cliente.

**Características**:
- Muda a forma, função ou propriedade do produto
- Do ponto de vista do cliente externo
- Necessária para atingir especificação
- Sem AV, o cliente não pagaria por ela

**Exemplos Industriais (Scania/Automotivo)**:
- ✅ Montar componente no chassis
- ✅ Soldar estrutura ou junta
- ✅ Pintar superfície
- ✅ Apertar parafuso de fixação crítica
- ✅ Furar ou usinar peça
- ✅ Testar funcionamento elétrico
- ✅ Embalar produto final
- ✅ Encaixar peça em subconjunto

**Características de Confiança Alta**:
- Visível no vídeo como transformação clara
- Etapa consta em especificação de produto
- Cliente reconheceria resultado diferente se não feito
- Takt time está associado principalmente a AV

---

### NAV (Não Agrega Valor, mas Necessário)

**Definição**: Etapa que NÃO transforma o produto, mas é necessária por motivos de processo, qualidade, segurança ou sistema para que o trabalho avance ou seja válido.

**Características**:
- Não é visível no produto final
- Mas sem ela, processo não funciona ou fica inválido
- Pode ser otimizada (reduzir, mas não eliminar)
- Geralmente associada a burocracia, validação, abastecimento

**Exemplos Industriais (Scania/Automotivo)**:
- ✅ Apontar ou registrar etapa no sistema (MES/SAP)
- ✅ Conferir peça antes de montar (inspeção de entrada)
- ✅ Abastecer componentes no carro ou kit
- ✅ Posicionar peça para próxima operação (reposicionar)
- ✅ Retirar peça defeituosa da linha para reparação
- ✅ Limpar área de trabalho entre operações
- ✅ Documentar teste de funcionamento
- ✅ Inspecionar acabamento visual
- ✅ Etiquetar ou marcar rastreabilidade
- ✅ Colocar peça em espera no buffer

**Critério de Diferenciação**:
- Se conseguir eliminar completamente sem impacto negativo = é D
- Se apenas reduzir tempo, mas precisa continuar existindo = é NAV
- Se eliminar causa ineficiência ou risco = é NAV

---

### D (Desperdício / Muda)

**Definição**: Atividade que consome tempo e recursos SEM agregar valor E SEM ser necessária para o funcionamento do processo.

**Características**:
- Pode ser eliminada imediatamente ou através de melhoria
- Não impacta produto, qualidade, segurança ou conformidade se removida
- Resultado de ineficiência, falta de padrão ou design inadequado
- Tipicamente associada aos 8 desperdícios Lean

**Exemplos Industriais (Scania/Automotivo)**:
- ❌ Esperar por material que deveria estar pronto
- ❌ Procurar ferramenta ou peça no posto (desorganização)
- ❌ Caminhar desnecessariamente (layout ruim, falta de 5S)
- ❌ Retrabalhar peça com erro de primeira
- ❌ Mover peça múltiplas vezes dentro da mesma célula
- ❌ Aguardar autorização desnecessária
- ❌ Conferir mesma coisa duas vezes (falta de padrão)
- ❌ Ajustar máquina quando deveria estar pré-ajustada
- ❌ Caminhar para longe buscar ferramenta que deveria estar no posto
- ❌ Esperar por máquina quando não era esperado (desvio de padrão)

---

## 🏭 Matriz de Decisão

| Transforma Produto? | Necessário no Processo? | Classificação | Exemplo |
|:---:|:---:|:---:|---|
| ✅ Sim | ✅ Sim | **AV** | Montar, soldar, pintar, furar |
| ✅ Sim | ❌ Não | **D** | Retrabalho (transformaria se feito certo na primeira) |
| ❌ Não | ✅ Sim | **NAV** | Conferir, abastecer, apontar, inspecionar |
| ❌ Não | ❌ Não | **D** | Procurar, esperar, caminhar desnecessário |

---

## 🔍 Regras de Decisão Específicas

### Teste da Eliminação

Para decidir entre AV e NAV:
- **"Se eu eliminar esta etapa completamente, o produto fica conforme especificação?"**
  - ✅ SIM → AV
  - ❌ NÃO → Continua

- **"Se eu eliminar, há risco de qualidade, segurança, rastreabilidade ou conformidade?"**
  - ✅ SIM → NAV
  - ❌ NÃO → D

### Teste do Cliente

Para validar AV:
- **"O cliente externo teria que aprovar ou validar este resultado se não fosse feito?"**
  - ✅ SIM → Provavelmente AV
  - ❌ NÃO → Provavelmente NAV ou D

### Teste do Padrão

Para NAV vs D:
- **"Existe procedimento/padrão SPS/Scania que exige esta etapa?"**
  - ✅ SIM → NAV
  - ❌ NÃO → D

### Teste de Observabilidade

Para qualquer classificação:
- **"O vídeo/descrição deixa claro o que está acontecendo?"**
  - ✅ CLARO → Classificação com confiança alta
  - ⚠️ AMBÍGUO → Sinalizar baixa confiança
  - ❌ INVISÍVEL → Não classificar, reportar incerteza

---

## 📋 Exemplos Completos: Processo de Montagem Automotiva

### Exemplo 1: Montar Volante
```
Etapa: "Operador pega volante do kit, encaixa no comando de direção, aperta 3 parafusos"

Análise:
- Transforma o produto? ✅ SIM (adiciona volante ao veículo)
- Necessário? ✅ SIM (cliente espera volante)
- Visível no produto final? ✅ SIM
- Teste do cliente? ✅ SIM (cliente valida)

Classificação: AV ✅
```

### Exemplo 2: Abastecer Kit de Componentes
```
Etapa: "Abastecedor coloca peças nas gavetas do carro, confere quantidade"

Análise:
- Transforma o produto? ❌ NÃO (apenas posiciona materiais)
- Necessário? ✅ SIM (sem abastecimento, operador não consegue trabalhar)
- É eliminável? ❌ NÃO (causaria parada de produção)
- Há padrão? ✅ SIM (5S, Kanban, abastecimento é atividade padrão)

Classificação: NAV ✅
```

### Exemplo 3: Procurar Chave de Fenda
```
Etapa: "Operador procura por 2 minutos a chave de fenda que não está no local padrão"

Análise:
- Transforma o produto? ❌ NÃO
- Necessário? ❌ NÃO (ferramenta deveria estar pronta)
- É eliminável? ✅ SIM (implementar 5S, quadro de ferramentas)
- Violação de padrão? ✅ SIM (desvio de Gemba)

Classificação: D ✅
Tipo de Desperdício: Movimento + 5S não implementado
```

### Exemplo 4: Conferir Peça Antes de Montar
```
Etapa: "Operador verifica dimensão e acabado da peça antes de montar no chassis"

Análise:
- Transforma o produto? ❌ NÃO (apenas valida)
- Necessário? ✅ SIM (qualidade, não montar peça ruim)
- É eliminável? ❌ NÃO (risco de passar defeito)
- Há procedimento? ✅ SIM (inspeção de entrada é padrão)

Classificação: NAV ✅
Otimização possível: Reduzir amostragem, usar automação (Fase futura)
```

### Exemplo 5: Aguardar Peça do Fornecedor Externo
```
Etapa: "Linha inteira fica parada por 15 minutos esperando chegada de subconjunto de outro departamento"

Análise:
- Transforma o produto? ❌ NÃO
- Necessário? ✅ Sim, para continuar
- MAS: É eliminável? ✅ SIM (melhorar síncrono, kanban, buffer)
- Viola padrão? ✅ SIM (não deveria ter parada)

Classificação: D ✅
Tipo de Desperdício: Espera + Problem Solving necessário
```

### Exemplo 6: Retrabalho de Parafuso Solto
```
Etapa: "Operador volta no passo anterior, aperta parafuso que ficou solto"

Análise:
- Transforma o produto? ✅ SIM (completa montagem corretamente)
- Necessário? ✅ SIM (produto precisa estar correto)
- MAS: Por que precisa desta etapa? ❌ NÃO deveria (erro de primeira)

Classificação: D ✅
Tipo de Desperdício: Retrabalho
Root Cause: Verificar por que parafuso ficou solto (poka-yoke, treinamento)
```

---

## 📊 Matriz de Confiança

Ao classificar, também informar nível de confiança:

| Confiança | Situação | O quê Fazer |
|:---:|---|---|
| **Alta** (> 90%) | Etapa clara, visível, padrão conhecido | Classificar e prosseguir |
| **Média** (70–90%) | Etapa parcialmente clara, alguns assumidos | Classificar + anotar suposição |
| **Baixa** (< 70%) | Etapa ambígua, vídeo ruim, falta contexto | Sinalizar `low_confidence_flag` |
| **Muito Baixa** (< 50%) | Impossível classificar com segurança | Não classificar, solicitar clarificação |

**Campos a Incluir**:
```json
{
  "classification": "AV | NAV | D",
  "confidence": 0.95,
  "justification": "descricao objetiva do por que",
  "low_confidence_flag": false ou true,
  "observation": "notas adicionais se confiança < 0.7"
}
```

---

## 🚨 Casos Especiais e Ambíguidades

### Teste vs Inspeção

- **Teste funcional pós-montagem** (máquina liga?) → **NAV**
  - Necessário por qualidade e segurança
- **Inspeção visual redundante** (já foi verificado antes?) → **D**
  - Se primeira verificação foi adequada
- **Inspeção de amostra estatística** → **NAV**
  - Necessário por processo de qualidade

### Setup de Máquina

- **Setup inicial do turno** → **NAV**
  - Necessário para máquina funcionar
- **Ajuste entre peças já configuradas** → **NAV ou D** conforme padrão
  - Se faz parte de SMED/Quick Change = NAV
  - Se é falta de preparação = D
- **Regulagem por erro de trocador** → **D**
  - Deveria ter sido feito antes

### Movimentação Interna

- **Pegar peça do kit padrão** → **AV** (parte de montagem)
- **Transportar peça 3 metros para posição correta** → **NAV** (necessário para operação)
- **Caminhar 20 metros buscar peça perdida** → **D** (deveria estar no kit)
- **Posicionar peça para câmera inspecionar** → **NAV** (necessário para inspeção)

### Paradas Inesperadas

- **Esperar autorização programada** → **NAV**
- **Esperar por problema imprevisto** → **D**
  - Reportar como desperdício de tipo "Espera"
  - Iniciar problem solving

---

## 🔄 Reclassificação e Melhoria

Uma etapa pode mudar de classificação através de melhoria:

| Etapa Antes | Ação | Etapa Depois |
|---|---|---|
| D (Espera) | Implementar kanban | NAV (Abastecimento programado) |
| NAV (Conferência) | Automação de inspeção | D (eliminada) ou mantém NAV |
| NAV (Apontar) | Sistema automático | D (eliminada) |
| NAV (Setup) | SMED / Quick Change | Reduzir, pode se aproximar de AV |

---

## 📝 Template de Análise Passo-a-Passo

Para cada etapa observada:

```
Etapa #: [numero]
Descrição: [o que faz, observável]
Duração: [tempo em segundos]

Análise de Classificação:
1. Transforma o produto? [ ] Sim [ ] Não
2. Necessário no processo? [ ] Sim [ ] Não
3. Cliente valida o resultado? [ ] Sim [ ] Não
4. Há padrão SPS/Scania? [ ] Sim [ ] Não [ ] Incerto

Classificação Proposta: [ ] AV [ ] NAV [ ] D
Justificativa: [resumo em 1–2 frases]

Confiança: [ ] Alta (>90%) [ ] Média (70–90%) [ ] Baixa (<70%)
Se Baixa, por quê: [falta de informação, ambiguidade, etc.]

Tipo de Desperdício (se D): [ ] Espera [ ] Transporte [ ] Retrabalho [ ] Movimento [ ] Superprocessamento [ ] Inventário [ ] Superprodução [ ] Talento

Observação Adicional: [notas relevantes]
```

---

## 🔗 Integração com IA

A IA deve:
1. Extrair etapas do vídeo/texto
2. Aplicar regras de classificação acima
3. Calcular confiança conforme nível de evidência
4. Justificar com referência a regra específica
5. Sinalizar `low_confidence_flags` quando apropriado
6. Permitir override do especialista

---

**Versão**: 1.0  
**Data**: Maio/2026  
**Próxima Revisão**: Conforme feedback de análises  
**Responsável**: Engenharia de Processos / SPS
