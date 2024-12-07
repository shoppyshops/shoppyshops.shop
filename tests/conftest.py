import json
import os
from pathlib import Path
from typing import Dict, Any

import pytest
from _pytest.config import Config
from _pytest.config.argparsing import Parser
from django.test import AsyncClient


def pytest_addoption(parser: Parser) -> None:
    """Add custom command line options"""
    parser.addoption(
        "--use-real-apis",
        action="store_true",
        default=False,
        help="Run tests against real APIs instead of mocks"
    )


def pytest_configure(config: Config) -> None:
    """Configure custom markers"""
    config.addinivalue_line("markers", "mock: mark test to run with mock data")
    config.addinivalue_line("markers", "real: mark test to run with real APIs")


@pytest.fixture
def use_real_apis(request) -> bool:
    """Check if we should use real APIs"""
    return request.config.getoption("--use-real-apis")


@pytest.fixture
def mock_data_dir() -> Path:
    """Get the mock data directory"""
    return Path(__file__).parent / "mocks"


@pytest.fixture
def load_mock_data():
    """Fixture to load mock data from JSON files"""
    def _load_mock_data(service: str, filename: str) -> Dict[str, Any]:
        mock_file = Path(__file__).parent / "mocks" / service / f"{filename}.json"
        with mock_file.open() as f:
            return json.load(f)
    return _load_mock_data


@pytest.fixture
def shopify_credentials() -> Dict[str, str]:
    """Get Shopify credentials from environment"""
    shop_url = os.getenv('SHOPIFY_URL', '')
    if not shop_url.endswith('myshopify.com'):
        shop_url = f"{shop_url}.myshopify.com"
        
    return {
        'api_key': os.getenv('SHOPIFY_API_KEY', ''),
        'api_secret': os.getenv('SHOPIFY_API_SECRET', ''),
        'access_token': os.getenv('SHOPIFY_API_ACCESS_TOKEN', ''),
        'shop_url': shop_url,
        'api_version': os.getenv('SHOPIFY_API_VERSION', '2024-01')
    }


@pytest.fixture
def ebay_credentials() -> Dict[str, str]:
    """Get eBay credentials from environment"""
    return {
        'app_id': os.getenv('EBAY_APP_ID', ''),
        'cert_id': os.getenv('EBAY_CERT_ID', ''),
        'dev_id': os.getenv('EBAY_DEV_ID', ''),
        'user_token': os.getenv('EBAY_USER_TOKEN', ''),
        'environment': os.getenv('EBAY_ENV', 'sandbox')
    }


@pytest.fixture
def meta_credentials() -> Dict[str, str]:
    """Get Meta credentials from environment"""
    return {
        'app_id': os.getenv('META_APP_ID', ''),
        'app_secret': os.getenv('META_APP_SECRET', ''),
        'access_token': os.getenv('META_ACCESS_TOKEN', ''),
        'environment': os.getenv('META_ENV', 'sandbox')
    }


@pytest.fixture
async def client():
    """Async client fixture for testing async views"""
    return AsyncClient() 