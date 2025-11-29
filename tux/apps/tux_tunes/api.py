"""
Tux Tunes - Radio Browser API Client

Interfaces with radio-browser.info to search and discover internet radio stations.
API Documentation: https://docs.radio-browser.info/

Copyright (c) 2025 Christopher Dorrell. All Rights Reserved.
"""

import json
import urllib.request
import urllib.parse
import random
import socket
from dataclasses import dataclass
from typing import Optional


def get_api_servers() -> list[str]:
    """Get list of available API servers via DNS lookup."""
    try:
        # Query DNS for available servers
        ips = socket.getaddrinfo('all.api.radio-browser.info', 443, socket.AF_INET, socket.SOCK_STREAM)
        hosts = set()
        for ip in ips:
            try:
                # Reverse DNS to get hostname
                hostname = socket.gethostbyaddr(ip[4][0])[0]
                hosts.add(hostname)
            except:
                pass
        if hosts:
            print(f"Found API servers via DNS: {hosts}")
            return list(hosts)
    except Exception as e:
        print(f"DNS lookup failed: {e}")
    
    # Fallback to known servers
    return [
        "de1.api.radio-browser.info",
        "de2.api.radio-browser.info",
        "fi1.api.radio-browser.info",
        "nl1.api.radio-browser.info",
    ]


@dataclass
class Station:
    """Represents a radio station."""
    uuid: str
    name: str
    url: str
    url_resolved: str
    homepage: str
    favicon: str
    country: str
    countrycode: str
    state: str
    language: str
    tags: list[str]
    codec: str
    bitrate: int
    votes: int
    clickcount: int
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Station':
        """Create Station from API response dict."""
        return cls(
            uuid=data.get('stationuuid', ''),
            name=data.get('name', 'Unknown Station'),
            url=data.get('url', ''),
            url_resolved=data.get('url_resolved', data.get('url', '')),
            homepage=data.get('homepage', ''),
            favicon=data.get('favicon', ''),
            country=data.get('country', ''),
            countrycode=data.get('countrycode', ''),
            state=data.get('state', ''),
            language=data.get('language', ''),
            tags=[t.strip() for t in data.get('tags', '').split(',') if t.strip()],
            codec=data.get('codec', ''),
            bitrate=data.get('bitrate', 0),
            votes=data.get('votes', 0),
            clickcount=data.get('clickcount', 0),
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'stationuuid': self.uuid,
            'name': self.name,
            'url': self.url,
            'url_resolved': self.url_resolved,
            'homepage': self.homepage,
            'favicon': self.favicon,
            'country': self.country,
            'countrycode': self.countrycode,
            'state': self.state,
            'language': self.language,
            'tags': ','.join(self.tags),
            'codec': self.codec,
            'bitrate': self.bitrate,
            'votes': self.votes,
            'clickcount': self.clickcount,
        }


class RadioBrowserAPI:
    """Client for the radio-browser.info API."""
    
    def __init__(self):
        self.servers = get_api_servers()
        random.shuffle(self.servers)
        self.server_index = 0
        self.user_agent = "TuxTunes/1.0"
    
    @property
    def current_server(self) -> str:
        """Get current server hostname."""
        return self.servers[self.server_index % len(self.servers)]
    
    @property
    def base_url(self) -> str:
        """Get current server base URL."""
        return f"https://{self.current_server}/json"
    
    def _try_next_server(self):
        """Try the next server in the list."""
        self.server_index += 1
        print(f"Switching to server: {self.current_server}")
    
    def _request(self, endpoint: str, params: Optional[dict] = None) -> list[dict]:
        """Make API request and return JSON response."""
        # Try each server until one works
        for attempt in range(len(self.servers)):
            url = f"{self.base_url}/{endpoint}"
            
            if params:
                url += "?" + urllib.parse.urlencode(params)
            
            print(f"API Request: {url}")
            
            req = urllib.request.Request(url)
            req.add_header('User-Agent', self.user_agent)
            req.add_header('Accept', 'application/json')
            
            try:
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    print(f"API returned {len(data) if isinstance(data, list) else 'non-list'} results")
                    return data if isinstance(data, list) else []
            except Exception as e:
                print(f"API request failed on {self.current_server}: {e}")
                self._try_next_server()
        
        print("All API servers failed")
        return []
    
    def search(self, query: str, limit: int = 50) -> list[Station]:
        """Search for stations by name."""
        data = self._request('stations/search', {
            'name': query,
            'limit': limit,
            'order': 'clickcount',
            'reverse': 'true',
            'hidebroken': 'true',
        })
        return [Station.from_dict(s) for s in data]
    
    def search_by_tag(self, tag: str, limit: int = 50) -> list[Station]:
        """Search stations by tag/genre."""
        # URL path style: /stations/bytag/rock
        data = self._request(f'stations/bytag/{urllib.parse.quote(tag)}', {
            'limit': limit,
            'order': 'clickcount',
            'reverse': 'true',
            'hidebroken': 'true',
        })
        return [Station.from_dict(s) for s in data]
    
    def search_by_country(self, country: str, limit: int = 50) -> list[Station]:
        """Search stations by country."""
        data = self._request(f'stations/bycountry/{urllib.parse.quote(country)}', {
            'limit': limit,
            'order': 'clickcount',
            'reverse': 'true',
            'hidebroken': 'true',
        })
        return [Station.from_dict(s) for s in data]
    
    def get_popular(self, limit: int = 50) -> list[Station]:
        """Get most clicked stations."""
        data = self._request('stations/topclick', {
            'limit': limit,
            'hidebroken': 'true',
        })
        return [Station.from_dict(s) for s in data]
    
    def get_trending(self, limit: int = 50) -> list[Station]:
        """Get stations with recent clicks."""
        data = self._request('stations/lastclick', {
            'limit': limit,
            'hidebroken': 'true',
        })
        return [Station.from_dict(s) for s in data]
    
    def get_top_voted(self, limit: int = 50) -> list[Station]:
        """Get most voted stations."""
        data = self._request('stations/topvote', {
            'limit': limit,
            'hidebroken': 'true',
        })
        return [Station.from_dict(s) for s in data]
    
    def get_tags(self, limit: int = 100) -> list[dict]:
        """Get available tags/genres."""
        return self._request('tags', {
            'limit': limit,
            'order': 'stationcount',
            'reverse': 'true',
        })
    
    def get_countries(self, limit: int = 100) -> list[dict]:
        """Get countries with stations."""
        return self._request('countries', {
            'limit': limit,
            'order': 'stationcount', 
            'reverse': 'true',
        })
    
    def click(self, station_uuid: str):
        """Register a click/play for a station."""
        try:
            self._request(f'url/{station_uuid}')
        except:
            pass
    
    def vote(self, station_uuid: str):
        """Vote for a station."""
        try:
            self._request(f'vote/{station_uuid}')
        except:
            pass
