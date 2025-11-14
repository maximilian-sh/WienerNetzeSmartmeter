#!/usr/bin/env python3
"""
Test script to verify Optima Aktiv price scraping locally
"""
import sys
import re
import requests
from lxml import html
from datetime import date

WIEN_ENERGIE_OPTIMA_AKTIV_BASE_URL = "https://www.wienenergie.at/privat/produkte/strom/optima-aktiv/"

def build_url(zusammensetzung: str) -> str:
    """Build the URL with the selected Zusammensetzung option."""
    options = f"SOPTA_0001-{zusammensetzung}-none"
    prozessdatum = date.today().strftime("%Y-%m-%d")
    return f"{WIEN_ENERGIE_OPTIMA_AKTIV_BASE_URL}?prozessdatum={prozessdatum}&options={options}"

def fetch_price_data(zusammensetzung: str = "basismix"):
    """Fetch and parse price data from Wien Energie website."""
    url = build_url(zusammensetzung)
    print(f"Fetching: {url}\n")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    
    try:
        # Don't request compression - let requests handle it automatically
        headers_no_compression = headers.copy()
        headers_no_compression.pop("Accept-Encoding", None)
        
        response = requests.get(url, headers=headers_no_compression, timeout=15)
        response.raise_for_status()
        
        # Ensure we decode the content properly
        if response.encoding is None:
            response.encoding = 'utf-8'
        
        print(f"✓ Response status: {response.status_code}")
        print(f"✓ Response length: {len(response.text)} bytes")
        print(f"✓ Content-Type: {response.headers.get('Content-Type', 'unknown')}")
        print(f"✓ Encoding: {response.encoding}\n")
        
        # Check if we got HTML content
        if not response.text or len(response.text) < 1000:
            print("✗ Received suspiciously short response")
            return None
        
        # Parse HTML
        tree = html.fromstring(response.content)
        
        verbrauchspreis = None
        
        # Strategy 1: Look for price elements with class containing "cardPrice"
        price_elements = tree.xpath('//p[contains(@class, "cardPrice")]')
        print(f"Found {len(price_elements)} price elements with 'cardPrice' class")
        
        # Strategy 2: Look for spans with "Verbrauchspreis" label
        verbrauchspreis_spans = tree.xpath('//span[contains(text(), "Verbrauchspreis")]')
        print(f"Found {len(verbrauchspreis_spans)} spans with 'Verbrauchspreis' text")
        
        # Strategy 3: Look for any element containing "Verbrauchspreis"
        verbrauchspreis_elements = tree.xpath('//*[contains(text(), "Verbrauchspreis")]')
        print(f"Found {len(verbrauchspreis_elements)} elements containing 'Verbrauchspreis'\n")
        
        # Try to find price near the Verbrauchspreis label
        print("Trying Strategy 1: Finding price near Verbrauchspreis label...")
        for span in verbrauchspreis_spans:
            parent = span.getparent()
            if parent is not None:
                container = parent.getparent() if parent.getparent() is not None else parent
                price_texts = container.xpath('.//p[contains(@class, "cardPrice")]//text()')
                if not price_texts:
                    price_texts = container.xpath('.//text()[contains(., "Cent/kWh")]')
                for price_text in price_texts:
                    match = re.search(r'([\d,]+)\s*Cent/kWh', price_text)
                    if match:
                        verbrauchspreis_str = match.group(1).replace(',', '.')
                        verbrauchspreis = float(verbrauchspreis_str)
                        print(f"✓ Found Verbrauchspreis: {verbrauchspreis} Cent/kWh")
                        break
                if verbrauchspreis is not None:
                    break
        
        # Fallback: parse all price elements
        if verbrauchspreis is None:
            print("\nTrying Strategy 2: Parsing all price elements...")
            for element in price_elements:
                text = element.text_content().strip()
                print(f"  Price element text: {text[:100]}")
                if "Cent/kWh" in text:
                    match = re.search(r'([\d,]+)\s*Cent/kWh', text)
                    if match:
                        verbrauchspreis_str = match.group(1).replace(',', '.')
                        verbrauchspreis = float(verbrauchspreis_str)
                        print(f"✓ Found Verbrauchspreis: {verbrauchspreis} Cent/kWh")
                        break
        
        # Another fallback: search in all text nodes
        if verbrauchspreis is None:
            print("\nTrying Strategy 3: Searching all text nodes...")
            all_text_nodes = tree.xpath('//text()[contains(., "Cent/kWh")]')
            print(f"Found {len(all_text_nodes)} text nodes containing 'Cent/kWh'")
            for text_node in all_text_nodes:
                match = re.search(r'([\d,]+)\s*Cent/kWh', text_node)
                if match:
                    verbrauchspreis_str = match.group(1).replace(',', '.')
                    verbrauchspreis = float(verbrauchspreis_str)
                    print(f"✓ Found Verbrauchspreis: {verbrauchspreis} Cent/kWh")
                    break
        
        # Last resort: regex search on full HTML
        if verbrauchspreis is None:
            print("\nTrying Strategy 4: Regex search on full HTML...")
            all_text = response.text
            patterns = [
                r'Verbrauchspreis[^>]*>.*?([\d,]+)\s*Cent/kWh',
                r'([\d,]+)\s*Cent/kWh[^<]*Verbrauchspreis',
                r'Verbrauchspreis.*?([\d,]+)\s*Cent/kWh',
            ]
            for i, pattern in enumerate(patterns, 1):
                match = re.search(pattern, all_text, re.DOTALL | re.IGNORECASE)
                if match:
                    verbrauchspreis_str = match.group(1).replace(',', '.')
                    try:
                        verbrauchspreis = float(verbrauchspreis_str)
                        print(f"✓ Found Verbrauchspreis with pattern {i}: {verbrauchspreis} Cent/kWh")
                        break
                    except ValueError:
                        continue
        
        # Final fallback: simple regex for any price
        if verbrauchspreis is None:
            print("\nTrying Strategy 5: Simple regex for any price pattern...")
            all_text = response.text
            price_patterns = [
                r'([\d,]+)\s*Cent/kWh',  # German format with comma
                r'([\d.]+)\s*Cent/kWh',  # English format with dot
            ]
            for pattern in price_patterns:
                matches = re.findall(pattern, all_text)
                if matches:
                    print(f"Found {len(matches)} matches with pattern: {pattern}")
                    for match in matches:
                        try:
                            price_str = match.replace(',', '.')
                            price_val = float(price_str)
                            # Sanity check: price should be between 10 and 50 Cent/kWh
                            if 10.0 <= price_val <= 50.0:
                                verbrauchspreis = price_val
                                print(f"✓ Found Verbrauchspreis: {verbrauchspreis} Cent/kWh")
                                break
                        except ValueError:
                            continue
                    if verbrauchspreis is not None:
                        break
        
        # Strategy 6: Look for JSON data embedded in HTML
        if verbrauchspreis is None:
            print("\nTrying Strategy 6: Parsing embedded JSON data...")
            all_text = response.text
            # Look for patterns like "verbrauchspreis-product":"17.4237" or similar
            json_patterns = [
                r'"verbrauchspreis[^"]*":"([\d.]+)"',
                r'"verbrauchspreis[^"]*":"([\d,]+)"',
                r'verbrauchspreis[^:]*:\s*["\']?([\d.]+)',
                r'verbrauchspreis[^:]*:\s*["\']?([\d,]+)',
            ]
            for pattern in json_patterns:
                matches = re.findall(pattern, all_text, re.IGNORECASE)
                if matches:
                    print(f"Found {len(matches)} matches with JSON pattern: {pattern}")
                    for match in matches:
                        try:
                            price_str = match.replace(',', '.')
                            price_val = float(price_str)
                            # Sanity check: price should be between 10 and 50 Cent/kWh
                            if 10.0 <= price_val <= 50.0:
                                verbrauchspreis = price_val
                                print(f"✓ Found Verbrauchspreis in JSON: {verbrauchspreis} Cent/kWh")
                                break
                        except ValueError:
                            continue
                    if verbrauchspreis is not None:
                        break
        
        if verbrauchspreis is None:
            print("\n✗ Could not parse Verbrauchspreis")
            print(f"\nHTML sample (first 1000 chars):")
            print(response.text[:1000])
            print("\n" + "="*80)
            print("Searching for 'Verbrauchspreis' in HTML...")
            if "Verbrauchspreis" in response.text:
                idx = response.text.find("Verbrauchspreis")
                print(f"Found at position {idx}")
                print("Context (500 chars before and after):")
                start = max(0, idx - 250)
                end = min(len(response.text), idx + 250)
                print(response.text[start:end])
            else:
                print("'Verbrauchspreis' not found in HTML!")
            return None
        
        print(f"\n✅ Successfully parsed Verbrauchspreis: {verbrauchspreis} Cent/kWh")
        return verbrauchspreis
        
    except requests.RequestException as e:
        print(f"\n✗ Error fetching Wien Energie website: {e}")
        return None
    except Exception as e:
        print(f"\n✗ Error parsing Wien Energie website: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("="*80)
    print("Testing Optima Aktiv Price Scraping")
    print("="*80)
    print()
    
    zusammensetzungen = ["basismix", "sonnenmix", "okopure"]
    
    for zus in zusammensetzungen:
        print(f"\n{'='*80}")
        print(f"Testing Zusammensetzung: {zus}")
        print('='*80)
        result = fetch_price_data(zus)
        if result:
            print(f"✅ {zus}: {result} Cent/kWh")
        else:
            print(f"❌ {zus}: Failed to parse")
        print()
    
    sys.exit(0)

