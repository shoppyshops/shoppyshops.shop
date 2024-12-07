"""
ASGI config for shoppyshops project.
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter
import logging
from contextlib import asynccontextmanager
from shoppyshop.shoppyshop import ShoppyShop
import asyncio

logger = logging.getLogger(__name__)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shoppyshops.settings')

# Initialize this at module level to ensure single instance
_shop_instance = None
_lifespan_lock = asyncio.Lock()

@asynccontextmanager
async def lifespan(scope, receive, send):
    """
    Lifecycle manager for the ASGI application.
    Handles startup and shutdown of the ShoppyShop instance.
    """
    global _shop_instance
    
    async with _lifespan_lock:
        try:
            # Initialize ShoppyShop on startup only if not already initialized
            if _shop_instance is None:
                _shop_instance = await ShoppyShop.get_instance()
                logger.info("ShoppyShop initialized successfully")
            yield
        finally:
            # Shutdown ShoppyShop on application termination
            if _shop_instance is not None:
                await _shop_instance.shutdown()
                _shop_instance = None
                logger.info("ShoppyShop shutdown complete")

# Create the base application with protocol routing
django_application = ProtocolTypeRouter({
    "http": get_asgi_application(),
})

async def application(scope, receive, send):
    """
    ASGI application that combines Django with ShoppyShop lifecycle management
    """
    if scope["type"] == "lifespan":
        async with lifespan(scope, receive, send):
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    await send({"type": "lifespan.startup.complete"})
                elif message["type"] == "lifespan.shutdown":
                    await send({"type": "lifespan.shutdown.complete"})
                    break
    else:
        await django_application(scope, receive, send)
