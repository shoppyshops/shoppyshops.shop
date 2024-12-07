from django.shortcuts import render
from django.http import HttpResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
import json
import logging
import asyncio
from datetime import datetime
from .shoppyshop import ShoppyShop, ServiceEvent
from django.conf import settings

logger = logging.getLogger(__name__)

@csrf_exempt
@require_POST
async def shopify_webhook(request):
    """
    Webhook handler for Shopify events.
    Verifies the webhook and processes the order creation event.
    """
    try:
        # Log webhook headers
        logger.info("Received Shopify webhook:")
        
        # Get headers, supporting both direct and Django test client formats
        hmac = (request.headers.get('X-Shopify-Hmac-Sha256') or 
                request.META.get('HTTP_X_SHOPIFY_HMAC_SHA256') or
                request.META.get('HTTP_HTTP_X_SHOPIFY_HMAC_SHA256'))
        topic = (request.headers.get('X-Shopify-Topic') or 
                request.META.get('HTTP_X_SHOPIFY_TOPIC') or
                request.META.get('HTTP_HTTP_X_SHOPIFY_TOPIC'))
        
        logger.info(f"Extracted hmac: {hmac}")
        logger.info(f"Extracted topic: {topic}")
        
        if not hmac or not topic:
            logger.error("Missing required Shopify webhook headers")
            logger.error(f"Available headers: {list(request.headers.keys())}")
            logger.error(f"Available META: {[k for k in request.META.keys() if k.startswith('HTTP_')]}")
            return HttpResponse(status=401)
            
        if topic != 'orders/create':
            logger.info(f"Ignoring non-order webhook: {topic}")
            return HttpResponse(status=200)
            
        # Get ShoppyShop instance and initialize services
        shop = await ShoppyShop.get_instance()
        
        # Initialize services if needed
        try:
            await shop.initialize_services()
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            return HttpResponse(status=503)  # Service Unavailable
            
        try:
            data = json.loads(request.body)
            order_id = data.get('id')
            
            if not order_id:
                logger.error("Missing order ID in webhook data")
                return HttpResponse(status=400)
            
            # Convert numeric ID to Shopify's gid format
            gid = f"gid://shopify/Order/{order_id}"
            logger.info(f"Converting order ID {order_id} to GID: {gid}")
            
            # Verify Shopify client exists
            if not shop.shopify:
                logger.error("Shopify client not available")
                return HttpResponse(status=503)  # Service Unavailable
            
            # Emit order created event with properly formatted ID
            await shop.emit(ServiceEvent.ORDER_CREATED, {
                'order_id': gid,
                'source': 'shopify',
                'raw_data': data
            })
            
            logger.info(f"Queued Shopify order for processing: {gid}")
            return HttpResponse(status=200)  # OK - Webhook received successfully
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in webhook body: {e}")
            return HttpResponse(status=400)
            
    except Exception as e:
        logger.error(f"Error processing Shopify webhook: {e}", exc_info=True)
        return HttpResponse(status=500)

async def orders_list(request):
    """HTMX endpoint for fetching recent orders"""
    shop = await ShoppyShop.get_instance()
    try:
        start_time = datetime.now()
        
        # Ensure services are initialized
        await shop.initialize_services()
        
        # Fetch recent orders from Shopify using get_orders
        orders = await shop.shopify.get_orders(
            limit=5,
            sort_key="CREATED_AT",
            reverse=True
        )
        
        # Calculate timing
        fetch_time = (datetime.now() - start_time).total_seconds()
        
        # Extract order details
        order_details = [
            {
                'number': order.get('orderNumber', 'N/A'),
                'status': order.get('fulfillmentStatus', 'unknown')
            }
            for order in orders
        ]
        
        # Format order details with proper quote escaping
        order_summaries = [
            f"{details['number']}({details['status']})"
            for details in order_details
        ]
        
        logger.info(
            f"Fetched {len(orders)} orders in {fetch_time:.2f}s: {order_summaries}"
        )
        
        return render(request, 'partials/orders_list.html', {'orders': orders})
    except Exception as e:
        logger.error(f"Error fetching orders: {e}")
        return HttpResponse(
            """<div class="text-red-500">Error loading orders. Please try again.</div>""",
            status=500
        )

