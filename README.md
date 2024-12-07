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

1. Run tests once:
   ```bash
   pytest
   ```

2. Watch mode (automatically run tests when files change):
   ```bash
   ptw .  # Interactive mode
   # OR
   ptw . --now  # Run tests immediately and watch for changes
   ```
   
   Interactive controls in watch mode:
   - `Enter`: Run tests manually
   - `r`: Reset runner arguments
   - `c`: Change runner arguments
   - `f`: Run only failed tests
   - `p`: Enable PDB debugger on failures
   - `v`: Increase verbosity
   - `e`: Clear screen
   - `q`: Quit watcher

3. Watch mode with coverage reporting:
   ```bash
   pytest --cov=shoppyshops --cov-report=term-missing
   ```

4. Generate HTML coverage report:
   ```bash
   pytest --cov=shoppyshops --cov-report=html
   ```

## Development Servers
Run these in separate terminals:

```bash
# Terminal 1: Django development server
./manage.py runserver

# Terminal 2: Live reload
./manage.py livereload

# Terminal 3: Test watcher
ptw . --now  # Run tests immediately and watch for changes
```
