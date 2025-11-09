import pathlib as plb
import zipfile
from io import BytesIO

import httpx
import pytest
from pytest_httpx import HTTPXMock

from persona.cache import (
    download_and_cache_github_repo,
    get_repo_cache_dir,
    parse_gh_url,
)


@pytest.mark.parametrize(
    ('url', 'expected'),
    [
        ('https://github.com/user/repo/tree/develop', ('user', 'repo', 'develop')),
        ('https://github.com/user/repo', ('user', 'repo', 'main')),
        (
            'https://github.com/another-user/another-repo/tree/feature-branch',
            ('another-user', 'another-repo', 'feature-branch'),
        ),
    ],
)
def test_parse_gh_url(url: str, expected: tuple[str, str, str]) -> None:
    """Test that parse_gh_url correctly parses GitHub URLs."""
    # Act
    result = parse_gh_url(url)

    # Assert
    assert result == expected


def test_get_repo_cache_dir(monkeypatch) -> None:
    """Test that get_repo_cache_dir constructs the correct cache path."""
    # Arrange
    mock_cache_dir = plb.Path('/tmp/persona-cache')
    monkeypatch.setattr('persona.cache.PERSONA_CACHE', mock_cache_dir)
    url = 'https://github.com/user/repo'

    # Act
    result = get_repo_cache_dir(url)

    # Assert
    assert result == mock_cache_dir / 'user' / 'repo'


def test_download_and_cache_github_repo_not_cached(
    httpx_mock: HTTPXMock, tmp_path: plb.Path, monkeypatch
) -> None:
    """Test downloading and caching a repo that is not already cached."""
    # Arrange
    monkeypatch.setattr('persona.cache.PERSONA_CACHE', tmp_path)
    url = 'https://github.com/user/repo/tree/main'
    user, repo, branch = parse_gh_url(url)
    zip_url = f'https://github.com/{user}/{repo}/archive/refs/heads/{branch}.zip'
    repo_dir = tmp_path / user / repo / f'{repo}-{branch}'

    # Create a dummy zip file in memory
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zf:
        zf.writestr(f'{repo}-{branch}/test.txt', 'test content')
    zip_content = zip_buffer.getvalue()

    httpx_mock.add_response(url=zip_url, content=zip_content)

    # Act
    result = download_and_cache_github_repo(url, str(tmp_path))

    # Assert
    assert result == repo_dir
    assert repo_dir.exists()
    assert (repo_dir / 'test.txt').read_text() == 'test content'


def test_download_and_cache_github_repo_already_cached(
    httpx_mock: HTTPXMock, tmp_path: plb.Path, monkeypatch
) -> None:
    """Test that an already cached repo is not re-downloaded."""
    # Arrange
    monkeypatch.setattr('persona.cache.PERSONA_CACHE', tmp_path)
    url = 'https://github.com/user/repo/tree/main'
    user, repo, branch = parse_gh_url(url)
    repo_dir = tmp_path / user / repo / f'{repo}-{branch}'
    repo_dir.mkdir(parents=True)
    (repo_dir / 'test.txt').write_text('cached content')

    # Act
    result = download_and_cache_github_repo(url, str(tmp_path))

    # Assert
    assert result == repo_dir
    assert len(httpx_mock.get_requests()) == 0


def test_download_and_cache_github_repo_http_error(
    httpx_mock: HTTPXMock, tmp_path: plb.Path, monkeypatch
) -> None:
    """Test that an HTTP error during download is handled correctly."""
    # Arrange
    monkeypatch.setattr('persona.cache.PERSONA_CACHE', tmp_path)
    url = 'https://github.com/user/repo/tree/main'
    user, repo, branch = parse_gh_url(url)
    zip_url = f'https://github.com/{user}/{repo}/archive/refs/heads/{branch}.zip'

    httpx_mock.add_exception(httpx.RequestError('Network error'), url=zip_url)

    # Act & Assert
    with pytest.raises(httpx.RequestError):
        download_and_cache_github_repo(url, str(tmp_path))
