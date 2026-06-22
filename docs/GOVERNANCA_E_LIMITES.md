# Governança e Limites

## 1. Papel da IA

A IA apoia a análise de engenharia de processos. Ela não aprova mudança de método, layout, ferramenta, sequência, abastecimento ou padrão de trabalho.

Qualquer recomendação deve ser tratada como hipótese técnica a validar.

## 2. Validação no Gemba

Validação no gemba é obrigatória quando a análise envolver:

- alteração de método;
- alteração de sequência;
- mudança de layout;
- mudança de abastecimento;
- mudança de ferramenta;
- mudança de posto ou responsabilidade;
- impacto em segurança, qualidade, ergonomia ou rastreabilidade.

## 3. Não Responsabilizar Operador

A análise não deve culpar operador sem evidência objetiva.

Desperdícios devem ser descritos como efeito de:

- processo;
- layout;
- sistema;
- abastecimento;
- ergonomia;
- padrão de trabalho;
- disponibilidade de informação;
- condição operacional.

## 4. Nomenclatura

A IA não deve inventar siglas, nomes de peças, ferramentas, postos ou padrões.

Fontes aceitas:

- documentos em `data/knowledge_raw/corporativo`;
- documentos em `data/knowledge_raw/posicoes/{POSTO}`;
- metadados informados pelo usuário;
- evidência visível no vídeo;
- revisão humana.

Quando houver dúvida, o JSON deve registrar baixa confiança ou alerta de validação.

## 5. Baixa Confiança

Use baixa confiança quando:

- frame está borrado ou cortado;
- ação acontece fora de câmera;
- ferramenta ou peça não é identificável;
- tempo não pode ser medido com precisão;
- há inferência baseada apenas em contexto;
- há divergência entre vídeo e documento.

Quando `confianca < 0.7`, o campo `baixa_confianca_motivo` é obrigatório.

## 6. Controle de Versão dos Documentos

Documentos da base local devem ser versionados e revisados.

Recomendação:

- registrar responsável por alteração;
- registrar data;
- manter nomenclatura consistente;
- evitar duplicidade entre arquivos corporativos e por posição;
- revisar exemplos de microetapas após mudança real de processo.

## 7. Uso Produtivo

Antes de uso produtivo:

- obter aprovação da TI;
- definir política de dados e retenção;
- validar uso de API externa conforme regras corporativas;
- definir responsáveis por manutenção do template;
- definir governança para documentos SPS;
- definir processo de revisão humana;
- executar piloto controlado com posto conhecido.

## 8. Limites Técnicos

- O sistema não garante medição metrológica de tempo.
- A qualidade do vídeo limita a qualidade da análise.
- Structured Outputs reduz risco de JSON inválido, mas não elimina necessidade de revisão.
- O Excel gerado depende do template e dos mapeamentos atuais.
- Gráficos e spaghetti são apoio visual, não prova final de método.
