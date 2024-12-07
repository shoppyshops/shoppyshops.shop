from typing import Dict, Any, List, Optional
from shoppyshop.shoppyshop import (
    ServiceBase,
    ServiceClientError,
    ServiceValidationError,
    ProductBase,
    OrderBase
)
import httpx
from urllib.parse import urlparse


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
        
        # Handle both full URLs and domain-only URLs
        shop_url = credentials['shop_url']
        if 'http' in shop_url:
            # Extract domain from full URL
            parsed = urlparse(shop_url)
            self.shop_url = parsed.netloc
        else:
            self.shop_url = shop_url
            
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
    
    async def get_orders(
        self, 
        status: Optional[str] = None, 
        limit: int = 10,
        sort_key: str = "CREATED_AT",
        reverse: bool = False
    ) -> List[ShopifyOrder]:
        """
        Get orders with flexible filtering and sorting
        
        Args:
            status: Optional status filter
            limit: Number of orders to fetch (default: 10)
            sort_key: Field to sort by (default: CREATED_AT)
            reverse: Sort in reverse order (default: False)
        
        Returns:
            List of orders matching criteria
        """
        if not self.client:
            raise ServiceClientError("Shopify client not initialized")
        
        query = """
        query getOrders($first: Int!, $query: String, $sortKey: OrderSortKeys!, $reverse: Boolean!) {
          orders(first: $first, query: $query, sortKey: $sortKey, reverse: $reverse) {
            edges {
              node {
                id
                name
                email
                phone
                displayFulfillmentStatus
                displayFinancialStatus
                createdAt
                totalPriceSet {
                  shopMoney {
                    amount
                    currencyCode
                  }
                }
                lineItems(first: 10) {
                  edges {
                    node {
                      id
                      name
                      quantity
                    }
                  }
                }
              }
            }
          }
        }
        """
        
        variables = {
            'first': limit,
            'query': f"status:{status}" if status else None,
            'sortKey': sort_key,
            'reverse': reverse
        }
        
        try:
            response = await self.client.post(
                self.graphql_url,
                json={
                    'query': query,
                    'variables': variables
                }
            )
            response.raise_for_status()
            data = response.json()
            
            if 'errors' in data:
                print(f"GraphQL errors in get_orders: {data['errors']}")
                raise ServiceClientError(f"GraphQL Error: {data['errors']}")
            
            # Transform the GraphQL response into our order type
            orders = []
            for edge in data['data']['orders']['edges']:
                node = edge['node']
                orders.append({
                    'id': node['id'],
                    'orderNumber': node['name'].replace('#', ''),
                    'email': node['email'],
                    'phone': node['phone'],
                    'fulfillmentStatus': node['displayFulfillmentStatus'],
                    'financialStatus': node['displayFinancialStatus'],
                    'createdAt': node['createdAt'],
                    'totalPrice': node['totalPriceSet']['shopMoney']['amount'],
                    'currencyCode': node['totalPriceSet']['shopMoney']['currencyCode'],
                    'lineItems': [item['node'] for item in node['lineItems']['edges']]
                })
            
            return orders
            
        except httpx.HTTPError as e:
            print(f"HTTP error in get_orders: {str(e)}")
            raise ServiceClientError(f"Failed to fetch orders: {str(e)}")
    
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
            email
            phone
            displayFulfillmentStatus
            displayFinancialStatus
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
                print(f"GraphQL errors in get_order: {data['errors']}")
                raise ServiceClientError(f"GraphQL Error: {data['errors']}")
            
            order_data = data['data']['order']
            
            # Transform the response to match our expected format
            return {
                'id': order_data['id'],
                'orderNumber': order_data['name'].replace('#', ''),
                'email': order_data['email'],
                'phone': order_data['phone'],
                'fulfillmentStatus': order_data['displayFulfillmentStatus'],
                'financialStatus': order_data['displayFinancialStatus'],
                'totalPrice': {
                    'amount': order_data['totalPriceSet']['shopMoney']['amount'],
                    'currency': order_data['totalPriceSet']['shopMoney']['currencyCode']
                },
                'subtotalPrice': {
                    'amount': order_data['subtotalPriceSet']['shopMoney']['amount'],
                    'currency': order_data['subtotalPriceSet']['shopMoney']['currencyCode']
                },
                'shippingPrice': {
                    'amount': order_data['totalShippingPriceSet']['shopMoney']['amount'],
                    'currency': order_data['totalShippingPriceSet']['shopMoney']['currencyCode']
                },
                'totalTax': {
                    'amount': order_data['totalTaxSet']['shopMoney']['amount'],
                    'currency': order_data['totalTaxSet']['shopMoney']['currencyCode']
                },
                'lineItems': [
                    {
                        'id': item['node']['id'],
                        'name': item['node']['name'],
                        'quantity': item['node']['quantity'],
                        'originalPrice': item['node']['originalUnitPrice'],
                        'discountedPrice': item['node']['discountedUnitPrice'],
                        'variant': item['node']['variant']
                    }
                    for item in order_data['lineItems']['edges']
                ],
                'shippingAddress': order_data['shippingAddress']
            }
            
        except httpx.HTTPError as e:
            print(f"HTTP error in get_order: {str(e)}")
            raise ServiceClientError(f"Failed to fetch order: {str(e)}")
