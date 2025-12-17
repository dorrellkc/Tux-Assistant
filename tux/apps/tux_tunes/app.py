"""
Tux Tunes - GTK4 Application

Main application class for the internet radio player.

Copyright (c) 2025 Christopher Dorrell. Licensed under GPL-3.0.
"""

import sys

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib

from . import __version__, __app_name__, __app_id__
from .window import TuxTunesWindow


class TuxTunesApp(Adw.Application):
    """Main Tux Tunes application."""
    
    def __init__(self):
        super().__init__(
            application_id=__app_id__,
            flags=Gio.ApplicationFlags.NON_UNIQUE
        )
        
        self.window = None
        
        # Set up actions
        self._setup_actions()
    
    def _setup_actions(self):
        """Set up application actions."""
        # About action
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about)
        self.add_action(about_action)
        
        # Preferences action
        prefs_action = Gio.SimpleAction.new("preferences", None)
        prefs_action.connect("activate", self._on_preferences)
        self.add_action(prefs_action)
        
        # Shortcuts action
        shortcuts_action = Gio.SimpleAction.new("shortcuts", None)
        shortcuts_action.connect("activate", self._on_shortcuts)
        self.add_action(shortcuts_action)
        
        # Quit action
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", self._on_quit)
        self.add_action(quit_action)
        self.set_accels_for_action("app.quit", ["<Control>q"])
        
        # Keyboard shortcuts
        self.set_accels_for_action("app.preferences", ["<Control>comma"])
    
    def do_activate(self):
        """Handle application activation."""
        print("do_activate called!")
        if not self.window:
            print("Creating window...")
            self.window = TuxTunesWindow(application=self)
            print("Window created!")
            
            # Check audio analysis dependencies on first launch
            GLib.timeout_add(1000, self._check_audio_deps)
        
        print("Presenting window...")
        self.window.present()
        print("Window presented!")
    
    def _check_audio_deps(self):
        """Check if audio analysis libraries are available."""
        # Recording disabled - no need to notify user about missing libs
        # Keeping the check for future debugging only
        try:
            from .audio_analyzer import check_requirements
            reqs = check_requirements()
            
            if not reqs['full_features']:
                # Just log, don't show toast since recording is disabled
                print("Audio deps: Some missing (recording disabled anyway)")
            else:
                print("Audio analysis: All dependencies available")
        except Exception as e:
            print(f"Audio deps check error: {e}")
        
        return False  # Don't repeat
    
    def do_shutdown(self):
        """Handle application shutdown."""
        if self.window:
            self.window.cleanup()
        
        Adw.Application.do_shutdown(self)
    
    def _on_about(self, action, param):
        """Show about dialog."""
        about = Adw.AboutDialog()
        about.set_application_name(__app_name__)
        about.set_version(__version__)
        about.set_developer_name("Christopher Dorrell")
        about.set_license_type(Gtk.License.CUSTOM)
        about.set_copyright("© 2025 Christopher Dorrell")
        about.set_comments(
            "Internet radio player with smart recording.\n\n"
            "Captures complete songs without cut-offs using intelligent buffering."
        )
        about.set_website("https://github.com/yourusername/tux-tunes")
        about.set_application_icon("audio-x-generic")
        
        # Credits
        about.set_developers(["Christopher Dorrell"])
        about.set_designers(["Christopher Dorrell"])
        
        # Acknowledgments
        about.add_acknowledgement_section(
            "Powered By",
            ["radio-browser.info - Community Radio Database", "GStreamer - Multimedia Framework"]
        )
        
        about.present(self.window)
    
    def _on_preferences(self, action, param):
        """Show preferences dialog."""
        dialog = PreferencesDialog(self.window)
        dialog.present(self.window)
    
    def _on_shortcuts(self, action, param):
        """Show keyboard shortcuts."""
        # Simple toast for now
        if self.window:
            toast = Adw.Toast.new("Space: Play/Pause • Ctrl+Q: Quit")
            self.window.toast_overlay.add_toast(toast)
    
    def _on_quit(self, action, param):
        """Quit the application."""
        self.quit()


