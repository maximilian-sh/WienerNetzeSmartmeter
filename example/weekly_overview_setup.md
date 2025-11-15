# Wochenübersicht für Wiener Netze Smartmeter

Diese Anleitung beschreibt den kompletten Weg von **0 auf 100**, um in Home Assistant eine Wochenübersicht mit täglichen Balken anzuzeigen – inklusive Wochensumme oben.

## 1. Sensor-ID herausfinden
1. Home Assistant → *Einstellungen* → *Geräte & Dienste* → *Entwicklerwerkzeuge* → Tab **Zustände**.
2. Suche nach deinem Wiener-Netze-Sensor (z. B. `sensor.at0010XXXXXXX`).
3. Kopiere die genaue Entity-ID – sie wird in allen folgenden Schritten benötigt.

## 2. Statistik-Sensor anlegen
1. Öffne `/config/custom.yaml` (oder eine andere Datei, die du für eigene Sensoren verwendest).
2. Trage dort **nur** folgenden Abschnitt ein und ersetze `<DEIN_SENSOR>` durch deine Entity-ID aus Schritt 1:

```yaml
sensor:
  - platform: statistics
    name: "Wochenverbrauch Summe"
    entity_id: <DEIN_SENSOR>
    state_characteristic: sum
    max_age:
      days: 7
    precision: 2
```

> Falls du bereits andere Sensoren in `custom.yaml` hast, füge einfach einen weiteren Eintrag unter `sensor:` hinzu.

## 3. Datei einbinden
Stelle sicher, dass die Datei in `configuration.yaml` eingebunden wird, z. B.:

```yaml
sensor: !include custom.yaml
```

(oder nutze einen spezifischen Dateinamen wie `custom_sensors.yaml`; wichtig ist nur, dass Home Assistant den Abschnitt lädt.)

## 4. Home Assistant neu starten
Nach dem Speichern → *Einstellungen* → *System* → *Neustart*, damit der Statistik-Sensor `sensor.wochenverbrauch_summe` erstellt wird.

## 5. Lovelace-Karte hinzufügen
Füge im Dashboard eine „Manual Card“ mit folgendem YAML ein und ersetze `<DEIN_SENSOR>` erneut:

```yaml
type: custom:mini-graph-card
name: Wochenübersicht - Täglicher Stromverbrauch
icon: mdi:chart-bar
entities:
  - entity: <DEIN_SENSOR>
    name: Täglicher Verbrauch
    aggregate_func: sum
    show_state: false
  - entity: sensor.wochenverbrauch_summe
    name: Wochen-Summe
    show_graph: false
    show_state: true
show:
  graph: bar
  fill: true
  points: hover
  labels: hover
  legend: false
  state: true
  name: true
  icon: true
hours_to_show: 168
points_per_hour: 0.142857
group_by: date
aggregate_func: sum
bar_spacing: 2
height: 200
font_size: 100
decimals: 2
unit: "kWh"
align_state: center
```

- Die Balken zeigen jeden Tag (letzte 7 Tage) an.
- Beim Hover siehst du den Tageswert.
- Oben wird automatisch `sensor.wochenverbrauch_summe` (Summe der Woche) angezeigt.

## 6. Optional
- Wenn du weitere Wochenübersichten brauchst, dupliziere einfach Sensor + Karte mit den jeweiligen Entity-IDs.
- Farben/Schriftgrößen kannst du in der Card nach Belieben anpassen.

Fertig! Damit ist alles aufgeräumt und nachvollziehbar – keine Legacy-Dateien mehr notwendig.
