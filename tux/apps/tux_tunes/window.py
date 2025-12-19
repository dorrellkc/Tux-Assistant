"""
Tux Tunes - Main Window

GTK4/Libadwaita user interface for the radio player.
Features: Search, Genre browsing, Custom stations, Favorites, Recents

Copyright (c) 2025 Christopher Dorrell. All Rights Reserved.
"""

import threading
import uuid as uuid_module
from typing import Optional

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib, Gdk, GdkPixbuf

from . import __version__, __app_name__
from .api import RadioBrowserAPI, Station
from .library import Library
from .player import Player, TrackInfo


class TuxTunesWindow(Adw.ApplicationWindow):
    """Main application window."""
    
    # Popular genres/tags for quick access
    POPULAR_GENRES = [
        ("rock", "Rock"),
        ("pop", "Pop"),
        ("jazz", "Jazz"),
        ("classical", "Classical"),
        ("electronic", "Electronic"),
        ("hip hop", "Hip Hop"),
        ("country", "Country"),
        ("blues", "Blues"),
        ("metal", "Metal"),
        ("alternative", "Alternative"),
        ("indie", "Indie"),
        ("r&b", "R&B / Soul"),
        ("reggae", "Reggae"),
        ("folk", "Folk"),
        ("latin", "Latin"),
        ("80s", "80s"),
        ("90s", "90s"),
        ("oldies", "Oldies"),
        ("news", "News"),
        ("talk", "Talk"),
        ("sports", "Sports"),
        ("ambient", "Ambient"),
        ("chill", "Chill / Lounge"),
        ("dance", "Dance"),
    ]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.set_title("Tux Tunes")
        
        # Set window icon - try custom first, fall back to generic
        self._set_window_icon()
        
        # Initialize components
        self.library = Library()
        self.api = RadioBrowserAPI()
        self.player = Player(self.library)
        
        # Load window size
        width = self.library.get_config('window_width', 950)
        height = self.library.get_config('window_height', 750)
        self.set_default_size(width, height)
        
        if self.library.get_config('window_maximized', False):
            self.maximize()
        
        # Connect window size saving
        self.connect("notify::default-width", self._on_size_changed)
        self.connect("notify::default-height", self._on_size_changed)
        self.connect("notify::maximized", self._on_state_changed)
        
        # Connect player callbacks
        self.player.on_state_changed = self._on_player_state_changed
        self.player.on_metadata_changed = self._on_metadata_changed
        self.player.on_track_changed = self._on_track_changed
        self.player.on_recording_ready = self._on_recording_ready
        self.player.on_recording_state = self._on_recording_state
        self.player.on_error = self._on_player_error
        
        # Build UI
        self._build_ui()
        
        # Load initial content
        GLib.idle_add(self._load_initial_content)
    
    def _on_size_changed(self, widget, param):
        """Save window size on change."""
        if not self.is_maximized():
            self.library.set_config('window_width', self.get_width())
            self.library.set_config('window_height', self.get_height())
    
    def _on_state_changed(self, widget, param):
        """Save window state on change."""
        self.library.set_config('window_maximized', self.is_maximized())
    
    def _build_ui(self):
        """Build the main user interface."""
        # Main layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)
        
        # Header bar
        header = Adw.HeaderBar()
        
        # Search button
        search_btn = Gtk.ToggleButton()
        search_btn.set_icon_name("system-search-symbolic")
        search_btn.set_tooltip_text("Search stations (Ctrl+F)")
        search_btn.connect("toggled", self._on_search_toggled)
        self.search_button = search_btn
        header.pack_start(search_btn)
        
        # Add custom station button
        add_btn = Gtk.Button()
        add_btn.set_icon_name("list-add-symbolic")
        add_btn.set_tooltip_text("Add custom station")
        add_btn.connect("clicked", self._on_add_custom_station)
        header.pack_start(add_btn)
        
        # Menu button
        menu_btn = Gtk.MenuButton()
        menu_btn.set_icon_name("open-menu-symbolic")
        menu_btn.set_menu_model(self._create_menu())
        header.pack_end(menu_btn)
        
        main_box.append(header)
        
        # Search bar (hidden by default)
        self.search_bar = Gtk.SearchBar()
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        search_box.set_hexpand(True)
        
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search stations by name...")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("activate", self._on_search_activate)
        self.search_entry.connect("search-changed", self._on_search_changed)
        search_box.append(self.search_entry)
        
        self.search_bar.set_child(search_box)
        self.search_bar.connect_entry(self.search_entry)
        main_box.append(self.search_bar)
        
        # Toast overlay
        self.toast_overlay = Adw.ToastOverlay()
        main_box.append(self.toast_overlay)
        self.toast_overlay.set_vexpand(True)
        
        # Content box
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.toast_overlay.set_child(content_box)
        
        # Now Playing bar (at top when playing)
        self.now_playing_bar = self._create_now_playing_bar()
        self.now_playing_bar.set_visible(False)
        content_box.append(self.now_playing_bar)
        
        # Navigation tabs
        self.view_switcher = Adw.ViewSwitcher()
        self.view_switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)
        
        # View stack
        self.view_stack = Adw.ViewStack()
        self.view_switcher.set_stack(self.view_stack)
        content_box.append(self.view_switcher)
        
        # Create views
        self._create_favorites_view()
        self._create_browse_view()  # Browse with genres
        self._create_search_view()  # Search results
        self._create_recents_view()
        
        content_box.append(self.view_stack)
        
        # Bottom player controls
        self.player_controls = self._create_player_controls()
        content_box.append(self.player_controls)
        
        # Keyboard shortcuts
        self._setup_shortcuts()
    
    def _setup_shortcuts(self):
        """Set up keyboard shortcuts."""
        controller = Gtk.ShortcutController()
        controller.set_scope(Gtk.ShortcutScope.MANAGED)
        
        # Ctrl+F for search
        controller.add_shortcut(Gtk.Shortcut.new(
            Gtk.ShortcutTrigger.parse_string("<Control>f"),
            Gtk.CallbackAction.new(lambda *a: self._toggle_search())
        ))
        
        # Space for play/pause
        controller.add_shortcut(Gtk.Shortcut.new(
            Gtk.ShortcutTrigger.parse_string("space"),
            Gtk.CallbackAction.new(lambda *a: self._on_play_pause(None))
        ))
        
        self.add_controller(controller)
    
    def _toggle_search(self):
        """Toggle search bar."""
        self.search_button.set_active(not self.search_button.get_active())
        return True
    
    def _create_menu(self) -> Gio.Menu:
        """Create application menu."""
        menu = Gio.Menu()
        menu.append("Add Custom Station", "app.add_station")
        menu.append("Preferences", "app.preferences")
        menu.append("Keyboard Shortcuts", "app.shortcuts")
        menu.append("About Tux Tunes", "app.about")
        return menu
    
    def _create_now_playing_bar(self) -> Gtk.Widget:
        """Create the now playing info bar."""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_start(16)
        box.set_margin_end(16)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.add_css_class("card")
        
        # Station icon placeholder
        icon = Gtk.Image.new_from_icon_name("audio-x-generic-symbolic")
        icon.set_pixel_size(48)
        box.append(icon)
        self.now_playing_icon = icon
        
        # Info labels
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info_box.set_hexpand(True)
        info_box.set_valign(Gtk.Align.CENTER)
        
        # Title row with recording indicator
        title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        self.now_playing_title = Gtk.Label(label="Not Playing")
        self.now_playing_title.set_halign(Gtk.Align.START)
        self.now_playing_title.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
        self.now_playing_title.add_css_class("heading")
        title_row.append(self.now_playing_title)
        
        # Recording indicator (hidden by default)
        self.recording_indicator = Gtk.Label(label="⏺ REC")
        self.recording_indicator.add_css_class("error")  # Red color
        self.recording_indicator.set_visible(False)
        title_row.append(self.recording_indicator)
        
        info_box.append(title_row)
        
        self.now_playing_station = Gtk.Label(label="")
        self.now_playing_station.set_halign(Gtk.Align.START)
        self.now_playing_station.set_ellipsize(3)
        self.now_playing_station.add_css_class("dim-label")
        info_box.append(self.now_playing_station)
        
        box.append(info_box)
        
        # Favorite button for current station
        fav_btn = Gtk.Button.new_from_icon_name("non-starred-symbolic")
        fav_btn.set_tooltip_text("Add to favorites")
        fav_btn.set_valign(Gtk.Align.CENTER)
        fav_btn.add_css_class("flat")
        fav_btn.connect("clicked", self._on_toggle_current_favorite)
        box.append(fav_btn)
        self.now_playing_fav_btn = fav_btn
        
        return box
    
    def _create_player_controls(self) -> Gtk.Widget:
        """Create bottom player control bar."""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_start(16)
        box.set_margin_end(16)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_halign(Gtk.Align.CENTER)
        
        # Play/Pause button
        self.play_button = Gtk.Button.new_from_icon_name("media-playback-start-symbolic")
        self.play_button.add_css_class("circular")
        self.play_button.add_css_class("suggested-action")
        self.play_button.set_tooltip_text("Play/Pause (Space)")
        self.play_button.connect("clicked", self._on_play_pause)
        self.play_button.set_sensitive(False)
        box.append(self.play_button)
        
        # Stop button
        stop_btn = Gtk.Button.new_from_icon_name("media-playback-stop-symbolic")
        stop_btn.add_css_class("circular")
        stop_btn.set_tooltip_text("Stop")
        stop_btn.connect("clicked", self._on_stop)
        box.append(stop_btn)
        
        # Volume control
        self.volume_button = Gtk.VolumeButton()
        self.volume_button.set_value(self.player.get_volume())
        self.volume_button.connect("value-changed", self._on_volume_changed)
        box.append(self.volume_button)
        
        return box
    
    def _create_favorites_view(self):
        """Create favorites view."""
        page = self._create_station_list_page("favorites")
        self.favorites_list = page['list_box']
        self.favorites_status = page['status']
        
        self.view_stack.add_titled_with_icon(
            page['widget'], "favorites", "Favorites", "starred-symbolic"
        )
    
    def _create_browse_view(self):
        """Create browse view with genre pills and popular stations."""
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        
        clamp = Adw.Clamp()
        clamp.set_maximum_size(900)
        clamp.set_margin_top(16)
        clamp.set_margin_bottom(16)
        clamp.set_margin_start(16)
        clamp.set_margin_end(16)
        scrolled.set_child(clamp)
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        clamp.set_child(content)
        
        # Genre section
        genre_group = Adw.PreferencesGroup()
        genre_group.set_title("Browse by Genre")
        genre_group.set_description("Tap a genre to see stations")
        content.append(genre_group)
        
        # Genre flow box (pills)
        genre_flow = Gtk.FlowBox()
        genre_flow.set_selection_mode(Gtk.SelectionMode.NONE)
        genre_flow.set_max_children_per_line(8)
        genre_flow.set_min_children_per_line(3)
        genre_flow.set_row_spacing(8)
        genre_flow.set_column_spacing(8)
        genre_flow.set_homogeneous(False)
        
        for tag, display_name in self.POPULAR_GENRES:
            btn = Gtk.Button(label=display_name)
            btn.add_css_class("pill")
            btn.connect("clicked", self._on_genre_clicked, tag, display_name)
            genre_flow.append(btn)
        
        genre_group.add(genre_flow)
        
        # Popular stations section
        popular_group = Adw.PreferencesGroup()
        popular_group.set_title("Popular Stations")
        popular_group.set_description("Most played stations worldwide")
        content.append(popular_group)
        
        # Popular list
        self.popular_list = Gtk.ListBox()
        self.popular_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.popular_list.add_css_class("boxed-list")
        popular_group.add(self.popular_list)
        
        # Loading indicator
        self.popular_spinner = Gtk.Spinner()
        self.popular_spinner.set_size_request(32, 32)
        self.popular_spinner.set_halign(Gtk.Align.CENTER)
        self.popular_spinner.set_margin_top(20)
        self.popular_spinner.set_margin_bottom(20)
        popular_group.add(self.popular_spinner)
        
        self.view_stack.add_titled_with_icon(
            scrolled, "browse", "Browse", "folder-music-symbolic"
        )
    
    def _create_search_view(self):
        """Create search results view with embedded search entry."""
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        
        clamp = Adw.Clamp()
        clamp.set_maximum_size(800)
        clamp.set_margin_top(16)
        clamp.set_margin_bottom(16)
        clamp.set_margin_start(16)
        clamp.set_margin_end(16)
        scrolled.set_child(clamp)
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        clamp.set_child(content)
        
        # Search entry at top of search view
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        search_box.set_margin_bottom(8)
        
        self.search_view_entry = Gtk.SearchEntry()
        self.search_view_entry.set_placeholder_text("Search stations by name...")
        self.search_view_entry.set_hexpand(True)
        self.search_view_entry.connect("activate", self._on_search_view_activate)
        self.search_view_entry.connect("search-changed", self._on_search_view_changed)
        search_box.append(self.search_view_entry)
        
        content.append(search_box)
        
        # Status page (shown when empty or loading)
        self.search_status = Adw.StatusPage()
        self.search_status.set_icon_name("system-search-symbolic")
        self.search_status.set_title("Search for Stations")
        self.search_status.set_description("Enter a station name above to search")
        content.append(self.search_status)
        
        # List box for stations
        self.search_list = Gtk.ListBox()
        self.search_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.search_list.add_css_class("boxed-list")
        self.search_list.set_visible(False)
        content.append(self.search_list)
        
        self.view_stack.add_titled_with_icon(
            scrolled, "search", "Search", "system-search-symbolic"
        )
    
    def _on_search_view_activate(self, entry):
        """Handle search activation from search view entry."""
        query = entry.get_text().strip()
        if query:
            self._cancel_pending_search()
            self._do_search(query)
    
    def _on_search_view_changed(self, entry):
        """Handle search text change from search view entry - debounced."""
        query = entry.get_text().strip()
        if len(query) >= 2:
            self._schedule_search(query)
        else:
            self._cancel_pending_search()
    
    def _schedule_search(self, query: str):
        """Schedule a search with debouncing (300ms delay)."""
        self._cancel_pending_search()
        self._pending_search_id = GLib.timeout_add(300, self._execute_scheduled_search, query)
    
    def _cancel_pending_search(self):
        """Cancel any pending search."""
        if hasattr(self, '_pending_search_id') and self._pending_search_id:
            GLib.source_remove(self._pending_search_id)
            self._pending_search_id = None
    
    def _execute_scheduled_search(self, query: str):
        """Execute the scheduled search."""
        self._pending_search_id = None
        self._do_search(query)
        return False  # Don't repeat
    
    def _create_recents_view(self):
        """Create recent stations view."""
        page = self._create_station_list_page("recents")
        self.recents_list = page['list_box']
        self.recents_status = page['status']
        
        self.view_stack.add_titled_with_icon(
            page['widget'], "recents", "Recent", "document-open-recent-symbolic"
        )
    
    def _create_station_list_page(self, page_id: str) -> dict:
        """Create a scrollable station list page."""
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        
        clamp = Adw.Clamp()
        clamp.set_maximum_size(800)
        clamp.set_margin_top(16)
        clamp.set_margin_bottom(16)
        clamp.set_margin_start(16)
        clamp.set_margin_end(16)
        scrolled.set_child(clamp)
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        clamp.set_child(content)
        
        # Status page (shown when empty or loading)
        status = Adw.StatusPage()
        status.set_icon_name("audio-x-generic-symbolic")
        status.set_title("No Stations")
        status.set_description("Add some stations to your favorites")
        content.append(status)
        
        # List box for stations
        list_box = Gtk.ListBox()
        list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        list_box.add_css_class("boxed-list")
        list_box.set_visible(False)
        content.append(list_box)
        
        return {
            'widget': scrolled,
            'list_box': list_box,
            'status': status,
            'content': content,
        }
    
    def _create_station_row(self, station: Station) -> Adw.ActionRow:
        """Create a row for a station."""
        row = Adw.ActionRow()
        
        # Escape markup characters in station name
        safe_name = (station.name
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))
        row.set_title(safe_name)
        
        subtitle_parts = []
        if station.country:
            subtitle_parts.append(station.country)
        if station.tags:
            # Escape tags too
            safe_tags = [t.replace("&", "&amp;") for t in station.tags[:3]]
            subtitle_parts.append(", ".join(safe_tags))
        if station.bitrate:
            subtitle_parts.append(f"{station.bitrate} kbps")
        
        row.set_subtitle(" • ".join(subtitle_parts) if subtitle_parts else "Internet Radio")
        row.set_activatable(True)
        
        # Store station reference
        row.station = station
        
        # Edit and Delete buttons (only for custom stations)
        if station.uuid.startswith("custom-"):
            edit_btn = Gtk.Button.new_from_icon_name("document-edit-symbolic")
            edit_btn.set_valign(Gtk.Align.CENTER)
            edit_btn.add_css_class("flat")
            edit_btn.set_tooltip_text("Edit station")
            edit_btn.connect("clicked", lambda b: self._on_edit_custom_station(station))
            row.add_suffix(edit_btn)
            
            delete_btn = Gtk.Button.new_from_icon_name("user-trash-symbolic")
            delete_btn.set_valign(Gtk.Align.CENTER)
            delete_btn.add_css_class("flat")
            delete_btn.set_tooltip_text("Delete station")
            delete_btn.connect("clicked", lambda b: self._on_delete_custom_station(station))
            row.add_suffix(delete_btn)
        
        # Play button
        play_btn = Gtk.Button.new_from_icon_name("media-playback-start-symbolic")
        play_btn.set_valign(Gtk.Align.CENTER)
        play_btn.add_css_class("flat")
        play_btn.set_tooltip_text("Play")
        play_btn.connect("clicked", lambda b: self._play_station(station))
        row.add_suffix(play_btn)
        
        # Favorite button (hide for custom stations - they use delete instead)
        if not station.uuid.startswith("custom-"):
            is_fav = self.library.is_favorite(station.uuid)
            fav_icon = "starred-symbolic" if is_fav else "non-starred-symbolic"
            fav_btn = Gtk.Button.new_from_icon_name(fav_icon)
            fav_btn.set_valign(Gtk.Align.CENTER)
            fav_btn.add_css_class("flat")
            fav_btn.set_tooltip_text("Remove from favorites" if is_fav else "Add to favorites")
            fav_btn.connect("clicked", lambda b: self._toggle_favorite(station, b))
            row.add_suffix(fav_btn)
        
        # Connect row activation to play
        row.connect("activated", lambda r: self._play_station(station))
        
        return row
    
    def _load_initial_content(self):
        """Load initial content after window is shown."""
        self._refresh_favorites()
        self._load_popular_stations()
        self._refresh_recents()
    
    def _refresh_favorites(self):
        """Refresh favorites list."""
        self._clear_list(self.favorites_list)
        
        favorites = self.library.get_favorites()
        
        if favorites:
            self.favorites_status.set_visible(False)
            self.favorites_list.set_visible(True)
            
            for station in favorites:
                row = self._create_station_row(station)
                self.favorites_list.append(row)
        else:
            self.favorites_status.set_visible(True)
            self.favorites_list.set_visible(False)
            self.favorites_status.set_title("No Favorites Yet")
            self.favorites_status.set_description(
                "Search for stations or browse by genre, then tap ⭐ to add favorites"
            )
    
    def _refresh_recents(self):
        """Refresh recents list."""
        self._clear_list(self.recents_list)
        
        recents = self.library.get_recents()
        
        if recents:
            self.recents_status.set_visible(False)
            self.recents_list.set_visible(True)
            
            for station in recents:
                row = self._create_station_row(station)
                self.recents_list.append(row)
        else:
            self.recents_status.set_visible(True)
            self.recents_list.set_visible(False)
            self.recents_status.set_title("No Recent Stations")
            self.recents_status.set_description("Stations you play will appear here")
    
    def _load_popular_stations(self):
        """Load popular stations in background."""
        self.popular_spinner.start()
        self.popular_spinner.set_visible(True)
        
        def fetch():
            stations = self.api.get_popular(limit=20)
            GLib.idle_add(self._populate_popular, stations)
        
        thread = threading.Thread(target=fetch, daemon=True)
        thread.start()
    
    def _populate_popular(self, stations: list[Station]):
        """Populate popular list with stations."""
        self.popular_spinner.stop()
        self.popular_spinner.set_visible(False)
        
        self._clear_list(self.popular_list)
        
        for station in stations:
            row = self._create_station_row(station)
            self.popular_list.append(row)
    
    def _clear_list(self, list_box: Gtk.ListBox):
        """Clear all rows from a list box."""
        while True:
            row = list_box.get_first_child()
            if row is None:
                break
            list_box.remove(row)
    
    def _on_search_toggled(self, button):
        """Handle search button toggle."""
        self.search_bar.set_search_mode(button.get_active())
        if button.get_active():
            self.search_entry.grab_focus()
            self.view_stack.set_visible_child_name("search")
    
    def _on_search_changed(self, entry):
        """Handle search text change - debounced live search."""
        query = entry.get_text().strip()
        if len(query) >= 2:
            self._schedule_search(query)
        else:
            self._cancel_pending_search()
    
    def _on_search_activate(self, entry):
        """Handle search activation (Enter key)."""
        query = entry.get_text().strip()
        if query:
            self._cancel_pending_search()
            self._do_search(query)
    
    def _do_search(self, query: str):
        """Perform search."""
        self.view_stack.set_visible_child_name("search")
        
        # Track this search to ignore stale results
        if not hasattr(self, '_search_id'):
            self._search_id = 0
        self._search_id += 1
        current_search_id = self._search_id
        
        # Show loading
        self.search_status.set_title("Searching...")
        self.search_status.set_description(f"Looking for '{query}'")
        self.search_status.set_visible(True)
        self.search_list.set_visible(False)
        
        def search():
            stations = self.api.search(query, limit=50)
            # Only update if this is still the current search
            GLib.idle_add(self._populate_search_results, stations, query, current_search_id)
        
        thread = threading.Thread(target=search, daemon=True)
        thread.start()
    
    def _populate_search_results(self, stations: list[Station], query: str, search_id: int = 0):
        """Populate search results."""
        # Ignore stale results from old searches
        if search_id != 0 and search_id != getattr(self, '_search_id', 0):
            return
        
        self._clear_list(self.search_list)
        
        if stations:
            self.search_status.set_visible(False)
            self.search_list.set_visible(True)
            
            for station in stations:
                row = self._create_station_row(station)
                self.search_list.append(row)
        else:
            self.search_status.set_visible(True)
            self.search_list.set_visible(False)
            self.search_status.set_title("No Results")
            self.search_status.set_description(f"No stations found for '{query}'")
    
    def _on_genre_clicked(self, button, tag: str, display_name: str):
        """Handle genre button click."""
        self.view_stack.set_visible_child_name("search")
        
        # Show loading
        self.search_status.set_title(f"Loading {display_name}...")
        self.search_status.set_description("Fetching stations")
        self.search_status.set_visible(True)
        self.search_list.set_visible(False)
        
        def search():
            stations = self.api.search_by_tag(tag, limit=50)
            GLib.idle_add(self._populate_genre_results, stations, display_name)
        
        thread = threading.Thread(target=search, daemon=True)
        thread.start()
    
    def _populate_genre_results(self, stations: list[Station], genre_name: str):
        """Populate genre results."""
        self._clear_list(self.search_list)
        
        if stations:
            self.search_status.set_visible(False)
            self.search_list.set_visible(True)
            
            for station in stations:
                row = self._create_station_row(station)
                self.search_list.append(row)
        else:
            self.search_status.set_visible(True)
            self.search_list.set_visible(False)
            self.search_status.set_title(f"No {genre_name} Stations")
            self.search_status.set_description("Try a different genre")
    
    def _on_add_custom_station(self, button):
        """Show dialog to add custom station."""
        dialog = AddStationDialog(self, on_add_callback=self._handle_custom_station_added)
        dialog.present(self)
    
    def _handle_custom_station_added(self, station):
        """Handle when a custom station is added."""
        if station:
            self.library.add_favorite(station)
            self._refresh_favorites()
            self._show_toast(f"Added '{station.name}' to favorites")
            self.view_stack.set_visible_child_name("favorites")
    
    def _on_edit_custom_station(self, station: Station):
        """Show dialog to edit a custom station."""
        dialog = EditStationDialog(self, station, on_save_callback=self._handle_custom_station_edited)
        dialog.present(self)
    
    def _handle_custom_station_edited(self, old_uuid: str, updated_station: Station):
        """Handle when a custom station is edited."""
        if updated_station:
            self.library.update_favorite(old_uuid, updated_station)
            self._refresh_favorites()
            self._show_toast(f"Updated '{updated_station.name}'")
    
    def _on_delete_custom_station(self, station: Station):
        """Show confirmation dialog to delete a custom station."""
        dialog = Adw.AlertDialog()
        dialog.set_heading(f"Delete '{station.name}'?")
        dialog.set_body("This custom station will be permanently removed.")
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("delete", "Delete")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        
        dialog.station = station
        dialog.connect("response", self._on_delete_station_response)
        dialog.present(self)
    
    def _on_delete_station_response(self, dialog, response):
        """Handle delete confirmation response."""
        if response == "delete":
            station = dialog.station
            self.library.remove_favorite(station.uuid)
            self._refresh_favorites()
            self._show_toast(f"Deleted '{station.name}'")
    
    def _play_station(self, station: Station):
        """Play a station."""
        self.player.play(station)
        self.play_button.set_sensitive(True)
        self.play_button.set_icon_name("media-playback-pause-symbolic")
        
        # Update now playing
        self.now_playing_bar.set_visible(True)
        self.now_playing_title.set_label("Connecting...")
        self.now_playing_station.set_label(station.name)
        
        # Update favorite button
        is_fav = self.library.is_favorite(station.uuid)
        self.now_playing_fav_btn.set_icon_name("starred-symbolic" if is_fav else "non-starred-symbolic")
        
        # Refresh recents
        self._refresh_recents()
    
    def _toggle_favorite(self, station: Station, button: Gtk.Button):
        """Toggle station favorite status."""
        if self.library.is_favorite(station.uuid):
            self.library.remove_favorite(station.uuid)
            button.set_icon_name("non-starred-symbolic")
            button.set_tooltip_text("Add to favorites")
            self._show_toast(f"Removed from favorites")
        else:
            self.library.add_favorite(station)
            button.set_icon_name("starred-symbolic")
            button.set_tooltip_text("Remove from favorites")
            self._show_toast(f"Added to favorites")
        
        self._refresh_favorites()
    
    def _on_toggle_current_favorite(self, button):
        """Toggle favorite status of currently playing station."""
        if self.player.current_station:
            station = self.player.current_station
            if self.library.is_favorite(station.uuid):
                self.library.remove_favorite(station.uuid)
                button.set_icon_name("non-starred-symbolic")
                self._show_toast("Removed from favorites")
            else:
                self.library.add_favorite(station)
                button.set_icon_name("starred-symbolic")
                self._show_toast("Added to favorites")
            
            self._refresh_favorites()
    
    def _on_play_pause(self, button):
        """Handle play/pause button."""
        if self.player.is_playing:
            self.player.pause()
            self.play_button.set_icon_name("media-playback-start-symbolic")
        else:
            self.player.resume()
            self.play_button.set_icon_name("media-playback-pause-symbolic")
    
    def _on_stop(self, button):
        """Handle stop button."""
        self.player.stop()
        self.play_button.set_icon_name("media-playback-start-symbolic")
        self.play_button.set_sensitive(False)
        self.now_playing_bar.set_visible(False)
        self.recording_indicator.set_visible(False)
    
    def _on_volume_changed(self, button, value):
        """Handle volume change."""
        self.player.set_volume(value)
    
    def _on_player_state_changed(self, state: str):
        """Handle player state change."""
        if state == "playing":
            self.play_button.set_icon_name("media-playback-pause-symbolic")
        elif state == "paused":
            self.play_button.set_icon_name("media-playback-start-symbolic")
    
    def _on_metadata_changed(self, title: str, artist: str):
        """Handle metadata change from stream."""
        if artist:
            self.now_playing_title.set_label(f"{artist} - {title}")
        else:
            self.now_playing_title.set_label(title)
    
    def _on_track_changed(self, track):
        """Handle track change (for recording UI)."""
        pass
    
    def _on_recording_state(self, is_recording: bool):
        """Handle recording state change - show/hide indicator."""
        self.recording_indicator.set_visible(is_recording)
    
    def _on_recording_ready(self, cached):
        """Handle when a recording is ready to be saved."""
        recording_mode = self.library.get_config('recording_mode', 'ask')
        
        if recording_mode == 'none':
            # Don't save, don't ask
            return
        elif recording_mode == 'auto':
            # Auto-save without asking
            self._save_recording(cached, notify=True)
        else:
            # 'ask' mode - check if we should prompt about auto-save first
            if not self.library.get_config('auto_save_prompted', False):
                self._show_auto_save_prompt(cached)
            else:
                self._show_save_recording_toast(cached)
    
    def _show_auto_save_prompt(self, cached):
        """Show first-time prompt asking about auto-save preference."""
        dialog = Adw.AlertDialog()
        dialog.set_heading("Save Recordings Automatically?")
        dialog.set_body(
            "A recording is ready to save. Would you like Tux Tunes to "
            "automatically save all recordings in the future?\n\n"
            "You can change this anytime in the menu."
        )
        dialog.add_response("no", "Ask Each Time")
        dialog.add_response("yes", "Auto-Save")
        dialog.set_response_appearance("yes", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("yes")
        dialog.set_close_response("no")
        
        # Store cached recording for after dialog
        dialog.cached_recording = cached
        dialog.connect("response", self._on_auto_save_prompt_response)
        dialog.present(self)
    
    def _on_auto_save_prompt_response(self, dialog, response):
        """Handle auto-save prompt response."""
        cached = dialog.cached_recording
        
        # Mark that we've prompted
        self.library.set_config('auto_save_prompted', True)
        
        if response == "yes":
            # Enable auto-save and save this recording
            self.library.set_config('recording_mode', 'auto')
            self._save_recording(cached, notify=True)
            self._show_toast("Auto-save enabled")
        else:
            # Keep ask mode, show the normal save toast
            self._show_save_recording_toast(cached)
    
    def _show_save_recording_toast(self, cached):
        """Show a toast asking if user wants to save the recording."""
        from .player import CachedRecording
        
        # Format duration
        duration = int(cached.track.duration)
        minutes = duration // 60
        seconds = duration % 60
        duration_str = f"{minutes}:{seconds:02d}"
        
        toast = Adw.Toast.new(f"Save '{cached.track.display_name}' ({duration_str})?")
        toast.set_timeout(15)  # 15 seconds to decide
        toast.set_button_label("Save")
        toast.connect("button-clicked", lambda t: self._save_recording(cached))
        self.toast_overlay.add_toast(toast)
    
    def _save_recording(self, cached, notify=False):
        """Save a cached recording."""
        filepath = self.player.save_cached_recording(cached)
        if filepath:
            filename = filepath.split('/')[-1]
            if notify:
                self._show_toast(f"Saved: {filename}", timeout=2)
        else:
            self._show_toast("Failed to save recording")
    
    def _on_player_error(self, message: str):
        """Handle player error."""
        self._show_toast(message)
        self.now_playing_bar.set_visible(False)
        self.play_button.set_icon_name("media-playback-start-symbolic")
        self.play_button.set_sensitive(False)
    
    def show_toast(self, message: str, timeout: int = 3):
        """Show a toast notification."""
        toast = Adw.Toast.new(message)
        toast.set_timeout(timeout)
        self.toast_overlay.add_toast(toast)
    
    def _show_toast(self, message: str, timeout: int = 3):
        """Show a toast notification (internal, for backwards compat)."""
        self.show_toast(message, timeout)
    
    def _set_window_icon(self):
        """Set the window icon."""
        import os
        
        # Try to load our custom icon from file
        icon_paths = [
            "/usr/share/icons/hicolor/scalable/apps/tux-tunes.svg",
            "/usr/share/icons/hicolor/128x128/apps/tux-tunes.png",
            "/opt/tux-assistant/assets/tux-tunes.svg",
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
                        "assets", "tux-tunes.svg"),
        ]
        
        for icon_path in icon_paths:
            if os.path.exists(icon_path):
                try:
                    # Load as pixbuf and set as window icon
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file(icon_path)
                    # Scale if needed
                    if pixbuf.get_width() > 128:
                        pixbuf = pixbuf.scale_simple(128, 128, GdkPixbuf.InterpType.BILINEAR)
                    
                    # Create texture from pixbuf
                    texture = Gdk.Texture.new_for_pixbuf(pixbuf)
                    
                    # For GTK4, we need to use the display's icon theme
                    # The icon is set via desktop file or WM_CLASS matching
                    # For now, just ensure the desktop file is correct
                    print(f"Icon loaded from: {icon_path}")
                    return
                except Exception as e:
                    print(f"Failed to load icon from {icon_path}: {e}")
        
        print("Using fallback icon")
    
    def cleanup(self):
        """Clean up resources."""
        self.player.cleanup()


