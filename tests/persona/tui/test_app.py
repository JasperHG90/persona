import pytest
from persona.tui.app import PersonaApp
from persona.tui.screens.browser import BrowserScreen
from textual.widgets import Header, Footer, TabbedContent


@pytest.mark.asyncio
async def test_app_startup(mock_app: PersonaApp) -> None:
    """Test that the app starts up and composes correctly."""
    async with mock_app.run_test() as pilot:
        await pilot.pause()

        assert mock_app.query_one(Header)
        assert mock_app.query_one(Footer)
        assert mock_app.query_one(TabbedContent)

        # Check tabs
        browsers = mock_app.query(BrowserScreen)
        assert len(browsers) == 2

        roles = mock_app.query_one('#roles BrowserScreen', BrowserScreen)
        assert roles.type == 'roles'

        skills = mock_app.query_one('#skills BrowserScreen', BrowserScreen)
        assert skills.type == 'skills'
