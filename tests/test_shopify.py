import pytest
from unittest.mock import AsyncMock, patch

from shopify.shopify import Shopify, ShopifyProduct


@pytest.mark.asyncio
@pytest.mark.mock
async def test_shopify_init(shopify_credentials):
    """Test Shopify service initialization"""
    service = Shopify(shopify_credentials)
    assert service.api_key == shopify_credentials['api_key']
    assert service.api_secret == shopify_credentials['api_secret']
    assert service.access_token == shopify_credentials['access_token']
    assert service.shop_url == shopify_credentials['shop_url']
    assert service.api_version == shopify_credentials['api_version']


@pytest.mark.asyncio
@pytest.mark.mock
async def test_shopify_get_products_mock(shopify_credentials, load_mock_data):
    """Test getting Shopify products with mock data"""
    mock_data = load_mock_data('shopify', 'products')
    
    with patch('shopify.shopify.Shopify.validate_credentials', return_value=True), \
         patch('shopify.shopify.Shopify.get_products', return_value=mock_data['products']):
        
        service = Shopify(shopify_credentials)
        await service.initialize()
        
        products = await service.get_products()
        assert len(products) == 1
        assert products[0]['id'] == "123456789"
        assert products[0]['title'] == "Test Product"


@pytest.mark.asyncio
@pytest.mark.real
@pytest.mark.skipif(
    not pytest.mark.use_real_apis,
    reason="--use-real-apis not specified"
)
async def test_shopify_get_products_real(shopify_credentials):
    """Test getting Shopify products with real API"""
    service = Shopify(shopify_credentials)
    await service.initialize()
    
    products = await service.get_products()
    assert isinstance(products, list)
    
    if products:  # If there are any products
        product = products[0]
        assert isinstance(product, dict)
        assert 'id' in product
        assert 'title' in product
        assert 'variants' in product


@pytest.mark.asyncio
@pytest.mark.mock
async def test_shopify_get_order_mock(shopify_credentials, load_mock_data):
    """Test getting a single Shopify order with mock data"""
    mock_data = load_mock_data('shopify', 'order')
    
    with patch('shopify.shopify.Shopify.validate_credentials', return_value=True), \
         patch('shopify.shopify.Shopify.get_order', return_value=mock_data['order']):
        
        service = Shopify(shopify_credentials)
        await service.initialize()
        
        order = await service.get_order("gid://shopify/Order/123456789")
        assert order['id'] == "gid://shopify/Order/123456789"
        assert order['orderNumber'] == "1001"
        assert order['fulfillmentStatus'] == "UNFULFILLED"


@pytest.mark.asyncio
@pytest.mark.real
@pytest.mark.skipif(
    not pytest.mark.use_real_apis,
    reason="--use-real-apis not specified"
)
async def test_shopify_get_order_real(shopify_credentials):
    """Test getting a single Shopify order with real API"""
    service = Shopify(shopify_credentials)
    await service.initialize()
    
    # First get list of orders to get a real ID
    orders = await service.get_orders()
    if not orders:
        pytest.skip("No orders available for testing")
    
    order_id = orders[0]['id']
    order = await service.get_order(order_id)
    
    assert order['id'] == order_id
    assert 'orderNumber' in order
    assert 'fulfillmentStatus' in order


@pytest.mark.asyncio
@pytest.mark.mock
async def test_shopify_get_latest_order_mock(shopify_credentials, load_mock_data):
    """Test getting latest Shopify order with mock data"""
    mock_data = load_mock_data('shopify', 'order')
    
    with patch('shopify.shopify.Shopify.validate_credentials', return_value=True), \
         patch('shopify.shopify.Shopify.get_orders', return_value=[mock_data['order']]):
        
        service = Shopify(shopify_credentials)
        await service.initialize()
        
        orders = await service.get_orders(limit=1, sort_key="CREATED_AT", reverse=True)
        assert len(orders) == 1
        order = orders[0]
        assert order is not None
        assert 'id' in order
        assert 'createdAt' in order
        assert order['orderNumber'] == mock_data['order']['orderNumber']


@pytest.mark.asyncio
@pytest.mark.real
@pytest.mark.skipif(
    not pytest.mark.use_real_apis,
    reason="--use-real-apis not specified"
)
async def test_shopify_get_latest_order_real(shopify_credentials):
    """Test getting latest Shopify order with real API"""
    service = Shopify(shopify_credentials)
    await service.initialize()
    
    orders = await service.get_orders(limit=1, sort_key="CREATED_AT", reverse=True)
    if not orders:
        pytest.skip("No orders available for testing")
        
    order = orders[0]
    assert 'id' in order
    assert 'createdAt' in order
    assert 'orderNumber' in order