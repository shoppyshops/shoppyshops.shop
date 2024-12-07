import json
import asyncio
import httpx
from pathlib import Path
from datetime import datetime
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Simulates Shopify webhooks for testing the interface'

    def add_arguments(self, parser):
        parser.add_argument(
            '--event',
            type=str,
            default='orders/create',
            help='Webhook event type to simulate (default: orders/create)'
        )
        parser.add_argument(
            '--count',
            type=int,
            default=1,
            help='Number of webhook events to send (default: 1)'
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=1.0,
            help='Delay between events in seconds (default: 1.0)'
        )

    def load_sample_order(self):
        mock_path = Path(__file__).parent.parent.parent.parent / 'tests' / 'mocks' / 'shopify' / 'webhooks' / 'order_created.json'
        with open(mock_path) as f:
            order = json.load(f)
        # Update the timestamp to current time
        order['created_at'] = datetime.now().isoformat()
        return order

    async def send_webhook(self, event_type, payload):
        webhook_url = 'http://localhost:8000/shoppyshop/webhooks/shopify/'
        headers = {
            'Content-Type': 'application/json',
            'X-Shopify-Topic': event_type,
            'X-Shopify-Hmac-SHA256': 'test_hmac',
            'X-Shopify-Shop-Domain': 'test-store.myshopify.com',
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(webhook_url, json=payload, headers=headers)
                return response.status_code == 200
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error sending webhook: {str(e)}'))
                return False

    def handle(self, *args, **options):
        event_type = options['event']
        count = options['count']
        delay = options['delay']
        
        self.stdout.write(f'Simulating {count} {event_type} webhook events...')
        
        async def run_simulation():
            for i in range(count):
                try:
                    payload = self.load_sample_order()
                    success = await self.send_webhook(event_type, payload)
                    
                    status = 'SUCCESS' if success else 'FAILED'
                    self.stdout.write(
                        self.style.SUCCESS(f'Webhook {i+1}/{count}: {status}')
                        if success else
                        self.style.ERROR(f'Webhook {i+1}/{count}: {status}')
                    )
                    
                    if i < count - 1:
                        await asyncio.sleep(delay)
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error in simulation: {str(e)}'))
                    return

        asyncio.run(run_simulation())
        self.stdout.write(self.style.SUCCESS('Webhook simulation completed'))