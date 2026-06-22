"""Base de conhecimento local."""

__all__ = [
    "KnowledgeDocument",
    "bootstrap_docs",
    "load_text_documents",
    "retrieve_context",
]


def __getattr__(name):
    if name == "bootstrap_docs":
        from app.knowledge.bootstrap_docs import bootstrap_docs

        return bootstrap_docs

    if name in {"KnowledgeDocument", "load_text_documents", "retrieve_context"}:
        from app.knowledge import local_retriever

        return getattr(local_retriever, name)

    raise AttributeError(name)
