from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, TabbedContent, TabPane
from persona.config import PersonaConfig
from persona.tui.screens.browser import BrowserScreen

from persona.storage import get_meta_store_backend, CursorLikeMetaStoreEngine
from persona.embedder import get_embedding_model, FastEmbedder


class PersonaApp(App):
    CSS_PATH = 'css/styles.tcss'
    BINDINGS = [('q', 'quit', 'Quit')]

    def __init__(self, config: PersonaConfig):
        super().__init__()
        self.persona_config = config
        self.meta_store: CursorLikeMetaStoreEngine = (
            get_meta_store_backend(config.meta_store, read_only=True).connect().bootstrap()
        )
        self.embedder: FastEmbedder = get_embedding_model()

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            with TabPane('Roles', id='roles'):
                yield BrowserScreen(type='roles')
            with TabPane('Skills', id='skills'):
                yield BrowserScreen(type='skills')
        yield Footer()

    def on_unmount(self) -> None:
        self.meta_store.close()