class PreferencesDialog(Adw.PreferencesDialog):
    """Preferences dialog."""
    
    def __init__(self, window: TuxTunesWindow):
        super().__init__()
        
        self.window = window
        self.library = window.library
        
        self.set_title("Preferences")
        
        self._build_ui()
    
    def _build_ui(self):
        """Build preferences UI."""
        # Recording page
        recording_page = Adw.PreferencesPage()
        recording_page.set_title("Recording")
        recording_page.set_icon_name("tux-media-record-symbolic")
        self.add(recording_page)
        
        # Recording settings group
        rec_group = Adw.PreferencesGroup()
        rec_group.set_title("Recording Settings")
        rec_group.set_description("Configure how tracks are recorded")
        recording_page.add(rec_group)
        
        # Recording mode
        mode_row = Adw.ComboRow()
        mode_row.set_title("Recording Mode")
        mode_row.set_subtitle("How to handle recorded tracks")
        
        modes = Gtk.StringList.new(["Ask for each track", "Auto-save all tracks", "Don't record"])
        mode_row.set_model(modes)
        
        current_mode = self.library.get_config('recording_mode', 'ask')
        mode_map = {'ask': 0, 'auto': 1, 'none': 2}
        mode_row.set_selected(mode_map.get(current_mode, 0))
        mode_row.connect("notify::selected", self._on_recording_mode_changed)
        rec_group.add(mode_row)
        
        # Pre-buffer
        pre_buffer_row = Adw.SpinRow.new_with_range(0, 15, 1)
        pre_buffer_row.set_title("Pre-buffer (seconds)")
        pre_buffer_row.set_subtitle("Audio captured before song detection")
        pre_buffer_row.set_value(self.library.get_config('pre_buffer_seconds', 8))
        pre_buffer_row.connect("notify::value", self._on_pre_buffer_changed)
        rec_group.add(pre_buffer_row)
        
        # Post-buffer
        post_buffer_row = Adw.SpinRow.new_with_range(0, 10, 1)
        post_buffer_row.set_title("Post-buffer (seconds)")
        post_buffer_row.set_subtitle("Continue recording after song ends")
        post_buffer_row.set_value(self.library.get_config('post_buffer_seconds', 3))
        post_buffer_row.connect("notify::value", self._on_post_buffer_changed)
        rec_group.add(post_buffer_row)
        
        # Storage group
        storage_group = Adw.PreferencesGroup()
        storage_group.set_title("Storage")
        recording_page.add(storage_group)
        
        # Recordings directory
        dir_row = Adw.ActionRow()
        dir_row.set_title("Recordings Folder")
        dir_row.set_subtitle(self.library.get_recordings_dir())
        dir_row.set_activatable(True)
        dir_row.add_suffix(Gtk.Image.new_from_icon_name("folder-open-symbolic"))
        dir_row.connect("activated", self._on_choose_directory)
        storage_group.add(dir_row)
        self.dir_row = dir_row
        
        # Playback page
        playback_page = Adw.PreferencesPage()
        playback_page.set_title("Playback")
        playback_page.set_icon_name("tux-multimedia-player-symbolic")
        self.add(playback_page)
        
        # Playback group
        play_group = Adw.PreferencesGroup()
        play_group.set_title("Playback Settings")
        playback_page.add(play_group)
        
        # Min recording duration
        min_dur_row = Adw.SpinRow.new_with_range(10, 120, 5)
        min_dur_row.set_title("Minimum track duration (seconds)")
        min_dur_row.set_subtitle("Tracks shorter than this won't be saved")
        min_dur_row.set_value(self.library.get_config('min_recording_seconds', 30))
        min_dur_row.connect("notify::value", self._on_min_duration_changed)
        play_group.add(min_dur_row)
    
    def _on_recording_mode_changed(self, row, param):
        """Handle recording mode change."""
        modes = ['ask', 'auto', 'none']
        selected = row.get_selected()
        if 0 <= selected < len(modes):
            self.library.set_config('recording_mode', modes[selected])
    
    def _on_pre_buffer_changed(self, row, param):
        """Handle pre-buffer change."""
        self.library.set_config('pre_buffer_seconds', int(row.get_value()))
        self.window.player.pre_buffer_seconds = int(row.get_value())
    
    def _on_post_buffer_changed(self, row, param):
        """Handle post-buffer change."""
        self.library.set_config('post_buffer_seconds', int(row.get_value()))
        self.window.player.post_buffer_seconds = int(row.get_value())
    
    def _on_min_duration_changed(self, row, param):
        """Handle min duration change."""
        self.library.set_config('min_recording_seconds', int(row.get_value()))
        self.window.player.min_recording_seconds = int(row.get_value())
    
    def _on_choose_directory(self, row):
        """Handle directory chooser."""
        dialog = Gtk.FileDialog()
        dialog.set_title("Choose Recordings Folder")
        dialog.set_modal(True)
        
        # Set initial folder
        initial = Gio.File.new_for_path(self.library.get_recordings_dir())
        dialog.set_initial_folder(initial)
        
        dialog.select_folder(self.window, None, self._on_directory_chosen)
    
    def _on_directory_chosen(self, dialog, result):
        """Handle directory selection."""
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                path = folder.get_path()
                self.library.set_recordings_dir(path)
                self.dir_row.set_subtitle(path)
        except GLib.Error:
            pass  # User cancelled


def main():
    """Main entry point."""
    print("Tux Tunes starting...")
    
    try:
        # Initialize Adw
        Adw.init()
        print("Adw initialized")
        
        app = TuxTunesApp()
        print("App created, running...")
        result = app.run(sys.argv)
        print(f"App exited with code: {result}")
        return result
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
