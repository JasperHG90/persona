from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, TabbedContent, TabPane
from persona.config import PersonaConfig
from persona.tui.screens.browser import BrowserScreen

from persona.api import PersonaAPI


class PersonaApp(App):
    CSS_PATH = 'css/styles.tcss'
    BINDINGS = [('q', 'quit', 'Quit')]

    def __init__(self, config: PersonaConfig):
        super().__init__()
        self.persona_config = config
        self.api = PersonaAPI(config)

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            with TabPane('Roles', id='roles'):
                yield BrowserScreen(type='roles')
            with TabPane('Skills', id='skills'):
                yield BrowserScreen(type='skills')
        yield Footer()
