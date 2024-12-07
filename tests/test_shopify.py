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
async def test_shopify_update_inventory_mock(shopify_credentials):
    """Test updating Shopify inventory with mock data"""
    service = Shopify(shopify_credentials)
    service.client = AsyncMock()  # Mock the client
    
    # Mock the update_inventory method
    service.client.update_inventory = AsyncMock(return_value=True)
    
    result = await service.update_inventory("123456789", 50)
    assert result is True
    
    # Verify the mock was called with correct arguments
    service.client.update_inventory.assert_called_once_with("123456789", 50)


@pytest.mark.asyncio
@pytest.mark.real
@pytest.mark.skipif(
    not pytest.mark.use_real_apis,
    reason="--use-real-apis not specified"
)
async def test_shopify_update_inventory_real(shopify_credentials):
    """Test updating Shopify inventory with real API"""
    service = Shopify(shopify_credentials)
    await service.initialize()
    
    # Get first product to test with
    products = await service.get_products()
    if not products:
        pytest.skip("No products available for testing")
    
    product_id = products[0]['id']
    current_quantity = products[0]['variants'][0]['inventory_quantity']
    
    # Try to update inventory
    result = await service.update_inventory(product_id, current_quantity + 1)
    assert result is True
    
    # Verify the update
    updated_products = await service.get_products()
    updated_quantity = next(
        p['variants'][0]['inventory_quantity'] 
        for p in updated_products 
        if p['id'] == product_id
    )
    assert updated_quantity == current_quantity + 1 