class AddStationDialog(Adw.Dialog):
    """Dialog for adding a custom station."""
    
    def __init__(self, parent, on_add_callback=None):
        super().__init__()
        
        self.parent = parent
        self.on_add_callback = on_add_callback
        self.set_title("Add Custom Station")
        self.set_content_width(400)
        self.set_content_height(300)
        
        self._build_ui()
    
    def _build_ui(self):
        """Build dialog UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        # Header
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)
        
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda b: self.close())
        header.pack_start(cancel_btn)
        
        self.add_btn = Gtk.Button(label="Add")
        self.add_btn.add_css_class("suggested-action")
        self.add_btn.set_sensitive(False)
        self.add_btn.connect("clicked", self._on_add)
        header.pack_end(self.add_btn)
        
        toolbar_view.add_top_bar(header)
        
        # Content
        clamp = Adw.Clamp()
        clamp.set_maximum_size(400)
        clamp.set_margin_top(24)
        clamp.set_margin_bottom(24)
        clamp.set_margin_start(16)
        clamp.set_margin_end(16)
        toolbar_view.set_content(clamp)
        
        group = Adw.PreferencesGroup()
        group.set_title("Station Details")
        group.set_description("Enter the stream URL and name for your station")
        clamp.set_child(group)
        
        # Name entry
        self.name_row = Adw.EntryRow()
        self.name_row.set_title("Station Name")
        self.name_row.connect("changed", self._validate)
        group.add(self.name_row)
        
        # URL entry
        self.url_row = Adw.EntryRow()
        self.url_row.set_title("Stream URL")
        self.url_row.set_input_purpose(Gtk.InputPurpose.URL)
        self.url_row.connect("changed", self._validate)
        group.add(self.url_row)
        
        # Genre/tags entry (optional)
        self.genre_row = Adw.EntryRow()
        self.genre_row.set_title("Genre (optional)")
        group.add(self.genre_row)
        
        # Help text
        help_label = Gtk.Label()
        help_label.set_markup(
            "<small>Supported formats: MP3, AAC, OGG streams\n"
            "Example: http://stream.example.com:8000/radio.mp3</small>"
        )
        help_label.set_wrap(True)
        help_label.add_css_class("dim-label")
        help_label.set_margin_top(12)
        group.add(help_label)
    
    def _validate(self, entry):
        """Validate input and enable/disable add button."""
        name = self.name_row.get_text().strip()
        url = self.url_row.get_text().strip()
        
        # Basic validation
        valid = bool(name) and bool(url) and (
            url.startswith("http://") or url.startswith("https://")
        )
        
        self.add_btn.set_sensitive(valid)
    
    def _on_add(self, button):
        """Handle add button click."""
        station = self.get_station()
        if station and self.on_add_callback:
            self.on_add_callback(station)
        self.close()
    
    def get_station(self) -> Optional[Station]:
        """Get the station from dialog input."""
        name = self.name_row.get_text().strip()
        url = self.url_row.get_text().strip()
        genre = self.genre_row.get_text().strip()
        
        if not name or not url:
            return None
        
        # Create a custom station with unique ID
        return Station(
            uuid=f"custom-{uuid_module.uuid4().hex[:12]}",
            name=name,
            url=url,
            url_resolved=url,
            homepage="",
            favicon="",
            country="Custom",
            countrycode="",
            state="",
            language="",
            tags=[genre] if genre else ["Custom"],
            codec="",
            bitrate=0,
            votes=0,
            clickcount=0,
        )


class EditStationDialog(Adw.Dialog):
    """Dialog for editing a custom station."""
    
    def __init__(self, parent, station: Station, on_save_callback=None):
        super().__init__()
        
        self.parent = parent
        self.station = station
        self.on_save_callback = on_save_callback
        self.set_title("Edit Station")
        self.set_content_width(400)
        self.set_content_height(300)
        
        self._build_ui()
    
    def _build_ui(self):
        """Build dialog UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        # Header
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)
        
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda b: self.close())
        header.pack_start(cancel_btn)
        
        self.save_btn = Gtk.Button(label="Save")
        self.save_btn.add_css_class("suggested-action")
        self.save_btn.connect("clicked", self._on_save)
        header.pack_end(self.save_btn)
        
        toolbar_view.add_top_bar(header)
        
        # Content
        clamp = Adw.Clamp()
        clamp.set_maximum_size(400)
        clamp.set_margin_top(24)
        clamp.set_margin_bottom(24)
        clamp.set_margin_start(16)
        clamp.set_margin_end(16)
        toolbar_view.set_content(clamp)
        
        group = Adw.PreferencesGroup()
        group.set_title("Station Details")
        group.set_description("Edit the stream URL or name")
        clamp.set_child(group)
        
        # Name entry (pre-filled)
        self.name_row = Adw.EntryRow()
        self.name_row.set_title("Station Name")
        self.name_row.set_text(self.station.name)
        self.name_row.connect("changed", self._validate)
        group.add(self.name_row)
        
        # URL entry (pre-filled)
        self.url_row = Adw.EntryRow()
        self.url_row.set_title("Stream URL")
        self.url_row.set_text(self.station.url)
        self.url_row.set_input_purpose(Gtk.InputPurpose.URL)
        self.url_row.connect("changed", self._validate)
        group.add(self.url_row)
        
        # Genre/tags entry (pre-filled)
        self.genre_row = Adw.EntryRow()
        self.genre_row.set_title("Genre (optional)")
        self.genre_row.set_text(", ".join(self.station.tags) if self.station.tags else "")
        group.add(self.genre_row)
        
        # Help text
        help_label = Gtk.Label()
        help_label.set_markup(
            "<small>Supported formats: MP3, AAC, OGG streams\n"
            "Example: http://stream.example.com:8000/radio.mp3</small>"
        )
        help_label.set_wrap(True)
        help_label.add_css_class("dim-label")
        help_label.set_margin_top(12)
        group.add(help_label)
    
    def _validate(self, entry):
        """Validate input and enable/disable save button."""
        name = self.name_row.get_text().strip()
        url = self.url_row.get_text().strip()
        
        # Basic validation
        valid = bool(name) and bool(url) and (
            url.startswith("http://") or url.startswith("https://")
        )
        
        self.save_btn.set_sensitive(valid)
    
    def _on_save(self, button):
        """Handle save button click."""
        updated = self.get_updated_station()
        if updated and self.on_save_callback:
            self.on_save_callback(self.station.uuid, updated)
        self.close()
    
    def get_updated_station(self) -> Optional[Station]:
        """Get the updated station from dialog input."""
        name = self.name_row.get_text().strip()
        url = self.url_row.get_text().strip()
        genre = self.genre_row.get_text().strip()
        
        if not name or not url:
            return None
        
        # Keep the same UUID so it updates in place
        return Station(
            uuid=self.station.uuid,
            name=name,
            url=url,
            url_resolved=url,
            homepage="",
            favicon="",
            country="Custom",
            countrycode="",
            state="",
            language="",
            tags=[t.strip() for t in genre.split(",")] if genre else ["Custom"],
            codec="",
            bitrate=0,
            votes=0,
            clickcount=0,
        )
