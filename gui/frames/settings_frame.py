"""
Settings frame for the Go game application.

This module provides the settings interface where users can adjust sound preferences,
volume levels, and other application settings.
"""

from typing import TYPE_CHECKING
import tkinter as tk
import tkinter.ttk as ttk

if TYPE_CHECKING:
    from gui.app import App


class SettingsFrame(ttk.Frame):
    """
    Frame for application settings.

    Allows the user to adjust sound settings and other preferences.
    """

    def __init__(self, parent: ttk.Frame, app: "App"):
        """
        Initialize the settings frame.

        Args:
            parent (ttk.Frame): The parent frame.
            app (App): The main application instance.
        """

        super().__init__(parent)

        self.app = app

        # Title
        title = ttk.Label(self, text="Paramètres", style="Title.TLabel")
        title.pack(pady=(40, 20))

        # Sound options frame
        main_option_frame = self.app.Frame(self, bg="black", bd=1)
        main_option_frame.pack(pady=20)
        option_frame = self.app.Frame(main_option_frame)
        option_frame.pack(pady=3, padx=3)

        # Sound settings
        self.sound_enabled = tk.BooleanVar(value=self.app.preferences["sound_enabled"])
        sound_enabled = ttk.Checkbutton(
            option_frame,
            text="Activer le son",
            variable=self.sound_enabled,
            takefocus=False,
        )
        sound_enabled.pack(padx=20, pady=(20, 10), fill=tk.X)

        # Volume controls
        self.app.Label(option_frame, text="Volume principal").pack(
            padx=20, pady=(10, 0)
        )
        self.master_volume_slider = ttk.Scale(
            option_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            variable=tk.IntVar(value=self.app.preferences["master_volume"]),
            takefocus=False,
        )
        self.master_volume_slider.pack(padx=20, pady=10, fill=tk.X, expand=True)

        self.app.Label(option_frame, text="Volume de la musique").pack(
            padx=20, pady=(10, 0)
        )
        self.music_volume_slider = ttk.Scale(
            option_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            variable=tk.IntVar(value=self.app.preferences["music_volume"]),
            takefocus=False,
        )
        self.music_volume_slider.pack(padx=20, pady=10, fill=tk.X, expand=True)

        self.app.Label(option_frame, text="Volume des effets").pack(
            padx=20, pady=(10, 0)
        )
        self.effects_volume_slider = ttk.Scale(
            option_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            variable=tk.IntVar(value=self.app.preferences["effects_volume"]),
            takefocus=False,
        )
        self.effects_volume_slider.pack(padx=20, pady=(10, 20), fill=tk.X, expand=True)

        # Return to Lobby button
        self.app.Button(
            self,
            text="Retour au Lobby",
            overlay_path=self.app.return_icon_path,
            hover_overlay_path=self.app.hovered_return_icon_path,
            command=self._return_to_lobby,
            takefocus=False,
        ).pack(pady=20)

        # Save settings when sliders or checkbox are changed
        sound_enabled.config(command=self._save_settings)
        self.master_volume_slider.config(command=lambda e: self._save_settings())
        self.music_volume_slider.config(command=lambda e: self._save_settings())
        self.effects_volume_slider.config(command=lambda e: self._save_settings())

    def _save_settings(self) -> None:
        """
        Save the current settings to the application preferences.
        """

        # Save sound settings
        self.app.preferences["sound_enabled"] = self.sound_enabled.get()
        self.app.preferences["master_volume"] = self.master_volume_slider.get()
        self.app.preferences["music_volume"] = self.music_volume_slider.get()
        self.app.preferences["effects_volume"] = self.effects_volume_slider.get()

        # Apply updated preferences
        self.app.apply_preferences()

    def _return_to_lobby(self) -> None:
        """
        Return to the lobby frame.
        """
        from gui.frames.lobby_frame import LobbyFrame

        self.app.show_frame(LobbyFrame)
