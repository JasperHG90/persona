from typing import Any

from persona.embedder import FastEmbedder
from persona.storage import BaseMetaStoreSession


def get_templates_data(
    meta_store_session: BaseMetaStoreSession, root: str, type: str
) -> list[dict[str, Any]]:
    """Get the templates currently available for a type as a list of dictionaries.

    Args:
        config (PersonaConfig): Persona configuration
        type (personaTypes): type of template to list
    """
    results = meta_store_session.get_many(
        table_name=type,
        column_filter=['name', 'description', 'uuid'],
    )

    data = []
    for result in results.to_pylist():
        data.append(
            {
                'name': result['name'],
                'path': '%s/%s/%s' % (root, type, result['name']),
                'description': result['description'],
                'uuid': result['uuid'],
            }
        )
    return data


def search_templates_data(
    query: str,
    embedder: FastEmbedder,
    meta_store_session: BaseMetaStoreSession,
    root: str,
    type: str,
    limit: int = 3,
    max_cosine_distance: float = 0.8,
) -> list[dict[str, Any]]:
    """Search templates based on a query and return data as a list of dictionaries.

    Args:
        config (PersonaConfig): Persona configuration
        query (str): query string to match
        type (str): type of template to search in
    """
    query_vector = embedder.encode([query]).squeeze().tolist()
    results = meta_store_session.search(
        query=query_vector,
        table_name=type,
        limit=limit,
        column_filter=['name', 'description', 'uuid'],
        max_cosine_distance=max_cosine_distance,
    )

    data = []
    for result in results.to_pylist():
        data.append(
            {
                'name': result['name'],
                'path': '%s/%s/%s' % (root, type, result['name']),
                'description': result['description'],
                'distance': result['score'],
                'uuid': result['uuid'],
            }
        )
    return data
