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
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime


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
            
            # Step 1: Get location (lat/lon)
            if location:
                # User specified location - use geocoding
                lat, lon, city, region = self._geocode_location(curl_path, location)
            else:
                # Auto-detect from IP using ip-api.com (more accurate than wttr.in)
                lat, lon, city, region = self._get_ip_location(curl_path)
            
            if lat is None or lon is None:
                print("[Weather] Could not determine location")
                return None
            
            location_str = f"{city}, {region}" if city else "Unknown Location"
            print(f"[Weather] Location: {location_str} ({lat}, {lon})")
            
            # Step 2: Get weather from Open-Meteo
            url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={lat}&longitude={lon}"
                f"&current=temperature_2m,relative_humidity_2m,weather_code"
                f"&daily=weather_code,temperature_2m_max,temperature_2m_min"
                f"&temperature_unit=fahrenheit"
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
            
            weather = Weather(
                temperature=f"{int(temp)}°F" if temp != '--' else "--°F",
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
    ]
    
    def __init__(self):
        self.cache = {}
        self.cache_time = {}
        self.cache_duration = 900  # 15 minutes
    
    def get_linux_news(self, max_items: int = 5) -> List[NewsItem]:
        """Fetch Linux news from RSS feeds."""
        cache_key = "linux"
        
        # Check cache
        if cache_key in self.cache and cache_key in self.cache_time:
            elapsed = (datetime.now() - self.cache_time[cache_key]).total_seconds()
            if elapsed < self.cache_duration:
                return self.cache[cache_key][:max_items]
        
        items = []
        
        for source_name, feed_url in self.LINUX_FEEDS[:3]:  # Limit sources
            try:
                items.extend(self._fetch_rss(feed_url, source_name, max_per_feed=2))
            except Exception as e:
                print(f"RSS error ({source_name}): {e}")
                continue
        
        # Sort by recency (if we had timestamps) and limit
        items = items[:max_items]
        
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
        except:
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
        except:
            pass


class NewsCard(Gtk.Box):
    """News headlines card."""
    
    def __init__(self, title: str, icon: str = "📰"):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add_css_class("card")
        self.set_margin_start(4)
        self.set_margin_end(4)
        
        self.title = title
        self.icon = icon
        self._build_ui()
    
    def _build_ui(self):
        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.set_margin_start(8)
        header.set_margin_end(8)
        header.set_margin_top(8)
        header.set_margin_bottom(4)
        self.append(header)
        
        title_label = Gtk.Label(label=f"{self.icon} {self.title}")
        title_label.add_css_class("heading")
        title_label.set_xalign(0)
        header.append(title_label)
        
        # Headlines container
        self.headlines_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.append(self.headlines_box)
        
        # Loading state
        self.loading_label = Gtk.Label(label="Loading...")
        self.loading_label.add_css_class("dim-label")
        self.loading_label.set_margin_start(8)
        self.loading_label.set_margin_bottom(8)
        self.headlines_box.append(self.loading_label)
    
    def set_headlines(self, items: List[NewsItem]):
        """Update headlines."""
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
            subprocess.Popen(['xdg-open', url])
        except:
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
        self._build_popover()
        
        # Start data refresh after a short delay (don't block startup)
        GLib.timeout_add_seconds(2, self._initial_refresh)
        
        # Auto-refresh every 15 minutes
        GLib.timeout_add_seconds(900, self._scheduled_refresh)
    
    def _initial_refresh(self):
        """Initial refresh on startup."""
        self._do_refresh()
        return False  # Don't repeat
    
    def _scheduled_refresh(self):
        """Scheduled refresh every 15 minutes."""
        if self._error_count < self._max_errors:
            self._do_refresh()
        return True  # Keep timer running
    
    def _do_refresh(self):
        """Actually perform the refresh (once)."""
        if self._refreshing:
            return  # Already refreshing, skip
        
        self._refreshing = True
        
        def do_refresh():
            try:
                # Fetch weather
                weather = self.weather_service.get_weather()
                if weather:
                    self._error_count = 0  # Reset on success
                    GLib.idle_add(self._update_weather, weather)
                else:
                    self._error_count += 1
                    GLib.idle_add(self._show_weather_error)
                
                # Fetch Linux news
                linux_news = self.news_service.get_linux_news(max_items=4)
                GLib.idle_add(self.linux_news_card.set_headlines, linux_news)
            except Exception as e:
                self._error_count += 1
                print(f"Widget refresh error: {e}")
            finally:
                self._refreshing = False
        
        thread = threading.Thread(target=do_refresh, daemon=True)
        thread.start()
    
    def _build_popover(self):
        """Build the widget panel popover."""
        self.popover = Gtk.Popover()
        self.popover.set_size_request(340, -1)
        self.set_popover(self.popover)
        
        # Main panel
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        panel.set_margin_top(8)
        panel.set_margin_bottom(8)
        panel.set_margin_start(4)
        panel.set_margin_end(4)
        
        # Weather card
        self.weather_card = WeatherCard()
        panel.append(self.weather_card)
        
        # Linux news card
        self.linux_news_card = NewsCard(title="Linux News", icon="🐧")
        panel.append(self.linux_news_card)
        
        # Settings button (placeholder for Phase 5)
        settings_btn = Gtk.Button()
        settings_btn.add_css_class("flat")
        settings_box = Gtk.Box(spacing=8)
        settings_box.append(Gtk.Label(label="⚙️"))
        settings_box.append(Gtk.Label(label="Widget Settings"))
        settings_btn.set_child(settings_box)
        settings_btn.set_halign(Gtk.Align.CENTER)
        settings_btn.set_margin_top(4)
        settings_btn.connect("clicked", self._on_settings_clicked)
        panel.append(settings_btn)
        
        self.popover.set_child(panel)
    
    def _update_weather(self, weather: Weather):
        """Update weather display."""
        # Update button
        self.weather_icon.set_label(weather.icon)
        self.temp_label.set_label(weather.temperature.replace("°F", "°"))
        
        # Update card
        self.weather_card.update(weather)
    
    def _show_weather_error(self):
        """Show weather error state."""
        self.weather_icon.set_label("⚠️")
        self.temp_label.set_label("--°")
        self.weather_card.show_error("Could not load weather")
    
    def _on_settings_clicked(self, button):
        """Open widget settings (placeholder)."""
        if hasattr(self.window, 'show_toast'):
            self.window.show_toast("Widget settings coming soon!")
        self.popover.popdown()
