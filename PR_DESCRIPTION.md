# Add Optima Aktiv Verbrauchspreis Sensor

## Summary

This PR adds a new sensor to display the current Optima Aktiv Verbrauchspreis (consumption price) from Wien Energie, with support for selecting the Zusammensetzung (energy composition: okopure, sonnenmix, or basismix).

## Features

### ✨ New Optima Aktiv Price Sensor
- Fetches Verbrauchspreis from Wien Energie WordPress REST API
- Supports all three Zusammensetzung options: okopure, sonnenmix, basismix
- Uses clean API endpoint (no HTML scraping)
- Proper error handling and logging

### 🔧 Enhanced Config Flow
- Multi-step setup process:
  1. Username/Password authentication
  2. **Optional** Optima Aktiv sensor (user can opt-in)
  3. Zusammensetzung selection (if enabled)
- Users can skip the price sensor if not needed
- Proper data initialization and validation

### 🐛 Bug Fixes
- Fixed `KeyError` in `importer.py` when `unitOfMeasurement` is missing
- Fixed meter reading loop to stop after first successful reading
- Improved sensor setup error handling to prevent integration failure

### ⚡ Performance Improvements
- Sensor respects quarter-hour granularity for faster updates
- Updates every 20 minutes when quarter-hour data is available
- Keeps 6-hour interval for daily updates

## Technical Details

- **API Endpoint**: `https://www.wienenergie.at/wp-json/tarife/tarifberater`
- **No new dependencies**: Uses existing `requests` library
- **Backward compatible**: All existing functionality unchanged
- **Optional feature**: Users must opt-in during setup

## Files Changed

- `custom_components/wnsm/optima_aktiv_sensor.py` (new file, 201 lines)
- `custom_components/wnsm/config_flow.py` (+89 lines)
- `custom_components/wnsm/sensor.py` (+69 lines)
- `custom_components/wnsm/const.py` (+1 line)
- `custom_components/wnsm/translations/en.json` (+14 lines)
- `custom_components/wnsm/wnsm_sensor.py` (+23 lines)
- `custom_components/wnsm/importer.py` (+10 lines, bug fix)

## Testing

✅ Tested locally with all three Zusammensetzung options
✅ Verified API responses and price extraction
✅ Confirmed backward compatibility
✅ Tested error handling scenarios

## Usage

After installation, users will see a new step during integration setup asking if they want to add the Optima Aktiv price sensor. If enabled, they can select their Zusammensetzung, and the sensor will display the current Verbrauchspreis in Cent/kWh.

The sensor updates automatically based on the user's granularity settings (every 20 minutes for quarter-hour data, or every 6 hours for daily data).
