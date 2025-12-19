"""
Weather Widget - Windows 11 style widget panel for Tux Assistant

A clean, privacy-respecting widget panel showing:
- Current weather + forecast
- Local news (RSS, no trackers)
- Linux news (RSS, no trackers)

Copyright (c) 2025 Christopher Dorrell. Licensed under GPL-3.0.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib, Gio
import subprocess
import threading
import urllib.request
import urllib.parse
import json
import re
import os
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime


# Config file for widget settings
WIDGET_CONFIG_DIR = os.path.expanduser("~/.config/tux-assistant")
WIDGET_CONFIG_FILE = os.path.join(WIDGET_CONFIG_DIR, "widget.conf")


def load_widget_config() -> dict:
    """Load widget configuration from file."""
    defaults = {
        "temp_unit": "fahrenheit",  # or "celsius"
        "location": "",  # Empty = auto-detect
        "headlines_count": 4,
        "refresh_interval": 15,  # minutes
        "enabled_sources": ["Phoronix", "OMG! Ubuntu", "9to5Linux", "It's FOSS", 
                           "GamingOnLinux", "FOSS Force", "Brutalist Report"],
    }
    
    try:
        os.makedirs(WIDGET_CONFIG_DIR, exist_ok=True)
        if os.path.exists(WIDGET_CONFIG_FILE):
            with open(WIDGET_CONFIG_FILE, 'r') as f:
                saved = json.load(f)
                defaults.update(saved)
    except Exception as e:
        print(f"[Widget] Config load error: {e}")
    
    return defaults


def save_widget_config(config: dict):
    """Save widget configuration to file."""
    try:
        os.makedirs(WIDGET_CONFIG_DIR, exist_ok=True)
        with open(WIDGET_CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"[Widget] Config save error: {e}")


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Weather:
    """Weather data."""
    temperature: str
    condition: str
    icon: str
    location: str = ""
    high: str = ""
    low: str = ""
    humidity: str = ""
    forecast: List[dict] = None  # [{day, icon, temp}, ...]


@dataclass
class NewsItem:
    """A news headline."""
    title: str
    source: str
    url: str
    time_ago: str = ""


# =============================================================================
# Weather Service (Open-Meteo - free, no API key, accurate geolocation)
# =============================================================================

class WeatherService:
    """Fetch weather data from Open-Meteo with ip-api.com geolocation."""
    
    def __init__(self):
        self.cache = None
        self.cache_time = None
        self.cache_duration = 1800  # 30 minutes
    
    def get_weather(self, location: str = "") -> Optional[Weather]:
        """Get current weather using Open-Meteo."""
        try:
            # Load config for settings
            config = load_widget_config()
            temp_unit = config.get("temp_unit", "fahrenheit")
            config_location = config.get("location", "")
            
            # Check cache
            if self.cache and self.cache_time:
                elapsed = (datetime.now() - self.cache_time).total_seconds()
                if elapsed < self.cache_duration:
                    return self.cache
            
            import shutil
            curl_path = shutil.which('curl')
            if not curl_path:
                print("[Weather] curl not found!")
                return None
            
            # Step 1: Get location (lat/lon) - config location takes priority
            use_location = config_location or location
            if use_location:
                # User specified location - use geocoding
                lat, lon, city, region = self._geocode_location(curl_path, use_location)
            else:
                # Auto-detect from IP using ip-api.com (more accurate than wttr.in)
                lat, lon, city, region = self._get_ip_location(curl_path)
            
            if lat is None or lon is None:
                print("[Weather] Could not determine location")
                return None
            
            location_str = f"{city}, {region}" if city else "Unknown Location"
            print(f"[Weather] Location: {location_str} ({lat}, {lon})")
            
            # Step 2: Get weather from Open-Meteo (respect temp unit setting)
            url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={lat}&longitude={lon}"
                f"&current=temperature_2m,relative_humidity_2m,weather_code"
                f"&daily=weather_code,temperature_2m_max,temperature_2m_min"
                f"&temperature_unit={temp_unit}"
                f"&timezone=auto"
                f"&forecast_days=3"
            )
            
            result = subprocess.run(
                [curl_path, '-s', '-m', '10', url],
                capture_output=True, text=True, timeout=15
            )
            
            if result.returncode != 0 or not result.stdout.strip():
                print(f"[Weather] Open-Meteo request failed")
                return None
            
            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError as e:
                print(f"[Weather] JSON parse error: {e}")
                return None
            
            current = data.get('current', {})
            daily = data.get('daily', {})
            
            # Get current conditions
            temp = current.get('temperature_2m', '--')
            humidity = current.get('relative_humidity_2m', '--')
            weather_code = current.get('weather_code', 0)
            
            # Build forecast
            forecast = []
            dates = daily.get('time', [])
            codes = daily.get('weather_code', [])
            highs = daily.get('temperature_2m_max', [])
            lows = daily.get('temperature_2m_min', [])
            
            day_names = ['Today', 'Tomorrow']
            for i in range(min(3, len(dates))):
                day_name = day_names[i] if i < len(day_names) else datetime.strptime(
                    dates[i], '%Y-%m-%d'
                ).strftime('%a')
                
                forecast.append({
                    'day': day_name,
                    'icon': self._code_to_icon(codes[i] if i < len(codes) else 0),
                    'high': f"{int(highs[i])}°" if i < len(highs) else "--°",
                    'low': f"{int(lows[i])}°" if i < len(lows) else "--°"
                })
            
            # Use correct temperature unit symbol
            unit_symbol = "°F" if temp_unit == "fahrenheit" else "°C"
            
            weather = Weather(
                temperature=f"{int(temp)}{unit_symbol}" if temp != '--' else f"--{unit_symbol}",
                condition=self._code_to_condition(weather_code),
                icon=self._code_to_icon(weather_code),
                location=location_str,
                high=forecast[0]['high'] if forecast else "--°",
                low=forecast[0]['low'] if forecast else "--°",
                humidity=f"{humidity}%",
                forecast=forecast
            )
            
            # Cache it
            self.cache = weather
            self.cache_time = datetime.now()
            
            print(f"[Weather] Success: {weather.temperature} {weather.condition}")
            return weather
            
        except Exception as e:
            print(f"Weather fetch error: {e}")
            return None
    
    def _get_ip_location(self, curl_path: str) -> tuple:
        """Get lat/lon from IP address using ip-api.com (accurate geolocation)."""
        try:
            result = subprocess.run(
                [curl_path, '-s', '-m', '5', 'http://ip-api.com/json/?fields=lat,lon,city,regionName'],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
                print(f"[Weather] IP location: {data}")
                return (
                    data.get('lat'),
                    data.get('lon'),
                    data.get('city', ''),
                    data.get('regionName', '')
                )
        except Exception as e:
            print(f"[Weather] IP geolocation failed: {e}")
        
        return (None, None, '', '')
    
    def _geocode_location(self, curl_path: str, location: str) -> tuple:
        """Convert location name to lat/lon using Open-Meteo geocoding."""
        try:
            encoded = urllib.parse.quote(location)
            url = f"https://geocoding-api.open-meteo.com/v1/search?name={encoded}&count=1"
            
            result = subprocess.run(
                [curl_path, '-s', '-m', '5', url],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
                results = data.get('results', [])
                if results:
                    r = results[0]
                    return (
                        r.get('latitude'),
                        r.get('longitude'),
                        r.get('name', ''),
                        r.get('admin1', '')  # State/region
                    )
        except Exception as e:
            print(f"[Weather] Geocoding failed: {e}")
        
        return (None, None, '', '')
    
    def _code_to_icon(self, code: int) -> str:
        """Convert WMO weather code to emoji icon."""
        code = int(code) if code else 0
        if code == 0:
            return '☀️'   # Clear sky
        elif code in [1, 2, 3]:
            return '⛅'   # Partly cloudy
        elif code in [45, 48]:
            return '🌫️'  # Fog
        elif code in [51, 53, 55, 56, 57]:
            return '🌧️'  # Drizzle
        elif code in [61, 63, 65, 66, 67]:
            return '🌧️'  # Rain
        elif code in [71, 73, 75, 77]:
            return '❄️'   # Snow
        elif code in [80, 81, 82]:
            return '🌧️'  # Rain showers
        elif code in [85, 86]:
            return '🌨️'  # Snow showers
        elif code in [95, 96, 99]:
            return '⛈️'   # Thunderstorm
        else:
            return '🌡️'
    
    def _code_to_condition(self, code: int) -> str:
        """Convert WMO weather code to condition text."""
        code = int(code) if code else 0
        conditions = {
            0: "Clear",
            1: "Mostly Clear",
            2: "Partly Cloudy",
            3: "Overcast",
            45: "Foggy",
            48: "Icy Fog",
            51: "Light Drizzle",
            53: "Drizzle",
            55: "Heavy Drizzle",
            56: "Freezing Drizzle",
            57: "Heavy Freezing Drizzle",
            61: "Light Rain",
            63: "Rain",
            65: "Heavy Rain",
            66: "Freezing Rain",
            67: "Heavy Freezing Rain",
            71: "Light Snow",
            73: "Snow",
            75: "Heavy Snow",
            77: "Snow Grains",
            80: "Light Showers",
            81: "Showers",
            82: "Heavy Showers",
            85: "Light Snow Showers",
            86: "Heavy Snow Showers",
            95: "Thunderstorm",
            96: "Thunderstorm with Hail",
            99: "Heavy Thunderstorm",
        }
        return conditions.get(code, "Unknown")


# =============================================================================
# News Service (RSS - clean, no tracking)
# =============================================================================

class NewsService:
    """Fetch news from clean RSS feeds."""
    
    LINUX_FEEDS = [
        ("Phoronix", "https://www.phoronix.com/rss.php"),
        ("OMG! Ubuntu", "https://www.omgubuntu.co.uk/feed"),
        ("9to5Linux", "https://9to5linux.com/feed"),
        ("It's FOSS", "https://itsfoss.com/feed"),
        ("GamingOnLinux", "https://www.gamingonlinux.com/article_rss.php"),
        ("FOSS Force", "https://fossforce.com/feed/"),
        ("Brutalist Report", "https://brutalist.report/feed/tech.rss"),
    ]
    
    def __init__(self):
        self.cache = {}
        self.cache_time = {}
        self.cache_duration = 900  # 15 minutes
    
    def get_linux_news(self, max_items: int = 5) -> List[NewsItem]:
        """Fetch Linux news from RSS feeds."""
        # Load config for enabled sources
        config = load_widget_config()
        enabled_sources = config.get("enabled_sources", [s[0] for s in self.LINUX_FEEDS])
        headlines_count = config.get("headlines_count", max_items)
        
        cache_key = "linux"
        
        # Check cache
        if cache_key in self.cache and cache_key in self.cache_time:
            elapsed = (datetime.now() - self.cache_time[cache_key]).total_seconds()
            if elapsed < self.cache_duration:
                return self.cache[cache_key][:headlines_count]
        
        items = []
        
        # Filter to only enabled sources
        active_feeds = [(name, url) for name, url in self.LINUX_FEEDS if name in enabled_sources]
        
        # Fetch from each enabled source (limit to 4 sources for performance)
        for source_name, feed_url in active_feeds[:4]:
            try:
                items.extend(self._fetch_rss(feed_url, source_name, max_per_feed=2))
            except Exception as e:
                print(f"RSS error ({source_name}): {e}")
                continue
        
        # Sort by recency (if we had timestamps) and limit
        items = items[:headlines_count]
        
        # Cache
        self.cache[cache_key] = items
        self.cache_time[cache_key] = datetime.now()
        
        return items
    
    def _fetch_rss(self, url: str, source: str, max_per_feed: int = 3) -> List[NewsItem]:
        """Fetch and parse RSS feed."""
        items = []
        
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'TuxAssistant/1.0'
            })
            
            with urllib.request.urlopen(req, timeout=5) as response:
                content = response.read().decode('utf-8', errors='ignore')
            
            # Simple regex RSS parsing (avoid XML dependency)
            # Find all <item> blocks
            item_pattern = re.compile(r'<item>(.*?)</item>', re.DOTALL)
            title_pattern = re.compile(r'<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>')
            link_pattern = re.compile(r'<link>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</link>')
            
            for match in item_pattern.finditer(content):
                item_content = match.group(1)
                
                title_match = title_pattern.search(item_content)
                link_match = link_pattern.search(item_content)
                
                if title_match and link_match:
                    title = title_match.group(1).strip()
                    url = self._strip_tracking(link_match.group(1).strip())
                    
                    # Clean up HTML entities
                    title = title.replace('&amp;', '&')
                    title = title.replace('&lt;', '<')
                    title = title.replace('&gt;', '>')
                    title = title.replace('&#8217;', "'")
                    title = title.replace('&#8211;', "–")
                    title = title.replace('&#8230;', "...")
                    
                    items.append(NewsItem(
                        title=title[:80] + "..." if len(title) > 80 else title,
                        source=source,
                        url=url,
                        time_ago=""  # Could parse pubDate if needed
                    ))
                    
                    if len(items) >= max_per_feed:
                        break
                        
        except Exception as e:
            print(f"RSS parse error: {e}")
        
        return items
    
    def _strip_tracking(self, url: str) -> str:
        """Remove UTM and other tracking parameters from URLs."""
        try:
            parsed = urllib.parse.urlparse(url)
            # Remove utm_* and other tracking params
            query_params = urllib.parse.parse_qs(parsed.query)
            clean_params = {k: v for k, v in query_params.items() 
                          if not k.startswith('utm_') and k not in ['ref', 'source']}
            clean_query = urllib.parse.urlencode(clean_params, doseq=True)
            return urllib.parse.urlunparse(parsed._replace(query=clean_query))
        except Exception:
            return url


# =============================================================================
# Widget Cards
# =============================================================================

class WeatherCard(Gtk.Box):
    """Weather display card."""
    
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.add_css_class("card")
        self.set_margin_start(4)
        self.set_margin_end(4)
        self._build_ui()
    
    def _build_ui(self):
        # Current conditions row
        current_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        current_box.set_margin_start(8)
        current_box.set_margin_end(8)
        current_box.set_margin_top(8)
        self.append(current_box)
        
        # Large temp + icon
        self.icon_label = Gtk.Label(label="🌡️")
        self.icon_label.add_css_class("title-1")
        current_box.append(self.icon_label)
        
        temp_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        current_box.append(temp_box)
        
        self.temp_label = Gtk.Label(label="--°F")
        self.temp_label.add_css_class("title-1")
        self.temp_label.set_xalign(0)
        temp_box.append(self.temp_label)
        
        self.condition_label = Gtk.Label(label="Loading...")
        self.condition_label.add_css_class("dim-label")
        self.condition_label.set_xalign(0)
        temp_box.append(self.condition_label)
        
        # Spacer
        current_box.append(Gtk.Box(hexpand=True))
        
        # High/Low
        hl_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        current_box.append(hl_box)
        
        self.high_label = Gtk.Label(label="H: --°")
        self.high_label.add_css_class("dim-label")
        self.high_label.set_xalign(1)
        hl_box.append(self.high_label)
        
        self.low_label = Gtk.Label(label="L: --°")
        self.low_label.add_css_class("dim-label")
        self.low_label.set_xalign(1)
        hl_box.append(self.low_label)
        
        # Location
        self.location_label = Gtk.Label(label="")
        self.location_label.add_css_class("dim-label")
        self.location_label.set_margin_start(8)
        self.location_label.set_xalign(0)
        self.append(self.location_label)
        
        # Forecast row
        self.forecast_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.forecast_box.set_homogeneous(True)
        self.forecast_box.set_margin_start(8)
        self.forecast_box.set_margin_end(8)
        self.forecast_box.set_margin_top(8)
        self.forecast_box.set_margin_bottom(8)
        self.append(self.forecast_box)
        
        # Source link
        source_btn = Gtk.Button(label="open-meteo.com ↗")
        source_btn.add_css_class("flat")
        source_btn.add_css_class("dim-label")
        source_btn.set_halign(Gtk.Align.END)
        source_btn.set_margin_end(8)
        source_btn.set_margin_bottom(4)
        source_btn.connect("clicked", self._on_source_clicked)
        self.append(source_btn)
    
    def update(self, weather: Weather):
        """Update the card with weather data."""
        self.icon_label.set_label(weather.icon)
        self.temp_label.set_label(weather.temperature)
        self.condition_label.set_label(weather.condition)
        self.high_label.set_label(f"H: {weather.high}")
        self.low_label.set_label(f"L: {weather.low}")
        self.location_label.set_label(weather.location)
        
        # Update forecast
        while child := self.forecast_box.get_first_child():
            self.forecast_box.remove(child)
        
        if weather.forecast:
            for day in weather.forecast:
                day_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
                day_box.set_halign(Gtk.Align.CENTER)
                
                day_label = Gtk.Label(label=day['day'])
                day_label.add_css_class("dim-label")
                day_box.append(day_label)
                
                icon_label = Gtk.Label(label=day['icon'])
                day_box.append(icon_label)
                
                temp_label = Gtk.Label(label=day['high'])
                temp_label.add_css_class("dim-label")
                day_box.append(temp_label)
                
                self.forecast_box.append(day_box)
    
    def show_error(self, message: str):
        """Show error state."""
        self.icon_label.set_label("⚠️")
        self.temp_label.set_label("--")
        self.condition_label.set_label(message)
    
    def _on_source_clicked(self, button):
        """Open Open-Meteo in browser."""
        try:
            subprocess.Popen(['xdg-open', 'https://open-meteo.com'])
        except Exception:
            pass


class NewsCard(Gtk.Box):
    """News headlines card with search."""
    
    def __init__(self, title: str, icon: str = "📰", url_callback=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add_css_class("card")
        self.set_margin_start(4)
        self.set_margin_end(4)
        
        self.title = title
        self.icon = icon
        self._all_items = []  # Store all items for filtering
        self._url_callback = url_callback  # Callback to open URLs (e.g., in Tux Browser)
        self._build_ui()
    
    def _build_ui(self):
        # Header with title and search toggle
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.set_margin_start(8)
        header.set_margin_end(8)
        header.set_margin_top(8)
        header.set_margin_bottom(4)
        self.append(header)
        
        title_label = Gtk.Label(label=f"{self.icon} {self.title}")
        title_label.add_css_class("heading")
        title_label.set_xalign(0)
        title_label.set_hexpand(True)
        header.append(title_label)
        
        # Search toggle button
        self.search_btn = Gtk.ToggleButton()
        self.search_btn.set_icon_name("tux-system-search-symbolic")
        self.search_btn.add_css_class("flat")
        self.search_btn.add_css_class("circular")
        self.search_btn.set_tooltip_text("Search news")
        self.search_btn.connect("toggled", self._on_search_toggled)
        header.append(self.search_btn)
        
        # Search bar (hidden by default)
        self.search_revealer = Gtk.Revealer()
        self.search_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        self.append(self.search_revealer)
        
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        search_box.set_margin_start(8)
        search_box.set_margin_end(8)
        search_box.set_margin_bottom(8)
        self.search_revealer.set_child(search_box)
        
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Filter headlines...")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("search-changed", self._on_search_changed)
        search_box.append(self.search_entry)
        
        # Headlines container
        self.headlines_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.append(self.headlines_box)
        
        # Loading state
        self.loading_label = Gtk.Label(label="Loading...")
        self.loading_label.add_css_class("dim-label")
        self.loading_label.set_margin_start(8)
        self.loading_label.set_margin_bottom(8)
        self.headlines_box.append(self.loading_label)
    
    def _on_search_toggled(self, button):
        """Toggle search bar visibility."""
        self.search_revealer.set_reveal_child(button.get_active())
        if button.get_active():
            self.search_entry.grab_focus()
        else:
            self.search_entry.set_text("")
            self._filter_headlines("")
    
    def _on_search_changed(self, entry):
        """Filter headlines based on search text."""
        search_text = entry.get_text().lower()
        self._filter_headlines(search_text)
    
    def _filter_headlines(self, search_text: str):
        """Filter and display headlines matching search text."""
        if not search_text:
            self._display_items(self._all_items)
        else:
            filtered = [item for item in self._all_items 
                       if search_text in item.title.lower() or search_text in item.source.lower()]
            self._display_items(filtered)
    
    def set_headlines(self, items: List[NewsItem]):
        """Update headlines."""
        self._all_items = items or []
        self._display_items(self._all_items)
    
    def _display_items(self, items: List[NewsItem]):
        """Display the given items."""
        # Clear existing
        while child := self.headlines_box.get_first_child():
            self.headlines_box.remove(child)
        
        if not items:
            empty_label = Gtk.Label(label="No news available")
            empty_label.add_css_class("dim-label")
            empty_label.set_margin_start(8)
            empty_label.set_margin_bottom(8)
            self.headlines_box.append(empty_label)
            return
        
        for item in items:
            row = self._create_headline_row(item)
            self.headlines_box.append(row)
    
    def _create_headline_row(self, item: NewsItem) -> Gtk.Widget:
        """Create a headline row."""
        row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        row.set_margin_start(8)
        row.set_margin_end(8)
        row.set_margin_top(6)
        row.set_margin_bottom(6)
        
        # Title button (clickable)
        title_btn = Gtk.Button()
        title_btn.add_css_class("flat")
        title_btn.set_halign(Gtk.Align.START)
        
        title_label = Gtk.Label(label=item.title)
        title_label.set_wrap(True)
        title_label.set_wrap_mode(2)  # WORD_CHAR
        title_label.set_xalign(0)
        title_label.set_max_width_chars(40)
        title_btn.set_child(title_label)
        title_btn.connect("clicked", self._on_headline_clicked, item.url)
        row.append(title_btn)
        
        # Source
        source_label = Gtk.Label(label=f"{item.source}")
        source_label.add_css_class("dim-label")
        source_label.add_css_class("caption")
        source_label.set_xalign(0)
        row.append(source_label)
        
        return row
    
    def _on_headline_clicked(self, button, url: str):
        """Open headline in browser."""
        try:
            if self._url_callback:
                # Use callback (e.g., open in Tux Browser)
                self._url_callback(url)
            else:
                # Fallback to system default browser
                subprocess.Popen(['xdg-open', url])
        except Exception:
            pass


# =============================================================================
# Main Widget Button (appears in header bar)
# =============================================================================

class WeatherWidget(Gtk.MenuButton):
    """
    Weather widget button for the header bar.
    Shows current temp, expands to full widget panel on click.
    """
    
    def __init__(self, window):
        super().__init__()
        self.window = window
        
        # Services
        self.weather_service = WeatherService()
        self.news_service = NewsService()
        
        # Track refresh state to prevent spam
        self._refreshing = False
        self._error_count = 0
        self._max_errors = 3
        
        # Build button content (collapsed state)
        self.button_content = Gtk.Box(spacing=6)
        self.button_content.set_margin_start(4)
        self.button_content.set_margin_end(4)
        
        self.weather_icon = Gtk.Label(label="☀️")
        self.temp_label = Gtk.Label(label="--°")
        self.button_content.append(self.weather_icon)
        self.button_content.append(self.temp_label)
        self.set_child(self.button_content)
        
        self.set_tooltip_text("Weather & News")
        self.add_css_class("flat")
        
        # Build popover (expanded state)
        self.popover = Gtk.Popover()
        self.popover.set_size_request(340, -1)
        self.set_popover(self.popover)
        
        # Scrolled window to prevent popover from getting too tall
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_max_content_height(450)
        scroll.set_propagate_natural_height(True)
        
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        panel.set_margin_top(8)
        panel.set_margin_bottom(8)
        panel.set_margin_start(4)
        panel.set_margin_end(4)
        
        self.weather_card = WeatherCard()
        panel.append(self.weather_card)
        
        self.linux_news_card = NewsCard(
            title="Linux News", 
            icon="🐧",
            url_callback=self._open_url_in_browser
        )
        panel.append(self.linux_news_card)
        
        settings_btn = Gtk.Button()
        settings_btn.add_css_class("flat")
        settings_box = Gtk.Box(spacing=8)
        settings_box.append(Gtk.Label(label="⚙️"))
        settings_box.append(Gtk.Label(label="Widget Settings"))
        settings_btn.set_child(settings_box)
        settings_btn.set_halign(Gtk.Align.CENTER)
        settings_btn.connect("clicked", self._on_settings_clicked)
        panel.append(settings_btn)
        
        scroll.set_child(panel)
        self.popover.set_child(scroll)
        
        # Start data refresh after a short delay (don't block startup)
        GLib.timeout_add_seconds(2, self._do_refresh)
    
    def _open_url_in_browser(self, url: str):
        """Open URL in Tux Browser (new tab)."""
        try:
            # Ensure browser is initialized
            if hasattr(self.window, 'browser_panel') and self.window.browser_panel is None:
                if hasattr(self.window, '_build_global_browser_panel'):
                    self.window._build_global_browser_panel()
            
            if hasattr(self.window, '_browser_new_tab') and self.window.browser_panel:
                self.popover.popdown()
                if hasattr(self.window, '_show_browser_docked'):
                    self.window._show_browser_docked()
                self.window._browser_new_tab(url)
            else:
                subprocess.Popen(['xdg-open', url])
        except Exception as e:
            print(f"Error opening URL: {e}")
            # Fallback to system browser
            try:
                subprocess.Popen(['xdg-open', url])
            except Exception:
                pass
    
    def _on_settings_clicked(self, button):
        """Open widget settings dialog."""
        self.popover.popdown()
        dialog = WidgetSettingsDialog(self.window, self)
        dialog.present()
    
    def _do_refresh(self):
        """Perform the refresh."""
        if self._refreshing:
            return False
        self._refreshing = True
        
        def do_refresh():
            try:
                weather = self.weather_service.get_weather()
                if weather:
                    self._error_count = 0
                    GLib.idle_add(self.weather_icon.set_label, weather.icon)
                    GLib.idle_add(self.temp_label.set_label, weather.temperature.replace("°F", "°").replace("°C", "°"))
                    GLib.idle_add(self.weather_card.update, weather)
                else:
                    self._error_count += 1
                
                config = load_widget_config()
                headlines_count = config.get("headlines_count", 4)
                news = self.news_service.get_linux_news(max_items=headlines_count)
                GLib.idle_add(self.linux_news_card.set_headlines, news)
            except Exception as e:
                self._error_count += 1
                print(f"Widget refresh error: {e}")
            finally:
                self._refreshing = False
        
        thread = threading.Thread(target=do_refresh, daemon=True)
        thread.start()
        return False


# =============================================================================
# Widget Settings Dialog
# =============================================================================

class WidgetSettingsDialog(Adw.Dialog):
    """Settings dialog for weather widget."""
    
    ALL_SOURCES = [
        "Phoronix", "OMG! Ubuntu", "9to5Linux", "It's FOSS", 
        "GamingOnLinux", "FOSS Force", "Brutalist Report"
    ]
    
    def __init__(self, parent_window, widget):
        super().__init__()
        self.parent_window = parent_window
        self.widget = widget
        self.config = load_widget_config()
        
        self.set_title("Widget Settings")
        self.set_content_width(400)
        self.set_content_height(500)
        
        self._build_ui()
    
    def _build_ui(self):
        # Main toolbar view
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        # Header bar
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(True)
        toolbar_view.add_top_bar(header)
        
        # Scrolled content
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        toolbar_view.set_content(scroll)
        
        # Main content box
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.set_margin_top(16)
        content.set_margin_bottom(16)
        content.set_margin_start(16)
        content.set_margin_end(16)
        scroll.set_child(content)
        
        # === Weather Settings ===
        weather_group = Adw.PreferencesGroup()
        weather_group.set_title("Weather")
        weather_group.set_description("Configure weather display")
        content.append(weather_group)
        
        # Temperature unit
        temp_row = Adw.ComboRow()
        temp_row.set_title("Temperature Unit")
        temp_row.set_subtitle("Choose Fahrenheit or Celsius")
        temp_model = Gtk.StringList.new(["Fahrenheit (°F)", "Celsius (°C)"])
        temp_row.set_model(temp_model)
        temp_row.set_selected(0 if self.config.get("temp_unit") == "fahrenheit" else 1)
        temp_row.connect("notify::selected", self._on_temp_unit_changed)
        weather_group.add(temp_row)
        self.temp_row = temp_row
        
        # Location override
        location_row = Adw.EntryRow()
        location_row.set_title("Location")
        location_row.set_text(self.config.get("location", ""))
        location_row.set_show_apply_button(True)
        location_row.connect("apply", self._on_location_changed)
        weather_group.add(location_row)
        self.location_row = location_row
        
        # Auto-detect hint
        location_hint = Adw.ActionRow()
        location_hint.set_subtitle("Leave empty to auto-detect from IP address")
        weather_group.add(location_hint)
        
        # === News Settings ===
        news_group = Adw.PreferencesGroup()
        news_group.set_title("News")
        news_group.set_description("Configure news sources and display")
        content.append(news_group)
        
        # Headlines count
        headlines_row = Adw.SpinRow.new_with_range(1, 10, 1)
        headlines_row.set_title("Headlines to Show")
        headlines_row.set_subtitle("Number of news items displayed")
        headlines_row.set_value(self.config.get("headlines_count", 4))
        headlines_row.connect("notify::value", self._on_headlines_count_changed)
        news_group.add(headlines_row)
        self.headlines_row = headlines_row
        
        # === News Sources ===
        sources_group = Adw.PreferencesGroup()
        sources_group.set_title("News Sources")
        sources_group.set_description("Enable or disable news sources")
        content.append(sources_group)
        
        enabled_sources = self.config.get("enabled_sources", self.ALL_SOURCES)
        self.source_switches = {}
        
        for source_name in self.ALL_SOURCES:
            row = Adw.SwitchRow()
            row.set_title(source_name)
            row.set_active(source_name in enabled_sources)
            row.connect("notify::active", self._on_source_toggled, source_name)
            sources_group.add(row)
            self.source_switches[source_name] = row
        
        # === Refresh Settings ===
        refresh_group = Adw.PreferencesGroup()
        refresh_group.set_title("Refresh")
        refresh_group.set_description("Configure data refresh behavior")
        content.append(refresh_group)
        
        # Refresh interval
        refresh_row = Adw.ComboRow()
        refresh_row.set_title("Refresh Interval")
        refresh_row.set_subtitle("How often to update weather and news")
        refresh_model = Gtk.StringList.new(["5 minutes", "10 minutes", "15 minutes", "30 minutes", "1 hour"])
        refresh_row.set_model(refresh_model)
        
        interval = self.config.get("refresh_interval", 15)
        interval_map = {5: 0, 10: 1, 15: 2, 30: 3, 60: 4}
        refresh_row.set_selected(interval_map.get(interval, 2))
        refresh_row.connect("notify::selected", self._on_refresh_changed)
        refresh_group.add(refresh_row)
        self.refresh_row = refresh_row
        
        # Refresh now button
        refresh_btn_row = Adw.ActionRow()
        refresh_btn_row.set_title("Refresh Now")
        refresh_btn_row.set_subtitle("Update weather and news immediately")
        
        refresh_btn = Gtk.Button(label="Refresh")
        refresh_btn.add_css_class("suggested-action")
        refresh_btn.set_valign(Gtk.Align.CENTER)
        refresh_btn.connect("clicked", self._on_refresh_now)
        refresh_btn_row.add_suffix(refresh_btn)
        refresh_btn_row.set_activatable_widget(refresh_btn)
        refresh_group.add(refresh_btn_row)
    
    def _on_temp_unit_changed(self, row, param):
        """Handle temperature unit change."""
        self.config["temp_unit"] = "fahrenheit" if row.get_selected() == 0 else "celsius"
        save_widget_config(self.config)
        # Update weather service
        if hasattr(self.widget, 'weather_service'):
            self.widget.weather_service.cache = None  # Clear cache to refresh
    
    def _on_location_changed(self, row):
        """Handle location change."""
        self.config["location"] = row.get_text().strip()
        save_widget_config(self.config)
        # Clear weather cache to use new location
        if hasattr(self.widget, 'weather_service'):
            self.widget.weather_service.cache = None
    
    def _on_headlines_count_changed(self, row, param):
        """Handle headlines count change."""
        self.config["headlines_count"] = int(row.get_value())
        save_widget_config(self.config)
    
    def _on_source_toggled(self, row, param, source_name):
        """Handle source toggle."""
        enabled = self.config.get("enabled_sources", list(self.ALL_SOURCES))
        if row.get_active():
            if source_name not in enabled:
                enabled.append(source_name)
        else:
            if source_name in enabled:
                enabled.remove(source_name)
        self.config["enabled_sources"] = enabled
        save_widget_config(self.config)
        # Clear news cache
        if hasattr(self.widget, 'news_service'):
            self.widget.news_service.cache = {}
    
    def _on_refresh_changed(self, row, param):
        """Handle refresh interval change."""
        intervals = [5, 10, 15, 30, 60]
        self.config["refresh_interval"] = intervals[row.get_selected()]
        save_widget_config(self.config)
    
    def _on_refresh_now(self, button):
        """Trigger immediate refresh."""
        if hasattr(self.widget, '_do_refresh'):
            self.widget._do_refresh()
        if hasattr(self.parent_window, 'show_toast'):
            self.parent_window.show_toast("Refreshing weather and news...")
