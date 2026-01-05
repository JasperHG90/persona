from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Input, Label, Button
from textual.containers import Vertical, Horizontal


class PathInputScreen(ModalScreen[str]):
    def __init__(self, title: str, initial_value: str = ''):
        super().__init__()
        self.dialog_title = title
        self.initial_value = initial_value

    def compose(self) -> ComposeResult:
        with Vertical(id='dialog'):
            yield Label(self.dialog_title)
            yield Input(value=self.initial_value, id='path_input')
            with Horizontal(id='buttons'):
                yield Button('Cancel', variant='error', id='cancel')
                yield Button('Confirm', variant='primary', id='confirm')

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == 'confirm':
            input_widget = self.query_one('#path_input', Input)
            self.dismiss(input_widget.value)
        else:
            self.dismiss(None)
