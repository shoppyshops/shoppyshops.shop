from abc import ABC, abstractmethod
from django.conf import settings
from typing import Dict, Any, List, TypedDict, Optional, Callable, Awaitable
from enum import Enum
import asyncio
from datetime import datetime, timedelta
import logging
from collections import defaultdict


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


class ServiceEvent(Enum):
    """Events that can be emitted by services"""
    ORDER_CREATED = "order_created"
    ORDER_UPDATED = "order_updated"
    ERROR = "error"


class Task:
    """Represents a scheduled task"""
    def __init__(
        self,
        func: Callable[..., Awaitable[Any]],
        interval: timedelta,
        name: str,
        args: tuple = (),
        kwargs: dict = None
    ):
        self.func = func
        self.interval = interval
        self.name = name
        self.args = args
        self.kwargs = kwargs or {}
        self.last_run: Optional[datetime] = None
        self.is_running = False


class ShoppyShop:
    """Main controller class managing service integrations"""
    
    _instance = None
    _initialized = False
    _lock = asyncio.Lock()
    _default_handlers_registered = False
    
    def __init__(self):
        """Initialize basic attributes but defer service initialization"""
        # Skip if this instance is already initialized
        if ShoppyShop._initialized and self == ShoppyShop._instance:
            return
            
        # Initialize logging
        self.logger = logging.getLogger(__name__)
        
        # Event handlers dictionary: event -> list of handler functions
        self.event_handlers: Dict[ServiceEvent, List[Callable]] = defaultdict(list)
        
        # Task scheduling
        self.tasks: List[Task] = []
        self.task_loop: Optional[asyncio.Task] = None
    
    @classmethod
    async def get_instance(cls) -> 'ShoppyShop':
        """Get or create a singleton instance with async initialization"""
        async with cls._lock:
            if not cls._instance:
                cls._instance = cls()
                await cls._instance._initialize_full()
            return cls._instance

    async def initialize_services(self) -> None:
        """Public method for initializing services (for backward compatibility)"""
        if not ShoppyShop._initialized:
            await self._initialize_full()

    async def _initialize_full(self) -> None:
        """Complete initialization of the instance"""
        if ShoppyShop._initialized:
            return
            
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
            
            # Initialize services
            await self.shopify.initialize()
            await self.ebay.initialize()
            await self.meta.initialize()
            
            # Register default event handlers only once
            await self._register_default_handlers()
            
            # Start the task scheduler
            self.task_loop = asyncio.create_task(self._task_scheduler())
            
            ShoppyShop._initialized = True
            self.logger.info("ShoppyShop fully initialized")
            
        except AttributeError as e:
            raise ServiceCredentialsError(f"Missing environment variable: {str(e)}")
        except Exception as e:
            ShoppyShop._initialized = False
            raise ServiceInitializationError(f"Failed to initialize services: {str(e)}")

    async def _register_default_handlers(self) -> None:
        """Register default event handlers"""
        if not ShoppyShop._default_handlers_registered:
            self.on(ServiceEvent.ORDER_CREATED, self._handle_order_created)
            ShoppyShop._default_handlers_registered = True

    def on(self, event: ServiceEvent, handler: Callable) -> None:
        """Register an event handler if not already registered"""
        if handler not in self.event_handlers[event]:
            self.event_handlers[event].append(handler)
            if self.logger.isEnabledFor(logging.DEBUG):
                handler_name = getattr(handler, '__name__', str(handler))
                handler_type = 'async' if asyncio.iscoroutinefunction(handler) else 'sync'
                self.logger.debug(
                    f"Registered {handler_type} handler '{handler_name}' "
                    f"for event: {event.value}"
                )

    async def emit(self, event: ServiceEvent, data: Any = None) -> None:
        """Emit an event to all registered handlers"""
        handlers = self.event_handlers[event]
        start_time = datetime.now()
        success_count = 0
        error_count = 0
        
        if self.logger.isEnabledFor(logging.DEBUG):
            handler_names = [getattr(h, '__name__', str(h)) for h in handlers]
            self.logger.debug(
                f"Emitting {event.value} to {len(handlers)} handlers: "
                f"{', '.join(handler_names)}"
            )
        
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
                success_count += 1
            except Exception as e:
                error_count += 1
                handler_name = getattr(handler, '__name__', str(handler))
                self.logger.error(
                    f"Error in handler '{handler_name}' for {event.value}: {str(e)}"
                )
                await self.emit(ServiceEvent.ERROR, {
                    "event": event,
                    "error": str(e),
                    "handler": handler_name
                })
        
        # Log summary if there were any handlers
        if handlers:
            process_time = (datetime.now() - start_time).total_seconds()
            self.logger.debug(
                f"Event {event.value} processed by {success_count}/{len(handlers)} handlers "
                f"in {process_time:.3f}s ({error_count} errors)"
            )

    async def _handle_order_created(self, data: Dict[str, Any]) -> None:
        """
        Handle order creation events from any service
        """
        try:
            source = data.get('source')
            order_id = data.get('order_id')
            raw_data = data.get('raw_data')
            
            if not source or not order_id:
                raise ValueError("Missing required order data")
                
            self.logger.info(f"Processing order from {source}: {order_id}")
            
            if source == 'shopify':
                # First try to process using raw webhook data if available
                if raw_data:
                    await self._process_shopify_order(raw_data)
                else:
                    # Fetch complete order details using Shopify client
                    order = await self.shopify.get_order(order_id)
                    if not order:
                        raise ServiceClientError(f"Failed to fetch order details for {order_id}")
                    
                    # Process the order
                    await self._process_shopify_order(order)
                
            # Add handlers for other sources (eBay, Meta) here
            
        except Exception as e:
            self.logger.error(f"Error handling order creation: {e}")
            await self.emit(ServiceEvent.ERROR, {
                'event': 'order_created',
                'error': str(e),
                'order_id': data.get('order_id')
            })
    
    async def _process_shopify_order(self, order: Dict[str, Any]) -> None:
        """
        Process a Shopify order
        """
        try:
            order_id = order.get('id')
            if not order_id:
                raise ValueError("Order data missing ID field")
            
            # Process order logic here
            # For now, just emit the order processed event
            await self.emit(ServiceEvent.ORDER_UPDATED, {
                'order_id': order_id,
                'status': 'processed',
                'source': 'shopify',
                'order_data': order
            })
            self.logger.info(f"Successfully processed Shopify order: {order_id}")
            
        except Exception as e:
            self.logger.error(f"Error processing Shopify order: {e}")
            raise

    async def _task_scheduler(self) -> None:
        """Background task scheduler for periodic tasks"""
        while True:
            try:
                for task in self.tasks:
                    # Check if task should run
                    if (
                        not task.last_run or 
                        datetime.now() - task.last_run >= task.interval
                    ):
                        if not task.is_running:
                            task.is_running = True
                            try:
                                await task.func(*task.args, **task.kwargs)
                                task.last_run = datetime.now()
                            except Exception as e:
                                self.logger.error(f"Error in task {task.name}: {e}")
                            finally:
                                task.is_running = False
                
                # Sleep for a short interval before checking tasks again
                await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in task scheduler: {e}")
                await asyncio.sleep(5)  # Wait a bit longer on error

    async def shutdown(self) -> None:
        """Gracefully shutdown the ShoppyShop instance"""
        if not ShoppyShop._initialized:
            return
            
        self.logger.info("Shutting down ShoppyShop...")
        
        # Cancel task scheduler
        if self.task_loop:
            self.task_loop.cancel()
            try:
                await self.task_loop
            except asyncio.CancelledError:
                pass

        # Close all service clients
        for service in [self.shopify, self.ebay, self.meta]:
            if hasattr(service, 'client') and service.client:
                await service.client.close()
        
        ShoppyShop._initialized = False
        ShoppyShop._default_handlers_registered = False
        self.logger.info("ShoppyShop shutdown complete")

    async def __aenter__(self):
        """Async context manager entry"""
        if not ShoppyShop._initialized:
            await self._initialize_full()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.shutdown()
