# Wiener Netze Smartmeter Integration for Home Assistant

![Tests](https://github.com/maximilian-sh/WienerNetzeSmartmeter/actions/workflows/test.yml/badge.svg)
![Hassfest](https://github.com/maximilian-sh/WienerNetzeSmartmeter/actions/workflows/hassfest.yml/badge.svg)
![Validate](https://github.com/maximilian-sh/WienerNetzeSmartmeter/actions/workflows/validate.yml/badge.svg)
![Release](https://github.com/maximilian-sh/WienerNetzeSmartmeter/actions/workflows/release.yml/badge.svg)

## ⚠️ Maintenance Notice

This is a maintained fork of the original [WienerNetzeSmartmeter](https://github.com/DarwinsBuddy/WienerNetzeSmartmeter) repository. The original repository appears to be unresponsive, so I've taken over maintenance to keep this integration working.

**Current Status**: The integration is working and I'm maintaining it as needed. However, I'm not sure how much time I'll be able to invest in major feature development long-term. Feel free to use it - it's functional and I'll fix critical issues as they arise.

## About

This repo contains a custom component for [Home Assistant](https://www.home-assistant.io) for exposing a sensor
providing information about a registered [WienerNetze Smartmeter](https://www.wienernetze.at/smartmeter).

## FAQs

[FAQs](https://github.com/maximilian-sh/WienerNetzeSmartmeter/discussions)

## Installation

### Manual

Copy `<project-dir>/custom_components/wnsm` into `<home-assistant-root>/config/custom_components`

### HACS

1. Search for `Wiener Netze Smart Meter` or `wnsm` in HACS
2. Install
3. ...
4. Profit!

## Configure

You can choose between ui configuration or manual (by adding your credentials to `configuration.yaml` and `secrets.yaml` resp.)
After successful configuration you can add sensors to your favourite dashboard, or even to your energy dashboard to track your total consumption.

### UI

<img src="./doc/wnsm1.png" alt="Settings" width="500"/>
<img src="./doc/wnsm2.png" alt="Integrations" width="500"/>
<img src="./doc/wnsm3.png" alt="Add Integration" width="500"/>
<img src="./doc/wnsm4.png" alt="Search for WienerNetze" width="500"/>
<img src="./doc/wnsm5.png" alt="Authenticate with your credentials" width="500"/>
<img src="./doc/wnsm6.png" alt="Observe that all your smartmeters got imported" width="500"/>

### Manual

See [Example configuration files](https://github.com/maximilian-sh/WienerNetzeSmartmeter/blob/main/example/configuration.yaml)

## Copyright

This integration uses the API of https://www.wienernetze.at/smartmeter
All rights regarding the API are reserved by [Wiener Netze](https://www.wienernetze.at/impressum)

Special thanks to [platrysma](https://github.com/platysma)
for providing me a starting point [vienna-smartmeter](https://github.com/platysma/vienna-smartmeter)
and especially [florianL21](https://github.com/florianL21/)
for his [fork](https://github.com/florianL21/vienna-smartmeter/network)
