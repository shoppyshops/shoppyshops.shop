from typing import Dict, Any, List, Optional
from shoppyshop.shoppyshop import (
    ServiceBase,
    ServiceClientError,
    ServiceValidationError,
    ProductBase,
    OrderBase
)
import httpx


class ShopifyProduct(ProductBase):
    """Shopify-specific product type"""
    vendor: str
    handle: str
    variants: List[Dict[str, Any]]
    images: List[Dict[str, Any]]


class ShopifyOrder(OrderBase):
    """Shopify-specific order type"""
    customer: Dict[str, Any]
    shipping_address: Dict[str, Any]
    fulfillment_status: str


class Shopify(ServiceBase):
    """Shopify store management interface"""
    
    @property
    def required_credentials(self) -> List[str]:
        return ['api_key', 'api_secret', 'access_token', 'shop_url', 'api_version']
    
    def __init__(self, credentials: Dict[str, Any]):
        """Initialize with provided credentials"""
        self.validate_credential_keys(credentials)
        self.api_key = credentials['api_key']
        self.api_secret = credentials['api_secret']
        self.access_token = credentials['access_token']
        self.shop_url = credentials['shop_url']
        self.api_version = credentials['api_version']
        self.client = None
        self.graphql_url = f"https://{self.shop_url}/admin/api/{self.api_version}/graphql.json"
    
    async def initialize(self) -> None:
        """Initialize Shopify API client"""
        self.client = httpx.AsyncClient(
            headers={
                "X-Shopify-Access-Token": self.access_token,
                "Content-Type": "application/json",
            }
        )
        if not await self.validate_credentials():
            raise ServiceValidationError("Invalid Shopify credentials")
    
    async def validate_credentials(self) -> bool:
        """Validate Shopify credentials with a simple shop query"""
        if not self.client:
            print("No client initialized")
            return False
        
        query = """
        query {
          shop {
            name
            id
          }
        }
        """
        
        try:
            response = await self.client.post(
                self.graphql_url,
                json={'query': query}
            )
            response.raise_for_status()
            data = response.json()
            
            if 'errors' in data:
                print(f"GraphQL errors: {data['errors']}")
                return False
            
            valid = 'data' in data and 'shop' in data['data']
            if not valid:
                print(f"Invalid response structure: {data}")
            return valid
            
        except Exception as e:
            print(f"Validation error: {str(e)}")
            return False
    
    async def get_products(self) -> List[ShopifyProduct]:
        """Retrieve product catalog using GraphQL"""
        if not self.client:
            raise ServiceClientError("Shopify client not initialized")
        
        query = """
        query getProducts {
          products(first: 50) {
            edges {
              node {
                id
                title
                description
                vendor
                handle
                variants(first: 10) {
                  edges {
                    node {
                      id
                      sku
                      price
                      inventoryQuantity
                    }
                  }
                }
                images(first: 1) {
                  edges {
                    node {
                      url
                      altText
                    }
                  }
                }
              }
            }
          }
        }
        """
        
        try:
            response = await self.client.post(
                self.graphql_url,
                json={'query': query}
            )
            response.raise_for_status()
            data = response.json()
            
            if 'errors' in data:
                raise ServiceClientError(f"GraphQL Error: {data['errors']}")
            
            # Transform the GraphQL response into our product type
            products = []
            for edge in data['data']['products']['edges']:
                node = edge['node']
                products.append({
                    'id': node['id'],
                    'title': node['title'],
                    'description': node['description'],
                    'vendor': node['vendor'],
                    'handle': node['handle'],
                    'variants': [v['node'] for v in node['variants']['edges']],
                    'images': [i['node'] for i in node['images']['edges']]
                })
            
            return products
            
        except httpx.HTTPError as e:
            raise ServiceClientError(f"Failed to fetch products: {str(e)}")
    
    async def update_inventory(self, product_id: str, quantity: int) -> bool:
        """Update product inventory"""
        if not self.client:
            raise ServiceClientError("Shopify client not initialized")
        # TODO: Implement inventory update
        return True
    
    async def get_orders(self, status: Optional[str] = None) -> List[ShopifyOrder]:
        """Get orders with optional status filter"""
        if not self.client:
            raise ServiceClientError("Shopify client not initialized")
        # TODO: Implement order retrieval
        return []
    
    async def get_order(self, order_id: str) -> Dict[str, Any]:
        """
        Get a single order by ID using GraphQL
        
        Args:
            order_id: The Shopify GID of the order (format: gid://shopify/Order/123456789)
        
        Returns:
            Dict containing order details
        """
        if not self.client:
            raise ServiceClientError("Shopify client not initialized")
        
        query = """
        query getOrder($id: ID!) {
          order(id: $id) {
            id
            name
            orderNumber
            email
            phone
            fulfillmentStatus
            financialStatus
            totalPriceSet {
              shopMoney {
                amount
                currencyCode
              }
            }
            subtotalPriceSet {
              shopMoney {
                amount
                currencyCode
              }
            }
            totalShippingPriceSet {
              shopMoney {
                amount
                currencyCode
              }
            }
            totalTaxSet {
              shopMoney {
                amount
                currencyCode
              }
            }
            lineItems(first: 50) {
              edges {
                node {
                  id
                  name
                  quantity
                  originalUnitPrice
                  discountedUnitPrice
                  variant {
                    id
                    sku
                    inventoryQuantity
                  }
                }
              }
            }
            shippingAddress {
              firstName
              lastName
              address1
              address2
              city
              province
              country
              zip
              phone
            }
          }
        }
        """
        
        try:
            response = await self.client.post(
                self.graphql_url,
                json={
                    'query': query,
                    'variables': {'id': order_id}
                }
            )
            response.raise_for_status()
            data = response.json()
            
            if 'errors' in data:
                raise ServiceClientError(f"GraphQL Error: {data['errors']}")
            
            return data['data']['order']
            
        except httpx.HTTPError as e:
            raise ServiceClientError(f"Failed to fetch order: {str(e)}")
