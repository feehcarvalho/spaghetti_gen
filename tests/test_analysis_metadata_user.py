from app.schemas.analysis import AnalysisMetadata


def test_analysis_metadata_accepts_optional_user_fields():
    metadata = AnalysisMetadata(
        departamento="Engenharia",
        posto="5.2.6",
        processo="Montagem 8x2",
        responsavel="Administrador Local (admin)",
        data_analise="2026-05-21",
        usuario_login="admin",
        usuario_nome="Administrador Local",
        usuario_area="Engenharia",
        aceite_responsabilidade_em="2026-05-21T12:00:00",
    )

    assert metadata.usuario_login == "admin"
    assert metadata.usuario_nome == "Administrador Local"


def test_analysis_metadata_keeps_user_fields_optional():
    metadata = AnalysisMetadata(
        departamento="Engenharia",
        posto="5.2.6",
        processo="Montagem 8x2",
        responsavel="Engenheiro de Processos",
        data_analise="2026-05-21",
    )

    assert metadata.usuario_login is None
