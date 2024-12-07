"""
ASGI config for shoppyshops project.
"""

import os
from django.core.asgi import get_asgi_application
from django.conf import settings
import logging
from contextlib import asynccontextmanager
from shoppyshop.shoppyshop import ShoppyShop

logger = logging.getLogger(__name__)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shoppyshops.settings')

@asynccontextmanager
async def lifespan(scope, receive, send):
    """
    Lifecycle manager for the ASGI application.
    Handles startup and shutdown of the ShoppyShop instance.
    """
    try:
        # Initialize ShoppyShop on startup
        shop = await ShoppyShop.get_instance()
        logger.info("ShoppyShop initialized successfully")
        yield
    finally:
        # Shutdown ShoppyShop on application termination
        await shop.shutdown()
        logger.info("ShoppyShop shutdown complete")

async def application(scope, receive, send):
    """
    ASGI application that combines Django with ShoppyShop lifecycle management
    """
    if scope["type"] == "lifespan":
        async with lifespan(scope, receive, send):
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
                message = await receive()
            if message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
    else:
        django_app = get_asgi_application()
        await django_app(scope, receive, send)
