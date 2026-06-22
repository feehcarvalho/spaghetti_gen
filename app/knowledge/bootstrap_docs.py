"""Bootstrap de documentos Markdown iniciais para conhecimento local."""

from __future__ import annotations

from pathlib import Path


DEFAULT_ROOT = Path(__file__).resolve().parents[2] / "data" / "knowledge_raw"


DOCUMENTS = {
    "corporativo/regras_av_nav_d.md": """# Regras AV NAV D

AV agrega valor quando transforma o produto de forma visivel e necessaria para especificacao.
Exemplos: montar, encaixar, colar adesivo, apontar farol na grade quando isso altera o estado do conjunto, apertar com apertadeira em junta especificada.

NAV nao agrega valor ao produto final, mas e necessario por qualidade, seguranca, rastreabilidade, sistema ou sequenciamento.
Exemplos: verificar WO no WPO, check-in visual, preparar VR, posicionar talha, conferir LD/LE, registrar KD ou ROP quando exigido.

D e desperdicio eliminavel sem prejudicar qualidade, seguranca ou conformidade.
Exemplos: procurar componente, caminhar ate abastecimento distante, aguardar liberacao sem trabalho, retrabalho, espera em IHM, deslocamento causado por layout ruim.

Nunca culpar o operador. Relacione desperdicios ao processo, abastecimento, layout, sistema, padrao, ergonomia ou disponibilidade de informacao.
""",
    "corporativo/nomenclatura_sps.md": """# Nomenclatura SPS

HOPE/Bluebox: ambiente ou sistema de apoio usado para consulta, apontamento, acompanhamento ou informacao operacional.
WO: work order ou ordem de trabalho. Pode aparecer no WPO para confirmar produto, variante e sequencia.
KD: knocked-down ou kit/condicao relacionada a abastecimento conforme contexto local.
ROP: ponto/registro operacional de producao ou referencia de processo conforme nomenclatura interna.

LD significa lado direito. LE significa lado esquerdo.
VR e um recurso/dispositivo de pega, suporte ou manipulacao usado para posicionar subconjuntos.
Talha e equipamento de suspensao auxiliar para movimentar pecas.
Apertadeira e ferramenta de torque para fixacao especificada.
IHM e interface homem-maquina usada para comando, apontamento ou leitura de status.
""",
    "corporativo/scania_way.md": """# Scania Way

O Scania Way orienta melhoria continua, respeito pelas pessoas, qualidade na fonte e decisao baseada no gemba.
Analises devem descrever fatos observaveis, sinalizar incertezas e propor melhorias praticas de processo.

Nao atribuir causa raiz a comportamento individual sem evidencia. Priorizar padrao, fluxo, ergonomia, abastecimento, informacao e estabilidade.
""",
    "corporativo/scania_house.md": """# Scania House

A casa SPS sustenta fluxo estavel, trabalho padronizado, qualidade, seguranca e melhoria continua.
Ao analisar uma operacao, relacionar desperdicios a pilares como padrao, fluxo, abastecimento, ergonomia, qualidade e desenvolvimento de pessoas.
""",
    "posicoes/PMGS.P1/padrao_posicao.md": """# Padrao da Posicao PMGS.P1

PMGS.P1 corresponde a pre-montagem de grade superior.
A operacao pode envolver verificacao de WO/WPO, uso de VR, talha, manipulacao de grade, colagem de adesivos, chicote, costelas/ribs, farol LD, farol LE, T-bone e apontamentos.

Separar microetapas por acao observavel: verificar WO, selecionar tarefa, deslocar ao abastecimento, suspender com VR, check-in visual, colar adesivo, pegar farol LD/LE, apontar farol, aguardar liberacao e posicionar VR no proximo posto.
""",
    "posicoes/PMGS.P1/pontos_criticos.md": """# Pontos Criticos PMGS.P1

Pontos criticos recorrentes:
- Confirmar variante antes de montar LD/LE.
- Evitar troca de farol LD com LE.
- Validar posicionamento de costelas/ribs e T-bone.
- Observar esperas em IHM, HOPE/Bluebox ou WPO.
- Identificar caminhadas ate caixas de abastecimento e falta de ponto de uso.
- Garantir uso seguro de talha e VR.
""",
    "posicoes/PMGS.P1/dicionario_posto.md": """# Dicionario do Posto PMGS.P1

VR: dispositivo usado para pegar, sustentar ou posicionar grade e subconjuntos.
Costelas/ribs: nervuras ou componentes estruturais da grade.
T-bone: componente de formato T usado como referencia local de montagem.
Chicote: conjunto eletrico roteado ou posicionado na grade.
Farol LD: farol do lado direito.
Farol LE: farol do lado esquerdo.
Talha: equipamento de elevacao.
Apertadeira: ferramenta de torque.
IHM: interface de maquina/sistema.
HOPE/Bluebox: sistema de apoio ou visualizacao.
""",
    "posicoes/PMGS.P1/exemplos_microetapas.md": """# Exemplos de Microetapas PMGS.P1

Exemplos:
- Verificar WO no WPO e confirmar produto/variante: NAV.
- Selecionar tarefa no WPO: NAV.
- Ir ate caixas de abastecimento: D se o deslocamento for causado por falta de ponto de uso.
- Suspender grade superior com VR: NAV ou AV conforme transformacao observavel; se apenas prepara montagem, NAV.
- Check-in visual da peca: NAV.
- Colar adesivo na grade: AV.
- Pegar farol LD ou LE: AV quando faz parte direta da montagem imediata; NAV se for somente preparacao logistica.
- Apontar farol na grade: AV se posiciona/monta; NAV se for apenas registro de sistema.
- Aguardar apontamento/liberacao: D quando a espera e eliminavel.
- Posicionar VR no proximo posto: NAV.
""",
}


def bootstrap_docs(root_dir: str | Path = DEFAULT_ROOT) -> list[Path]:
    """Cria documentos iniciais se ainda nao existirem."""

    root = Path(root_dir)
    created: list[Path] = []

    for relative_path, content in DOCUMENTS.items():
        path = root / relative_path
        if path.exists():
            continue

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content.strip() + "\n", encoding="utf-8")
        created.append(path)

    return created


if __name__ == "__main__":
    created_files = bootstrap_docs()
    print(f"Documentos criados: {len(created_files)}")
    for path in created_files:
        print(path)
