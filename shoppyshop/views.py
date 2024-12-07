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

logger = logging.getLogger(__name__)

@csrf_exempt
@require_POST
async def shopify_webhook(request):
    """
    Webhook handler for Shopify events.
    Verifies the webhook and processes the order creation event.
    """
    try:
        # Get ShoppyShop instance
        shop = await ShoppyShop.get_instance()
        
        # Verify Shopify webhook (you might want to add more verification)
        hmac = request.headers.get('X-Shopify-Hmac-Sha256')
        topic = request.headers.get('X-Shopify-Topic')
        
        if not hmac or not topic:
            logger.error("Missing required Shopify webhook headers")
            return HttpResponse(status=401)
            
        if topic != 'orders/create':
            logger.info(f"Ignoring non-order webhook: {topic}")
            return HttpResponse(status=200)
            
        # Parse the webhook data
        try:
            data = json.loads(request.body)
            order_id = data.get('id')
            if not order_id:
                logger.error("Missing order ID in webhook data")
                return HttpResponse(status=400)
                
            # Emit order created event
            await shop.emit(ServiceEvent.ORDER_CREATED, {
                'order_id': order_id,
                'source': 'shopify',
                'raw_data': data
            })
            
            logger.info(f"Successfully processed Shopify order webhook: {order_id}")
            return HttpResponse(status=200)
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in webhook body: {e}")
            return HttpResponse(status=400)
            
    except Exception as e:
        logger.error(f"Error processing Shopify webhook: {e}")
        return HttpResponse(status=500)

async def orders_list(request):
    """HTMX endpoint for fetching recent orders"""
    shop = await ShoppyShop.get_instance()
    try:
        # Ensure services are initialized
        await shop.initialize_services()
        
        # Fetch recent orders from Shopify using get_orders
        orders = await shop.shopify.get_orders(
            limit=5,
            sort_key="CREATED_AT",
            reverse=True
        )
        logger.info(f"Fetched orders: {orders}")
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
    
    async def event_generator():
        queue = asyncio.Queue()
        
        # Event handler that puts events into the queue
        async def handle_event(event_data):
            # Render the notification template
            notification_html = render_to_string('partials/notification.html', {
                'type': event_data.get('type', 'info'),
                'message': event_data.get('message', 'Update received'),
                'timestamp': datetime.now()
            })
            
            await queue.put({
                'event': 'notification',
                'data': notification_html
            })
        
        # Register handlers for events we want to stream
        shop.on(ServiceEvent.ORDER_CREATED, lambda data: handle_event({
            'type': 'success',
            'message': f"New order received: #{data.get('order_id')}"
        }))
        
        shop.on(ServiceEvent.ORDER_UPDATED, lambda data: handle_event({
            'type': 'success',
            'message': f"Order #{data.get('order_id')} has been updated"
        }))
        
        shop.on(ServiceEvent.ERROR, lambda data: handle_event({
            'type': 'error',
            'message': f"Error: {data.get('error')}"
        }))
        
        try:
            while True:
                event = await queue.get()
                yield f"event: {event['event']}\ndata: {event['data']}\n\n"
        except Exception as e:
            logger.error(f"Error in event stream: {e}")
        finally:
            # Clean up event handlers
            shop.event_handlers[ServiceEvent.ORDER_CREATED].clear()
            shop.event_handlers[ServiceEvent.ORDER_UPDATED].clear()
            shop.event_handlers[ServiceEvent.ERROR].clear()
    
    return StreamingHttpResponse(
        event_generator(),
        content_type='text/event-stream'
    )
