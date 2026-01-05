from typing import cast, TYPE_CHECKING
import pathlib as plb

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, Center, VerticalScroll
from textual.widgets import DataTable, Input, Markdown, Static, Button
from textual import work
from persona.types import personaTypes
from persona.tui.screens.path_input import PathInputScreen

if TYPE_CHECKING:
    from persona.tui.app import PersonaApp


class BrowserScreen(Static):
    def __init__(self, type: personaTypes):
        super().__init__()
        self.type = type
        self.selected_name: str | None = None
        self.full_definition: bytes | None = None

    def compose(self) -> ComposeResult:
        yield Input(placeholder=f'Search {self.type}...', id=f'search_{self.type}')
        with Horizontal():
            yield DataTable(id=f'table_{self.type}')
            with Vertical(id='right_pane'):
                with VerticalScroll(id=f'scroll_{self.type}'):
                    yield Markdown(id=f'details_{self.type}')
                with Center(id='action_container'):
                    action_label = 'Save Role' if self.type == 'roles' else 'Install Skill'
                    yield Button(action_label, id=f'action_{self.type}', disabled=True)

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
                query, template_type, columns=['name', 'description', 'uuid']
            )
        else:
            results = app.api.list_templates(template_type, columns=['name', 'description', 'uuid'])

        self.app.call_from_thread(self.update_table, results)

    def update_table(self, results: list[dict]) -> None:
        table = self.query_one(DataTable)
        table.clear()
        for r in results:
            table.add_row(
                *[str(v) for k, v in r.items() if k in ['name', 'description', 'uuid']],
                key=r['name'],
            )

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == f'search_{self.type}':
            self.load_data(event.value)

    @work(exclusive=True, thread=True)
    def load_definition(self, name: str) -> None:
        app = cast('PersonaApp', self.app)
        try:
            definition_bytes = app.api.get_definition(name, self.type)
            content = definition_bytes.decode('utf-8')
            self.app.call_from_thread(self.on_definition_loaded, content, definition_bytes)
        except Exception as e:
            self.app.call_from_thread(self.update_details, f'Error loading definition: {e}')

    def on_definition_loaded(self, content: str, definition_bytes: bytes) -> None:
        self.full_definition = definition_bytes
        self.update_details(content)
        self.enable_action_button()

    def enable_action_button(self) -> None:
        btn = self.query_one(f'#action_{self.type}', Button)
        btn.disabled = False

    def update_details(self, content: str) -> None:
        md = self.query_one(Markdown)
        md.update(content)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        row_data = event.data_table.get_row(event.row_key)
        name = row_data[0]
        self.selected_name = name

        # Reset state
        self.full_definition = None
        self.query_one(Markdown).update('Loading definition...')
        self.query_one(f'#action_{self.type}', Button).disabled = True

        self.load_definition(name)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == f'action_{self.type}' and self.selected_name:
            if self.type == 'roles':
                default_path = str(
                    plb.Path.cwd() / '.persona' / 'roles' / self.selected_name / 'ROLE.md'
                )
                self.app.push_screen(
                    PathInputScreen('Save Role to...', default_path), self.save_role
                )
            elif self.type == 'skills':
                default_path = str(plb.Path.cwd() / '.persona' / 'skills' / self.selected_name)
                self.app.push_screen(
                    PathInputScreen('Install Skill to directory...', default_path),
                    self.install_skill,
                )

    def save_role(self, path_str: str | None) -> None:
        if not path_str or not self.full_definition:
            return
        path = plb.Path(path_str)
        if not path.is_absolute():
            path = plb.Path.cwd() / path
        self.perform_save_role(path, self.full_definition)

    @work(exclusive=True, thread=True)
    def perform_save_role(self, path: plb.Path, content: bytes) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'wb') as f:
                f.write(content)
            self.app.call_from_thread(self.app.notify, f'Role saved to {path}')
        except Exception as e:
            self.app.call_from_thread(self.app.notify, f'Error saving role: {e}', severity='error')

    def install_skill(self, path_str: str | None) -> None:
        if not path_str or not self.selected_name:
            return
        path = plb.Path(path_str)
        if not path.is_absolute():
            path = plb.Path.cwd() / path
        self.perform_install_skill(self.selected_name, path)

    @work(exclusive=True, thread=True)
    def perform_install_skill(self, name: str, path: plb.Path) -> None:
        app = cast('PersonaApp', self.app)
        try:
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
            app.api.install_skill(name, path)
            self.app.call_from_thread(self.app.notify, f'Skill installed to {path}')
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, f'Error installing skill: {e}', severity='error'
            )