async def service_status(request):
    """HTMX endpoint for service status updates"""
    shop = await ShoppyShop.get_instance()
    try:
        statuses = {
            'shopify': await shop.shopify.check_status(),
            'ebay': await shop.ebay.check_status(),
            'meta': await shop.meta.check_status(),
        }
        return render(request, 'partials/service_status.html', {'statuses': statuses})
    except Exception as e:
        logger.error(f"Error checking service status: {e}")
        return HttpResponse(
            """<div class="text-red-500">Error checking services. Please try again.</div>""",
            status=500
        )

async def event_stream(request):
    """SSE endpoint for real-time updates"""
    shop = await ShoppyShop.get_instance()
    connection_id = id(request)
    logger.info(f"SSE connection established: {connection_id}")
    
    async def event_generator():
        queue = asyncio.Queue()
        handlers = []
        handler_count = 0
        
        # Send initial retry timeout
        yield f"retry: {settings.SSE_RETRY_TIMEOUT}\n\n"
        
        # Event handler that puts events into the queue
        async def handle_event(event_data):
            logger.info(f"Handling event for connection {connection_id}: {event_data}")
            notification_html = render_to_string('partials/notification.html', {
                'type': event_data.get('type', 'info'),
                'message': event_data.get('message', 'Update received'),
                'timestamp': datetime.now()
            })
            logger.debug(f"Rendered notification HTML: {notification_html!r}")
            
            await queue.put({
                'event': 'notification',
                'data': notification_html
            })
        
        # Register handlers for events we want to stream
        def register_handler(event: ServiceEvent, message_func, name: str):
            nonlocal handler_count
            
            async def event_handler(data):
                logger.info(f"Event handler {name} called for {connection_id}")
                await handle_event(message_func(data))
            event_handler.__name__ = f"notify_{name}_{connection_id}"
            
            shop.on(event, event_handler)
            handlers.append((event, event_handler))
            handler_count += 1
        
        # Register all handlers first
        register_handler(
            ServiceEvent.ORDER_CREATED,
            lambda data: {
                'type': 'success',
                'message': f"New order received: #{data.get('order_id')}"
            },
            'order_created'
        )
        
        register_handler(
            ServiceEvent.ORDER_UPDATED,
            lambda data: {
                'type': 'success',
                'message': f"Order #{data.get('order_id')} has been updated"
            },
            'order_updated'
        )
        
        register_handler(
            ServiceEvent.ERROR,
            lambda data: {
                'type': 'error',
                'message': f"Error: {data.get('error')}"
            },
            'error'
        )
        
        logger.info(f"Registered {handler_count} notification handlers for connection {connection_id}")
        
        try:
            logger.info(f"Starting event stream for {connection_id}")
            # Send initial connection event
            yield "event: open\ndata: {}\n\n"
            
            while True:
                event = await queue.get()
                logger.info(f"Got event for {connection_id}: {event}")
                # Format SSE event - don't JSON encode HTML content
                message = f"event: {event['event']}\ndata: {event['data']}\n\n"
                logger.debug(f"Sending SSE message: {message!r}")
                yield message
        except Exception as e:
            logger.error(f"Error in event stream for {connection_id}: {e}")
            # Send error event
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
        finally:
            # Clean up event handlers
            removed_count = 0
            for event, handler in handlers:
                if handler in shop.event_handlers[event]:
                    shop.event_handlers[event].remove(handler)
                    removed_count += 1
            logger.info(f"Cleaned up {removed_count} handlers for connection {connection_id}")

    response = StreamingHttpResponse(
        event_generator(),
        content_type='text/event-stream'
    )
    
    # Add SSE-specific headers
    response['Cache-Control'] = 'no-cache'
    response['Connection'] = 'keep-alive'
    response['X-Accel-Buffering'] = 'no'
    
    return response
