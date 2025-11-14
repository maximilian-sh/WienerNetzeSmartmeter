#!/bin/bash
# Setup virtual environment for testing

cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing dependencies..."
pip install requests lxml

echo ""
echo "✅ Setup complete!"
echo ""
echo "To run the test:"
echo "  source venv/bin/activate"
echo "  python3 test_price_scraping.py"
echo ""

