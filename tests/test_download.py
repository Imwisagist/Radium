"""Тесты функций для скачивания файлов."""
from pathlib import Path

import pytest
from aiohttp import ClientSession

from main import (
    get_response,
    download_file,
    download_files,
    parse_catalog,
)


@pytest.mark.asyncio()
async def test_download_files_from_gitea_repository(
    tmp_path: callable,
    fake_session: callable,
):
    ClientSession.get = fake_session.get
    directory = tmp_path / Path('new_dir')
