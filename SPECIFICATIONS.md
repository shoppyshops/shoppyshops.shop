# Project Specifications

## Core Architecture

### Environment Configuration (.env)
```python
# Shopify Credentials
SHOPIFY_ACCESS_TOKEN=''
SHOPIFY_STORE_URL=''

# eBay Credentials
EBAY_APP_ID=''
EBAY_CERT_ID=''
EBAY_DEV_ID=''
EBAY_AUTH_TOKEN=''

# Meta Credentials (read-only)
META_ACCESS_TOKEN=''
META_ACCOUNT_ID=''
```

### Service Classes

#### Main Controller (`shoppyshop/shoppyshop.py`)
```python
class ShoppyShop:
    """Main controller class managing service integrations"""
    def __init__(self):
        """Initialize services with credentials from environment"""
        self.shopify = Shopify(
            token=settings.SHOPIFY_ACCESS_TOKEN,
            store_url=settings.SHOPIFY_STORE_URL
        )
        self.ebay = Ebay(
            app_id=settings.EBAY_APP_ID,
            cert_id=settings.EBAY_CERT_ID,
            dev_id=settings.EBAY_DEV_ID,
            auth_token=settings.EBAY_AUTH_TOKEN
        )
        self.meta = Meta(
            token=settings.META_ACCESS_TOKEN,
            account_id=settings.META_ACCOUNT_ID
        )
    
    async def sync_inventory(self):
        """Cross-platform inventory synchronization"""
        pass
    
    async def process_orders(self):
        """Order processing and fulfillment"""
        pass

#### Shopify Integration (`shopify/shopify.py`)
```python
class Shopify:
    """Shopify store management interface"""
    def __init__(self, token: str, store_url: str):
        self.token = token
        self.store_url = store_url
    
    async def get_products(self):
        """Retrieve product catalog"""
        pass
    
    async def update_inventory(self):
        """Update product inventory"""
        pass
```

#### eBay Integration (`ebay/ebay.py`)
```python
class Ebay:
    """eBay fulfillment management interface"""
    def __init__(self, app_id: str, cert_id: str, dev_id: str, auth_token: str):
        self.app_id = app_id
        self.cert_id = cert_id
        self.dev_id = dev_id
        self.auth_token = auth_token
    
    async def list_product(self):
        """List product on eBay"""
        pass
    
    async def process_order(self):
        """Process eBay order"""
        pass
```

#### Meta Integration (`meta/meta.py`)
```python
class Meta:
    """Meta advertising insights interface (read-only)"""
    def __init__(self, token: str, account_id: str):
        self.token = token
        self.account_id = account_id
    
    async def get_campaign_insights(self):
        """Retrieve campaign performance data"""
        pass
    
    async def get_catalog_stats(self):
        """Get product catalog statistics"""
        pass
```

## Django Apps and Models

### 1. Shopify (`shopify/models.py`)
```python
# models.py
class ShopifyProduct(models.Model):
    """Shopify product data"""
    shopify_id = models.CharField(max_length=255, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    inventory_quantity = models.IntegerField()
    variants = models.JSONField()
    last_synced = models.DateTimeField(auto_now=True)

class ShopifyOrder(models.Model):
    """Shopify order data"""
    shopify_id = models.CharField(max_length=255, unique=True)
    order_number = models.CharField(max_length=255)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    fulfillment_status = models.CharField(max_length=50)
    items = models.JSONField()
    created_at = models.DateTimeField()
```

### 2. eBay (`ebay/models.py`)
```python
# models.py
class EbayListing(models.Model):
    """eBay listing data"""
    ebay_id = models.CharField(max_length=255, unique=True)
    shopify_product = models.ForeignKey('shopify.ShopifyProduct', on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField()
    status = models.CharField(max_length=50)
    last_updated = models.DateTimeField(auto_now=True)

class EbayOrder(models.Model):
    """eBay order data"""
    ebay_id = models.CharField(max_length=255, unique=True)
    buyer_username = models.CharField(max_length=255)
    order_total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=50)
    items = models.JSONField()
    shipping_details = models.JSONField()
    created_at = models.DateTimeField()
```

### 3. Meta (`meta/models.py`)
```python
# models.py
class MetaCampaignInsight(models.Model):
    """Meta campaign performance data (read-only)"""
    campaign_id = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    spend = models.DecimalField(max_digits=10, decimal_places=2)
    impressions = models.IntegerField()
    clicks = models.IntegerField()
    conversions = models.IntegerField()
    last_synced = models.DateTimeField(auto_now=True)

class MetaProductCatalog(models.Model):
    """Meta product catalog data (read-only)"""
    catalog_id = models.CharField(max_length=255, unique=True)
    shopify_product = models.ForeignKey('shopify.ShopifyProduct', on_delete=models.CASCADE)
    status = models.CharField(max_length=50)
    insights = models.JSONField()  # Engagement metrics
    last_synced = models.DateTimeField(auto_now=True)
```

## Project Structure
```
shoppyshops.shop/
├── shoppyshops/        # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── shoppyshop/         # Main service integration app
│   └── shoppyshop.py   # Main controller class
├── shopify/            # Shopify integration
│   ├── shopify.py      # Shopify service class
│   └── models.py       # Shopify models
├── ebay/              # eBay integration
│   ├── ebay.py        # eBay service class
│   └── models.py      # eBay models
├── meta/              # Meta integration (read-only)
│   ├── meta.py        # Meta service class
│   └── models.py      # Meta models
├── static/            # Static files
├── templates/         # HTML templates
├── tests/             # Test suite
├── .env              # Environment variables
└── .env.example      # Example environment configuration
```

## Data Flow
1. Product Management
   ```python
   shop = ShoppyShop(tokens)
   products = await shop.shopify.get_products()
   await shop.ebay.list_products(products)
   # Meta insights only
   insights = await shop.meta.get_catalog_stats()
   ```

2. Order Processing
   ```python
   orders = await shop.ebay.get_new_orders()
   for order in orders:
       await shop.shopify.create_fulfillment(order)
   ```

## Security and Performance
- Credentials stored in environment variables
- Environment variables loaded via python-dotenv
- Different .env files for development/staging/production
- Encrypted environment variable storage in deployment
- Rate limiting per service
- Async operations
- Background sync tasks
- Read-only Meta operations