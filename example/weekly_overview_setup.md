# Wochenübersicht für Wiener Netze Smartmeter

Diese Anleitung beschreibt den kompletten Weg von **0 auf 100**, um in Home Assistant eine Wochenübersicht mit täglichen Balken anzuzeigen – inklusive Wochensumme oben.

## 1. Sensor-ID herausfinden

1. Home Assistant → _Einstellungen_ → _Geräte & Dienste_ → _Entwicklerwerkzeuge_ → Tab **Zustände**.
2. Suche nach deinem Wiener-Netze-Sensor (z. B. `sensor.at0010XXXXXXX`).
3. Kopiere die genaue Entity-ID – sie wird in allen folgenden Schritten benötigt.

## 2. Sensoren anlegen

1. Erstelle eine neue Datei `/config/sensors.yaml` (oder verwende eine bestehende)
2. Füge folgenden Inhalt ein und ersetze `<DEIN_SENSOR>` durch deine Entity-ID aus Schritt 1:

```yaml
- platform: statistics
  name: "Wochenverbrauch Summe"
  entity_id: <DEIN_SENSOR>
  state_characteristic: change
  max_age:
      days: 7
  precision: 0
```

**WICHTIG:**

-   Kein `sensor:` am Anfang! Die Datei sollte eine Liste sein.
-   `state_characteristic: change` berechnet die Differenz zwischen jetzt und vor 7 Tagen (Wochen-Verbrauch)

## 3. Datei in configuration.yaml einbinden

Füge in deiner `/config/configuration.yaml` hinzu:

```yaml
sensor: !include sensors.yaml
```

Falls du bereits einen `sensor:` Abschnitt hast, entferne ihn und verwende stattdessen `!include`.

## 4. Home Assistant neu starten

Nach dem Speichern → _Einstellungen_ → _System_ → _Neustart_, damit der Statistik-Sensor `sensor.wochenverbrauch_summe` erstellt wird.

## 5. Lovelace-Karte hinzufügen

Füge im Dashboard eine „Manual Card“ mit folgendem YAML ein und ersetze `<DEIN_SENSOR>` erneut:

```yaml
type: custom:mini-graph-card
name: Wochenübersicht - Täglicher Stromverbrauch
icon: mdi:chart-bar
entities:
    - entity: sensor.wochenverbrauch_summe
      name: Wochen-Summe
      show_graph: false
      show_state: true
      show_legend: false
    - entity: <DEIN_SENSOR>
      name: Täglicher Verbrauch
      aggregate_func: diff
      show_state: false
      show_graph: true
      show_legend: false
show:
    graph: bar
    fill: true
    points: hover
    labels: hover
    legend: false
    state: true
    name: false
    icon: true
hours_to_show: 168
points_per_hour: 0.142857
group_by: date
aggregate_func: diff
bar_spacing: 2
height: 200
font_size: 100
decimals: 0
unit: "kWh"
align_state: center
```

-   **Oben in der Mitte**: Zeigt die Wochen-Summe (Verbrauch der letzten 7 Tage)
-   **Balken**: Jeder Balken zeigt den täglichen Verbrauch (Differenz zwischen Tagesanfang und Tagesende)
-   **Beim Hover**: Siehst du den genauen Tageswert

## 6. Optional

-   Wenn du weitere Wochenübersichten brauchst, dupliziere einfach Sensor + Karte mit den jeweiligen Entity-IDs.
-   Farben/Schriftgrößen kannst du in der Card nach Belieben anpassen.

Fertig! Damit ist alles aufgeräumt und nachvollziehbar – keine Legacy-Dateien mehr notwendig.
