import os
import shutil
import pathlib as plb
import tempfile
import zipfile
from io import BytesIO

import httpx
from rich.console import Console

console = Console()

DEFAULT_CACHE_DIR = plb.Path.home() / '.persona' / '.cache'
PERSONA_CACHE = plb.Path(os.environ.get('PERSONA_CACHE', DEFAULT_CACHE_DIR)).resolve()


def parse_gh_url(url: str) -> tuple[str, str, str]:
    parts = url.replace('https://github.com/', '').split('/tree/')
    user, repo = parts[0].split('/')
    if len(parts) == 1:
        branch = 'main'
    else:
        branch = parts[1]
    return user, repo, branch


def get_repo_cache_dir(url: str) -> plb.Path:
    """Get the cache directory for a given URL."""
    user, repo, _ = parse_gh_url(url)
    return PERSONA_CACHE / user / repo


def download_and_cache_github_repo(url: str, path: str) -> plb.Path:
    """Download and extract a GitHub repository."""
    # Convert the tree URL to a zip URL
    user, repo, branch = parse_gh_url(url)
    zip_url = 'https://github.com/%s/%s/archive/refs/heads/%s.zip' % (user, repo, branch)

    cache_dir = get_repo_cache_dir(url)
    repo_dir = cache_dir / f'{repo}-{branch}'
    if repo_dir.exists():
        console.print(f'Using cached repository: {repo_dir}')
        return repo_dir

    console.print(f'Downloading repository from {zip_url}...')
    try:
        response = httpx.get(zip_url, follow_redirects=True)
        response.raise_for_status()

        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(BytesIO(response.content)) as z:
                z.extractall(temp_dir)

            extracted_dir = plb.Path(temp_dir) / f'{repo}-{branch}'

            # move the extracted directory to the cache
            cache_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(extracted_dir), str(cache_dir))
            return repo_dir

    except httpx.RequestError as e:
        console.print(f'[red]Error downloading file: {e}[/red]')
        raise
