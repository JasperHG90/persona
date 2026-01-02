from typing import cast

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import DataTable, Input, Markdown, Static
from textual import work
from persona.types import personaTypes
from persona.utils import get_templates_data, search_templates_data
from persona.storage import CursorLikeMetaStoreEngine
from persona.embedder import FastEmbedder


class BrowserScreen(Static):
    def __init__(self, type: personaTypes):
        super().__init__()
        self.type = type

    def compose(self) -> ComposeResult:
        yield Input(placeholder=f'Search {self.type}...', id=f'search_{self.type}')
        with Horizontal():
            yield DataTable(id=f'table_{self.type}')
            yield Markdown(id=f'details_{self.type}')

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns('Name', 'Description', 'UUID')
        table.cursor_type = 'row'
        self.load_data()

    @work(exclusive=True, thread=True)
    def load_data(self, query: str = '') -> None:
        config = self.app.persona_config  # type: ignore
        with cast(
            CursorLikeMetaStoreEngine, getattr(self.app, 'meta_store')
        ).read_session() as meta_store_session:
            if query:
                results = search_templates_data(
                    query,
                    cast(FastEmbedder, getattr(self.app, 'embedder')),
                    meta_store_session,
                    config.root,
                    'roles' if self.type == 'roles' else 'skills',
                    limit=config.meta_store.similarity_search.max_results,
                    max_cosine_distance=config.meta_store.similarity_search.max_cosine_distance,
                )
            else:
                results = get_templates_data(
                    meta_store_session, config.root, 'roles' if self.type == 'roles' else 'skills'
                )

        self.app.call_from_thread(self.update_table, results)

    def update_table(self, results: list[dict]) -> None:
        table = self.query_one(DataTable)
        table.clear()
        for res in results:
            table.add_row(res['name'], res['description'], res['uuid'])

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == f'search_{self.type}':
            self.load_data(event.value)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        # For now, just show the description in the Markdown view
        # But it'd be cool to fetch the actual template file and render it
        #  NB: this probably needs (1) async, (2) caching
        row_data = event.data_table.get_row(event.row_key)
        name, description, uuid = row_data
        md = self.query_one(Markdown)
        md.update(f'# {name}\n\n{description}\n\n**UUID:** {uuid}')
