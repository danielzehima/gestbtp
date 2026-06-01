"""Service météo basé sur Open-Meteo (gratuit, sans clé API).

- Géocodage de l'adresse du chantier -> latitude/longitude
- Prévisions sur 7 jours (température, code météo, précipitations, vent)

Les appels réseau ont un User-Agent navigateur et un timeout court ;
toute erreur renvoie None (jamais de crash).
"""
import json
import urllib.parse
import urllib.request
import urllib.error
from flask import current_app

_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
       '(KHTML, like Gecko) Chrome/124.0 Safari/537.36')

# Code météo WMO -> (libellé FR, icône Font Awesome, emoji)
WMO = {
    0: ("Ciel dégagé", "fa-sun", "☀️"),
    1: ("Plutôt dégagé", "fa-sun", "🌤️"),
    2: ("Partiellement nuageux", "fa-cloud-sun", "⛅"),
    3: ("Couvert", "fa-cloud", "☁️"),
    45: ("Brouillard", "fa-smog", "🌫️"),
    48: ("Brouillard givrant", "fa-smog", "🌫️"),
    51: ("Bruine légère", "fa-cloud-rain", "🌦️"),
    53: ("Bruine", "fa-cloud-rain", "🌦️"),
    55: ("Bruine dense", "fa-cloud-rain", "🌧️"),
    61: ("Pluie faible", "fa-cloud-rain", "🌧️"),
    63: ("Pluie", "fa-cloud-rain", "🌧️"),
    65: ("Forte pluie", "fa-cloud-showers-heavy", "🌧️"),
    71: ("Neige faible", "fa-snowflake", "🌨️"),
    73: ("Neige", "fa-snowflake", "❄️"),
    75: ("Forte neige", "fa-snowflake", "❄️"),
    80: ("Averses", "fa-cloud-showers-heavy", "🌦️"),
    81: ("Averses", "fa-cloud-showers-heavy", "🌧️"),
    82: ("Averses violentes", "fa-cloud-showers-heavy", "⛈️"),
    95: ("Orage", "fa-cloud-bolt", "⛈️"),
    96: ("Orage avec grêle", "fa-cloud-bolt", "⛈️"),
    99: ("Orage violent", "fa-cloud-bolt", "⛈️"),
}


def _fetch_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': _UA, 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=8) as resp:
        return json.loads(resp.read().decode('utf-8'))


def geocode(adresse):
    """Adresse -> (lat, lon, libellé) via Open-Meteo Geocoding. None si échec."""
    if not adresse or not adresse.strip():
        return None
    try:
        q = urllib.parse.quote(adresse.strip())
        url = (f"https://geocoding-api.open-meteo.com/v1/search?name={q}"
               f"&count=1&language=fr&format=json")
        data = _fetch_json(url)
        results = data.get('results') or []
        if not results:
            return None
        r = results[0]
        lieu = ', '.join(filter(None, [r.get('name'), r.get('admin1'), r.get('country')]))
        return (r['latitude'], r['longitude'], lieu)
    except Exception as e:
        current_app.logger.info(f"Géocodage météo échoué: {e}")
        return None


def get_weather(adresse):
    """Retourne un dict météo (actuel + 5 jours) pour l'adresse, ou None."""
    geo = geocode(adresse)
    if not geo:
        return None
    lat, lon, lieu = geo
    try:
        url = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
               f"&current=temperature_2m,weather_code,wind_speed_10m,precipitation"
               f"&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
               f"&timezone=auto&forecast_days=5")
        data = _fetch_json(url)
    except Exception as e:
        current_app.logger.info(f"Prévisions météo échouées: {e}")
        return None

    cur = data.get('current', {})
    code = cur.get('weather_code', 0)
    libelle, icone, emoji = WMO.get(code, ("—", "fa-cloud", "🌡️"))

    daily = data.get('daily', {})
    jours = []
    from datetime import datetime
    for i, d in enumerate(daily.get('time', [])):
        c = daily['weather_code'][i]
        lib, ic, em = WMO.get(c, ("—", "fa-cloud", "🌡️"))
        try:
            label = datetime.fromisoformat(d).strftime('%a %d/%m')
        except Exception:
            label = d
        jours.append({
            'date': label,
            'emoji': em, 'libelle': lib,
            'tmax': round(daily['temperature_2m_max'][i]),
            'tmin': round(daily['temperature_2m_min'][i]),
            'pluie': daily['precipitation_probability_max'][i],
        })

    return {
        'lieu': lieu,
        'actuel': {
            'temp': round(cur.get('temperature_2m', 0)),
            'libelle': libelle, 'icone': icone, 'emoji': emoji,
            'vent': round(cur.get('wind_speed_10m', 0)),
            'precip': cur.get('precipitation', 0),
        },
        'jours': jours,
    }
