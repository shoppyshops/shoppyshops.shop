from abc import ABC, abstractmethod
from django.conf import settings
from typing import Dict, Any, List, TypedDict, Optional


class ServiceCredentialsError(Exception):
    """Exception raised for credential-related errors"""
    pass


class ServiceInitializationError(Exception):
    """Raised when service initialization fails"""
    pass


class ServiceValidationError(Exception):
    """Raised when service validation fails"""
    pass


class ServiceClientError(Exception):
    """Raised when service client operations fail"""
    pass


# Common type definitions
class ProductBase(TypedDict):
    """Base product type shared across services"""
    id: str
    title: str
    description: str
    price: float
    quantity: int


class OrderBase(TypedDict):
    """Base order type shared across services"""
    id: str
    status: str
    total: float
    items: List[Dict[str, Any]]
    created_at: str


class ServiceBase(ABC):
    """Abstract base class for all service integrations"""
    
    @property
    @abstractmethod
    def required_credentials(self) -> List[str]:
        """List of required credential keys"""
        pass
    
    def validate_credential_keys(self, credentials: Dict[str, Any]) -> None:
        """Validate that all required credentials are present"""
        missing_keys = [key for key in self.required_credentials if key not in credentials]
        if missing_keys:
            raise ServiceCredentialsError(f"Missing required credentials: {', '.join(missing_keys)}")
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize service connection"""
        pass
    
    @abstractmethod
    async def validate_credentials(self) -> bool:
        """Validate service credentials with API"""
        pass
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if hasattr(self, 'client') and self.client:
            await self.client.close()


class ShoppyShop:
    """Main controller class managing service integrations"""
    
    def __init__(self):
        """Initialize services with credentials from environment"""
        from shopify.shopify import Shopify
        from ebay.ebay import Ebay
        from meta.meta import Meta
        
        try:
            # Shopify credentials
            shopify_creds = {
                'api_key': settings.SHOPIFY_API_KEY,
                'api_secret': settings.SHOPIFY_API_SECRET,
                'access_token': settings.SHOPIFY_ACCESS_TOKEN,
                'shop_url': settings.SHOPIFY_URL,
                'api_version': settings.SHOPIFY_API_VERSION
            }
            
            # eBay credentials
            ebay_creds = {
                'app_id': settings.EBAY_APP_ID,
                'cert_id': settings.EBAY_CERT_ID,
                'dev_id': settings.EBAY_DEV_ID,
                'user_token': settings.EBAY_USER_TOKEN,
                'environment': settings.EBAY_ENV
            }
            
            # Meta credentials
            meta_creds = {
                'app_id': settings.META_APP_ID,
                'app_secret': settings.META_APP_SECRET,
                'access_token': settings.META_ACCESS_TOKEN,
                'environment': settings.META_ENV
            }
            
            self.shopify = Shopify(shopify_creds)
            self.ebay = Ebay(ebay_creds)
            self.meta = Meta(meta_creds)
            
        except AttributeError as e:
            raise ServiceCredentialsError(f"Missing environment variable: {str(e)}")
    
    async def initialize_services(self) -> None:
        """Initialize all service connections"""
        try:
            await self.shopify.initialize()
            await self.ebay.initialize()
            await self.meta.initialize()
        except Exception as e:
            raise ServiceInitializationError(f"Failed to initialize services: {str(e)}")
    
    async def sync_inventory(self) -> None:
        """Cross-platform inventory synchronization"""
        if not all([self.shopify.client, self.ebay.client]):
            raise ServiceClientError("Services not initialized")
        # TODO: Implement inventory sync
        pass
    
    async def process_orders(self) -> None:
        """Order processing and fulfillment"""
        if not all([self.shopify.client, self.ebay.client]):
            raise ServiceClientError("Services not initialized")
        # TODO: Implement order processing
        pass
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize_services()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        # Close all service clients
        for service in [self.shopify, self.ebay, self.meta]:
            if hasattr(service, 'client') and service.client:
                await service.client.close()
