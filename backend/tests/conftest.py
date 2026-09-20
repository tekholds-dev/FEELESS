import os
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv


# Shared API fixtures for public preview endpoint tests
load_dotenv(Path('/app/frontend/.env'))


@pytest.fixture(scope="session")
def base_url() -> str:
    url = os.environ.get("REACT_APP_BACKEND_URL")
    if not url:
        pytest.skip("REACT_APP_BACKEND_URL is missing; cannot run public endpoint tests")
    return url.rstrip("/")


@pytest.fixture(scope="session")
def api_client() -> requests.Session:
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session
