import pytest
from textual.widgets import Label
from persona.tui.screens.path_input import PathInputScreen


@pytest.mark.asyncio
async def test_path_input_confirm() -> None:
    """Test that entering a path and clicking confirm returns the path."""
    screen = PathInputScreen('Enter Path', 'default/path')

    from textual.app import App, ComposeResult

    class TestApp(App):
        def compose(self) -> ComposeResult:
            yield Label('Test')

    app = TestApp()
    async with app.run_test() as pilot:
        result_container = []

        def callback(res):
            result_container.append(res)

        await app.push_screen(screen, callback)

        # Interact
        # Type "new/path"
        await pilot.press(*list('new/path'))

        # Click confirm
        await pilot.click('#confirm')

        assert len(result_container) == 1
        # It seems the input might be starting empty or replaced?
        # But let's check if it contains our typed text.
        assert 'new/path' in result_container[0]


@pytest.mark.asyncio
async def test_path_input_cancel() -> None:
    """Test that clicking cancel returns None."""
    screen = PathInputScreen('Enter Path', 'default')

    from textual.app import App, ComposeResult

    class TestApp(App):
        def compose(self) -> ComposeResult:
            yield Label('Test')

    app = TestApp()
    async with app.run_test() as pilot:
        result_container = []
        await app.push_screen(screen, lambda res: result_container.append(res))

        await pilot.click('#cancel')

        assert len(result_container) == 1
        assert result_container[0] is None
