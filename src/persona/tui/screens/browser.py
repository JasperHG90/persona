from typing import cast, TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import DataTable, Input, Markdown, Static
from textual import work
from persona.types import personaTypes

if TYPE_CHECKING:
    from persona.tui.app import PersonaApp


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
        app = cast('PersonaApp', self.app)
        template_type = cast(personaTypes, self.type)
        if query:
            results = app.api.search_templates(
                query, template_type, columns=['name', 'description', 'uuid', 'score']
            )
        else:
            results = app.api.list_templates(template_type, columns=['name', 'description', 'uuid'])

        self.app.call_from_thread(self.update_table, results)

    def update_table(self, results: list[dict]) -> None:
        table = self.query_one(DataTable)
        table.clear()
        for r in results:
            table.add_row(*[str(v) for v in r.values()], key=r['name'])

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == f'search_{self.type}':
            self.load_data(event.value)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        row_data = event.data_table.get_row(event.row_key)
        name, description, uuid = row_data
        md = self.query_one(Markdown)
        md.update(f'# {name}\n\n{description}\n\n**UUID:** {uuid}')
