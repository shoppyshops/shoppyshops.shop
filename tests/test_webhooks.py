import json
import pytest
from django.urls import reverse
from unittest.mock import AsyncMock, patch
from shoppyshop.views import ShoppyShop, ServiceEvent

# Sample webhook data
@pytest.fixture
def shopify_order_webhook_data(load_mock_data):
    """Load mock webhook data from JSON file"""
    return load_mock_data('shopify/webhooks', 'order_created')

@pytest.fixture
def mock_shopify_headers():
    """Mock Shopify webhook headers with proper Django HTTP_ prefix"""
    return {
        'X_SHOPIFY_TOPIC': 'orders/create',
        'X_SHOPIFY_HMAC_SHA256': 'mock-hmac',
        'X_SHOPIFY_SHOP_DOMAIN': 'test-shop.myshopify.com',
        'X_SHOPIFY_TEST': 'true',
        'X_SHOPIFY_API_VERSION': '2024-01',
        'CONTENT_TYPE': 'application/json',
    }

@pytest.mark.asyncio
@pytest.mark.django_db
@pytest.mark.mock
async def test_shopify_webhook_order_created(client, shopify_order_webhook_data, mock_shopify_headers):
    """Test successful order webhook processing"""
    
    mock_shop = AsyncMock()
    mock_shop.shopify = AsyncMock()
    mock_shop.emit = AsyncMock()
    
    # Convert data to JSON string
    json_data = json.dumps(shopify_order_webhook_data)
    
    with patch('shoppyshop.views.ShoppyShop.get_instance', return_value=mock_shop):
        # Send webhook request with explicit content type
        response = await client.post(
            reverse('shoppyshop:shopify_webhook'),
            data=json_data,
            content_type='application/json',
            **mock_shopify_headers
        )
        
        # Assert response
        assert response.status_code == 200
        
        # Verify service initialization was called
        mock_shop.initialize_services.assert_called_once()
        
        # Verify event emission
        mock_shop.emit.assert_called_once_with(
            ServiceEvent.ORDER_CREATED,
            {
                'order_id': f"gid://shopify/Order/{shopify_order_webhook_data['id']}",
                'source': 'shopify',
                'raw_data': shopify_order_webhook_data
            }
        )

@pytest.mark.asyncio
@pytest.mark.django_db
@pytest.mark.mock
async def test_shopify_webhook_invalid_topic(client, shopify_order_webhook_data):
    """Test webhook with invalid topic"""
    headers = {
        'HTTP_X_SHOPIFY_TOPIC': 'products/create',  # Different topic
        'HTTP_X_SHOPIFY_HMAC_SHA256': 'mock-hmac',
        'HTTP_X_SHOPIFY_SHOP_DOMAIN': 'test-shop.myshopify.com',
        'HTTP_X_SHOPIFY_TEST': 'true',
        'HTTP_X_SHOPIFY_API_VERSION': '2024-01',
    }
    
    # Convert data to JSON string
    json_data = json.dumps(shopify_order_webhook_data)
    
    mock_shop = AsyncMock()
    with patch('shoppyshop.views.ShoppyShop.get_instance', return_value=mock_shop):
        response = await client.post(
            reverse('shoppyshop:shopify_webhook'),
            data=json_data,
            content_type='application/json',
            **headers
        )
        
        assert response.status_code == 200
        mock_shop.emit.assert_not_called()

@pytest.mark.asyncio
@pytest.mark.django_db
@pytest.mark.mock
async def test_shopify_webhook_service_unavailable(client, shopify_order_webhook_data, mock_shopify_headers):
    """Test webhook when Shopify service is unavailable"""
    
    mock_shop = AsyncMock()
    mock_shop.initialize_services.side_effect = Exception("Service initialization failed")
    
    # Convert data to JSON string
    json_data = json.dumps(shopify_order_webhook_data)
    
    with patch('shoppyshop.views.ShoppyShop.get_instance', return_value=mock_shop):
        response = await client.post(
            reverse('shoppyshop:shopify_webhook'),
            data=json_data,
            content_type='application/json',
            **mock_shopify_headers
        )
        
        assert response.status_code == 503

@pytest.mark.asyncio
@pytest.mark.django_db
@pytest.mark.mock
async def test_shopify_webhook_missing_headers(client, shopify_order_webhook_data):
    """Test webhook with missing required headers"""
    headers = {
        # Missing required headers
        'HTTP_X_SHOPIFY_SHOP_DOMAIN': 'test-shop.myshopify.com',
    }
    
    # Convert data to JSON string
    json_data = json.dumps(shopify_order_webhook_data)
    
    mock_shop = AsyncMock()
    with patch('shoppyshop.views.ShoppyShop.get_instance', return_value=mock_shop):
        response = await client.post(
            reverse('shoppyshop:shopify_webhook'),
            data=json_data,
            content_type='application/json',
            **headers
        )
        
        assert response.status_code == 401
        mock_shop.emit.assert_not_called()