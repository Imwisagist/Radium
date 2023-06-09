"""Test task for Radium.

The script in 3 streams downloads the contents of the remote git repository,
saves it to a temporary folder and counts the hash of each file.
"""
import sys
from asyncio import Semaphore, gather, run
from hashlib import sha256
from http import HTTPStatus
from multiprocessing import Pool
from pathlib import Path
from tempfile import TemporaryDirectory

from aiofiles import open as aiofile_open
from aiohttp import ClientResponse, ClientSession

file_paths: list = []
REPO_ENDPOINT: str = 'https://gitea.radium.group/radium/project-configuration'
API_ENDPOINT: str = (
    'https://gitea.radium.group/api/v1/repos/radium/' +
    'project-configuration/contents/'
)


async def get_response(session: ClientSession, url: str) -> ClientResponse:
    """Request data from the specified address using the GET method."""
    response: ClientResponse = await session.get(url)
    if response.status != HTTPStatus.OK:
        raise ConnectionError(
            'Unsuccessful response code: {0}'.format(response.status),
        )
    return response


async def download_file(
    file_data: dict, session: ClientSession, path: Path,
) -> None:
    """Download file for by the specified path."""
    async with Semaphore(3):
        file_url: str = '{0}/raw/branch/master/{1}'.format(
            REPO_ENDPOINT, file_data.get('path'),
        )
        raw_file: ClientResponse = await get_response(session, file_url)
        file_path: Path = path / file_data.get('name')
        async with aiofile_open(file_path, 'wb') as binary_file:
            await binary_file.write(await raw_file.content.read())
            file_paths.append(file_path)


def print_hash(file_path: Path) -> None:
    """Print calculated hash for one file."""
    if not file_path.exists():
        raise FileNotFoundError('File not Found')

    hsh = sha256()
    chunk_size: int = 4096
    with open(file_path, 'rb') as binary_read_file:
        while True:
            chunk: bytes = binary_read_file.read(chunk_size)
            if not chunk:
                break
            hsh.update(chunk)
        sys.stdout.write(
            '{0} hash: {1}\n'.format(file_path.name, hsh.hexdigest()),
        )


async def parse_catalog(
    catalog: list | dict, session: ClientSession, tasks: list, path: Path,
) -> None:
    """Parse directories for files, transfers files for download."""
    for file_or_dir in catalog:
        if not file_or_dir.get('type'):
            raise KeyError('Not valid response, key "type" not found')

        if file_or_dir.get('type') == 'file':
            tasks.append(download_file(file_or_dir, session, path))

        elif file_or_dir.get('type') == 'dir':
            path: Path = path / file_or_dir.get('path')
            Path.mkdir(path)
            new_response: ClientResponse = await get_response(
                session, API_ENDPOINT + path.name,
            )
            await parse_catalog(
                await new_response.json(), session, tasks, path,
            )


async def download_files(path: Path) -> None:
    """Create Session, response and send it to parsing."""
    async with ClientSession() as ssn:
        response: ClientResponse = await get_response(ssn, API_ENDPOINT)
        downloaded_paths: list = []
        await parse_catalog(await response.json(), ssn, downloaded_paths, path)
        await gather(*downloaded_paths)


async def main() -> None:
    """Create temp folder, download files and count hash."""
    with TemporaryDirectory() as temp_dir:
        sys.stdout.write('Downloading files...\n')
        await download_files(Path(temp_dir))
        sys.stdout.write('Calculation hash...\n')
        with Pool() as pool:   # I take all core == os.cpu_count()
            pool.map(print_hash, file_paths)


if __name__ == '__main__':
    run(main())   # pragma: no cover
