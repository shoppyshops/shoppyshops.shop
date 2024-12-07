# ShoppyShops.shop

A Django-based e-commerce platform with AI integration and real-time streaming capabilities.

## Quick Start
1. Clone the repository
   ```bash
   git clone https://github.com/shoppyshops/shoppyshops.shop.git
   cd shoppyshops.shop
   ```

2. Set up environment with Poetry
   ```bash
   # Install Poetry if you haven't already
   curl -sSL https://install.python-poetry.org | python3 -

   # Install dependencies and create virtual environment
   poetry install

   # Activate the virtual environment
   poetry shell
   ```

3. Configure environment variables
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. Run development servers
   ```bash
   # Terminal 1: Django development server
   ./manage.py runserver

   # Terminal 2: Live reload
   ./manage.py livereload

   # Terminal 3: Test watcher
   ptw . --now  # Run tests immediately and watch for changes
   ```

## Development Setup
- Python 3.11+
- Poetry for dependency management
- Django 5.0+
- OpenAI API key

## Dependencies Management
- Add new dependencies: `poetry add package_name`
- Add dev dependencies: `poetry add --group dev package_name`
- Update dependencies: `poetry update`
- Export requirements: `poetry export -f requirements.txt --output requirements.txt`

## AI-Assisted Development
This project uses AI-assisted development with Cursor editor:
1. Install Cursor: https://cursor.sh
2. Copy contents of `METHODOLOGY.md` into Cursor's AI Rules
3. Follow development methodology for consistency

## Project Structure
```
shoppyshops.shop/
├── shoppyshops/        # Django project settings
├── shoppyshop/         # Main service integration app
├── shopify/            # Shopify integration
├── ebay/              # eBay integration
├── meta/              # Meta integration (read-only)
├── static/            # Static files
├── templates/         # HTML templates
└── tests/             # Test suite
```

## Contributing
- See `METHODOLOGY.md` for development approach
- See `SPECIFICATIONS.md` for feature details

## Running Tests

There are several ways to run tests:

### 1. Watch Mode (Recommended)
```bash
# Watch mock tests (default)
ptw . "-m mock" --now

# Watch real API tests
ptw . "-m real" --now

# Watch specific test file
ptw tests/test_webhooks.py --now

# Watch specific test
ptw "tests/test_webhooks.py::test_shopify_webhook_order_created" --now
```

The commands break down as:
- `ptw .` - Watch current directory
- `"-m real"` - Only run tests marked with @pytest.mark.real
- `--now` - Run tests immediately instead of waiting for changes

### 2. Single Run
```bash
# Run mock tests
pytest -m mock

# Run real API tests
pytest -m real

# Run specific test
pytest tests/test_webhooks.py::test_shopify_webhook_order_created
```

### 3. Coverage Reports
```bash
# Terminal coverage report
pytest --cov=shoppyshops --cov-report=term-missing

# HTML coverage report
pytest --cov=shoppyshops --cov-report=html
```

### 4. Development Workflow
For development, run these in separate terminals:
```bash
# Terminal 1: Watch mock tests
ptw . "-m mock" --now

# Terminal 2: Watch real API tests
ptw . "-m real" --now

# Terminal 3: Django development server
./manage.py runserver

# Terminal 4: Live reload
./manage.py livereload
```

### 5. Test Environment
- Tests use mock data by default for speed and reliability
- Use `-m real` to run tests against real services
- Mock data is stored in `tests/mocks/`
- Environment variables are loaded from `.env`

### 6. Writing Tests
- Place tests in `tests/` directory
- Use appropriate markers (`@pytest.mark.mock`, `@pytest.mark.real`, etc.)
- Mock external services by default, use `-m real` for real API calls
- Follow existing patterns for consistency
