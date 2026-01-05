from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, TabbedContent, TabPane
from persona.config import PersonaConfig
from persona.tui.screens.browser import BrowserScreen

from persona.api import PersonaAPI
from persona.storage import get_file_store_backend, get_meta_store_backend
from persona.embedder import get_embedding_model


class PersonaApp(App):
    CSS_PATH = 'css/styles.tcss'
    BINDINGS = [('q', 'quit', 'Quit')]

    def __init__(self, config: PersonaConfig):
        super().__init__()
        self.persona_config = config
        meta_store = get_meta_store_backend(config.meta_store, read_only=True).connect().bootstrap()
        file_store = get_file_store_backend(config.file_store)
        embedder = get_embedding_model()
        self.api = PersonaAPI(
            config,
            meta_store=meta_store,
            file_store=file_store,
            embedder=embedder,
        )

    def on_unmount(self) -> None:
        self.api._meta_store.close()

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            with TabPane('Roles', id='roles'):
                yield BrowserScreen(type='roles')
            with TabPane('Skills', id='skills'):
                yield BrowserScreen(type='skills')
        yield Footer()
