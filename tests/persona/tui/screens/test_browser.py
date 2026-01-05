import pytest
from unittest.mock import MagicMock, patch, mock_open
from textual.widgets import DataTable, Button, TabbedContent
from persona.tui.screens.browser import BrowserScreen
from persona.tui.screens.path_input import PathInputScreen
from persona.tui.app import PersonaApp


@pytest.mark.asyncio
async def test_browser_initial_load(mock_app: PersonaApp, mock_api: MagicMock) -> None:
    """Test that the browser loads data on mount."""
    async with mock_app.run_test() as pilot:
        await pilot.pause()
        roles_browser = mock_app.query_one('#roles BrowserScreen', BrowserScreen)
        assert roles_browser is not None
        mock_api.list_templates.assert_called()
        table = roles_browser.query_one(DataTable)
        assert table.row_count > 0
        assert table.get_row_at(0)[0] == 'Test Role'


@pytest.mark.asyncio
async def test_browser_search(mock_app: PersonaApp, mock_api: MagicMock) -> None:
    """Test that searching updates the table."""
    async with mock_app.run_test() as pilot:
        await pilot.pause()
        await pilot.click('#search_roles')
        await pilot.press(*list('test'))
        await pilot.pause()
        mock_api.search_templates.assert_called()
        table = mock_app.query_one('#roles DataTable', DataTable)
        assert table.row_count > 0


@pytest.mark.asyncio
async def test_browser_select_row(mock_app: PersonaApp, mock_api: MagicMock) -> None:
    """Test that selecting a row loads the definition."""
    async with mock_app.run_test() as pilot:
        await pilot.pause()
        roles_browser = mock_app.query_one('#roles BrowserScreen', BrowserScreen)
        table = roles_browser.query_one(DataTable)

        # Focus table and select row
        table.focus()
        table.move_cursor(row=0)
        await pilot.press('enter')
        await pilot.pause()

        mock_api.get_definition.assert_called()
        btn = roles_browser.query_one('#action_roles', Button)
        assert not btn.disabled


@pytest.mark.asyncio
async def test_browser_save_role_flow(mock_app: PersonaApp, mock_api: MagicMock) -> None:
    """Test the flow of saving a role."""
    # Patch open and pathlib in browser module
    with (
        patch('builtins.open', mock_open()) as m_open,
        patch('persona.tui.screens.browser.plb.Path') as m_path,
    ):
        # Setup mock path behavior
        m_path_obj = MagicMock()
        m_path.return_value = m_path_obj
        m_path.cwd.return_value = m_path_obj
        m_path_obj.__truediv__.return_value = m_path_obj  # mocking / operator
        m_path_obj.is_absolute.return_value = False

        async with mock_app.run_test() as pilot:
            await pilot.pause()

            roles_browser = mock_app.query_one('#roles BrowserScreen', BrowserScreen)
            table = roles_browser.query_one(DataTable)

            # Select row
            table.focus()
            table.move_cursor(row=0)
            await pilot.press('enter')
            await pilot.pause()

            # Click Save
            await pilot.click('#action_roles')
            await pilot.pause(0.5)  # Wait for screen transition

            # Type path and confirm
            # Ensure we are on the new screen.
            # We can't query by ID globally if it's ambiguous, but #path_input is unique.
            # If NoMatches, maybe screen isn't pushed yet.

            await pilot.click('#path_input')
            await pilot.press(*list('test_role.md'))
            await pilot.click('#confirm')
            await pilot.pause()

            # Verify file write
            m_open.assert_called()
            handle = m_open()
            handle.write.assert_called()


@pytest.mark.asyncio
async def test_browser_install_skill_flow(mock_app: PersonaApp, mock_api: MagicMock) -> None:
    """Test the flow of installing a skill."""
    # Switch to skills tab
    async with mock_app.run_test() as pilot:
        await pilot.pause()

        # Switch tab programmatically to be robust
        mock_app.query_one(TabbedContent).active = 'skills'

        # Wait for tab switch and load
        await pilot.pause()

        skills_browser = mock_app.query_one('#skills BrowserScreen', BrowserScreen)
        table = skills_browser.query_one(DataTable)

        table.focus()
        table.move_cursor(row=0)
        await pilot.press('enter')
        await pilot.pause()

        # Click Install
        await pilot.click('#action_skills')
        await pilot.pause(0.5)

        with patch('persona.tui.screens.browser.plb.Path') as m_path:
            m_path_obj = MagicMock()
            m_path.return_value = m_path_obj
            m_path.cwd.return_value = m_path_obj
            m_path_obj.__truediv__.return_value = m_path_obj
            m_path_obj.exists.return_value = False

            # Type path and confirm
            await pilot.click('#path_input')
            await pilot.press(*list('skills/test_skill'))
            await pilot.click('#confirm')
            await pilot.pause()

            # Verify API install called
            mock_api.install_skill.assert_called()


@pytest.mark.asyncio
async def test_role_default_save_path(mock_app: PersonaApp, mock_api: MagicMock) -> None:
    """Test that the default save path for roles follows the correct format."""
    async with mock_app.run_test() as pilot:
        await pilot.pause()
        roles_browser = mock_app.query_one('#roles BrowserScreen', BrowserScreen)
        table = roles_browser.query_one(DataTable)

        # Mock push_screen to capture the screen instance
        original_push_screen = mock_app.push_screen
        mock_push_screen = MagicMock(side_effect=original_push_screen)
        mock_app.push_screen = mock_push_screen

        # Select a role
        table.focus()
        table.move_cursor(row=0)
        await pilot.press('enter')
        await pilot.pause()

        # Click Save
        await pilot.click('#action_roles')
        await pilot.pause(0.5)

        # Check what screen was pushed
        assert mock_push_screen.called
        args, _ = mock_push_screen.call_args
        pushed_screen = args[0]

        assert isinstance(pushed_screen, PathInputScreen)

        # The selected role name is 'Test Role' (from conftest fixtures usually, assuming 'Test Role')
        # Check conftest.py to be sure what the mock returns.
        # But generally we expect .persona/roles/<safe_name>/ROLE.md

        expected_suffix = '.persona/roles/Test Role/ROLE.md'
        # We need to check if the path ends with this
        assert pushed_screen.initial_value.endswith(expected_suffix)
