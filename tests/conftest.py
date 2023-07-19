import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest
from dotenv import dotenv_values, load_dotenv

load_dotenv("./tests/test.env")

from wg_discord.settings import settings


@pytest.fixture(autouse=True)
def default_fixture():
    with mock.patch("wg_discord.__main__.start_wireguard"), mock.patch(
        "wg_discord.__main__.stop_wireguard"
    ), mock.patch("lightbulb.BotApp"):
        yield


@pytest.fixture(autouse=True)
def init_settings():
    """Reset Settings for each test"""
    for k in {**dotenv_values("./tests/test.env")}.keys():
        os.environ.pop(k, None)

    load_dotenv("./tests/test.env", override=True)

    # Provide new temp file and dir
    os.environ["WIREGUARD_CONFIG_DIR"] = tempfile.TemporaryDirectory().name
    os.environ["WIREGUARD_CONFIG_FILENAME"] = Path(
        tempfile.NamedTemporaryFile(suffix=".conf").name
    ).name

    Path(os.environ["WIREGUARD_CONFIG_DIR"]).mkdir(parents=True, exist_ok=True)

    # Re-read and validate environment variables
    settings.__init__()

    yield

    Path(settings.wireguard_config_filepath).unlink()
    Path(settings.wireguard_config_dir).rmdir()
