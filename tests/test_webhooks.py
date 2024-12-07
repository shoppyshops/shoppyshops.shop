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
    return {
        'HTTP_X_SHOPIFY_TOPIC': 'orders/create',
        'HTTP_X_SHOPIFY_HMAC_SHA256': 'mock-hmac',
        'HTTP_X_SHOPIFY_SHOP_DOMAIN': 'test-shop.myshopify.com',
    }

@pytest.mark.asyncio
@pytest.mark.django_db
@pytest.mark.mock
async def test_shopify_webhook_order_created(client, shopify_order_webhook_data, mock_shopify_headers):
    """Test successful order webhook processing"""
    
    # Mock ShoppyShop instance and its methods
    mock_shop = AsyncMock()
    mock_shop.shopify = AsyncMock()
    mock_shop.emit = AsyncMock()
    
    with patch('shoppyshop.views.ShoppyShop.get_instance', return_value=mock_shop):
        # Send webhook request
        response = await client.post(
            reverse('shoppyshop:shopify_webhook'),
            data=json.dumps(shopify_order_webhook_data),
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
    }
    
    mock_shop = AsyncMock()
    with patch('shoppyshop.views.ShoppyShop.get_instance', return_value=mock_shop):
        response = await client.post(
            reverse('shoppyshop:shopify_webhook'),
            data=json.dumps(shopify_order_webhook_data),
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
    
    with patch('shoppyshop.views.ShoppyShop.get_instance', return_value=mock_shop):
        response = await client.post(
            reverse('shoppyshop:shopify_webhook'),
            data=json.dumps(shopify_order_webhook_data),
            content_type='application/json',
            **mock_shopify_headers
        )
        
        assert response.status_code == 503 