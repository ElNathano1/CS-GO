"""
Lobby frame for the Go game application.

This module provides the main lobby interface where users can start new games,
access settings, view rules, and resume previous games.
"""

from typing import TYPE_CHECKING
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox

from gui.frames.settings_frame import SettingsFrame
from gui.frames.game_frame import GameFrame, SingleplayerGameFrame
from gui.frames.local_lobby_frame import LocalLobbyFrame
from gui.utils import random_username
from gui.widgets import TopLevelWindow

if TYPE_CHECKING:
    from gui.app import App
    from game.core import GoGame


class LobbyFrame(ttk.Frame):
    """
    Frame for initiating a lobby.

    Allows the user to start a new game, consult the game rules and go to parameters.
    """

    def __init__(self, parent: ttk.Frame, app: "App"):
        """
        Initialize the lobby frame.

        Args:
            parent (ttk.Frame): The parent frame.
            app (App): The main application instance.
        """
        super().__init__(parent)

        self.app = app
        self._loading = None
        if not self.app.has_loading():
            self._loading = self.app.show_loading("Chargement du lobby...")

        self.after(0, self._build_step_1)

    def _build_step_1(self) -> None:
        """
        First step: background music + account panel wiring.
        """

        # Play background music if sound is not already playing
        if (
            self.app.sound_manager.is_enabled()
            and not self.app.sound_manager.is_playing("background_music")
        ):
            self.app.sound_manager.play_exclusive("background_music")

        # Ensure account panel is visible on this frame
        if hasattr(self.app, "account_panel") and self.app.account_panel:
            self.app.account_panel.lift()
            # Setup callbacks for this frame
            self.app.usee_updated_callback = self._update_account_info  # type: ignore
            self.app.profile_photo_updated_callback = self._update_profile_photo  # type: ignore
            self.app.connection_strength_callback = self._on_connection_strength_changed  # type: ignore
            # Ensure current account info/photo are applied on entry
            self._update_account_info()

        self.after(0, self._build_step_2)

    def _build_step_2(self) -> None:
        """
        Second step: title.
        """

        # Title
        title = tk.Canvas(
            self,
            width=600,
            height=182,
            relief=tk.FLAT,
            bd=0,
            highlightthickness=0,
            bg="#1e1e1e",
        )
        title.create_image(
            0,
            0,
            image=self.app.cs_go_banner,
            anchor="nw",
        )
        title.pack(pady=40)

        self.after(0, self._build_step_3)

    def _build_step_3(self) -> None:
        """
        Third step: menu and buttons.
        """

        # Menu frame
        main_menu_frame = self.app.Frame(self, bg="black", bd=1)
        main_menu_frame.pack(pady=20, padx=30)
        self._menu_frame = self.app.Frame(main_menu_frame)
        self._menu_frame.pack(pady=3, padx=3)

        self._menu_build_steps = [
            self._build_local_button,
            self._build_online_button,
            self._build_settings_button,
            self._build_return_button,
        ]
        self._build_menu_step(0)

    def _build_menu_step(self, index: int) -> None:
        if index >= len(self._menu_build_steps):
            if self._loading is not None:
                self.app.hide_loading(self._loading)
            return

        self._menu_build_steps[index]()
        self.after(0, lambda: self._build_menu_step(index + 1))

    def _build_local_button(self) -> None:
        self.app.Button(
            self._menu_frame.content_frame,
            overlay_path=self.app.local_icon_path,
            hover_overlay_path=self.app.hovered_local_icon_path,
            text="Partie locale",
            command=lambda: self._open_local_game(),
            takefocus=False,
        ).pack(pady=(20, 10), fill=tk.X, padx=30)

    def _build_online_button(self) -> None:
        self.online_button = self.app.Button(
            self._menu_frame.content_frame,
            overlay_path=self.app.online_icon_path,
            hover_overlay_path=self.app.hovered_online_icon_path,
            text="Partie en ligne",
            state=tk.DISABLED if self.app.name is None else tk.NORMAL,
            command=lambda: self._open_online_game(),
            takefocus=False,
        )
        self.online_button.pack(pady=10, fill=tk.X, padx=30)

    def _build_settings_button(self) -> None:
        self.app.Button(
            self._menu_frame.content_frame,
            overlay_path=self.app.prefs_icon_path,
            hover_overlay_path=self.app.hovered_prefs_icon_path,
            text="Paramètres",
            command=lambda: self._open_settings(),
            takefocus=False,
        ).pack(pady=10, fill=tk.X, padx=30)

    def _build_return_button(self) -> None:
        self.app.Button(
            self._menu_frame.content_frame,
            overlay_path=self.app.return_icon_path,
            hover_overlay_path=self.app.hovered_return_icon_path,
            text="Retour au bureau",
            command=lambda: self.app.return_to_desktop(),
            takefocus=False,
        ).pack(pady=(10, 20), fill=tk.X, padx=30)

    def _open_local_game(self) -> None:
        """
        Open the game starting window.

        Args:
            game (GoGame, optional): The game instance to resume. Defaults to None.
        """

        self.app.show_frame(lambda parent, app: LocalLobbyFrame(parent, app))

    def _open_online_game(self) -> None:
        """
        Open the online game lobby.
        """
        pass

    def _open_settings(self) -> None:
        """
        Open settings window.
        """

        self.app.open_dialog(
            dialog=TopLevelWindow(self.app, width=400, height=600),
            frame_class=SettingsFrame,  # type: ignore
            show_account_panel=False,
        )

    def _update_account_info(self) -> None:
        """
        Update the account info displayed in the account panel.
        """
        display_name = self.app.name if self.app.name else random_username()
        self.app.account_profile_photo.config(text=f"{display_name}  ")
        self._update_profile_photo()

    def _update_profile_photo(self) -> None:
        """
        Update the profile photo displayed in the account panel.
        """
        new_photo = self.app.get_profile_photo()
        self.app.account_profile_photo.config(image=new_photo)
        # Keep a reference to prevent garbage collection
        self.app.account_profile_photo.image = new_photo  # type: ignore

    def _on_connection_strength_changed(self, strength: int) -> None:
        """
        Update online button state based on connection strength.

        Args:
            strength: Connection strength (0=poor/none, 1=weak, 2=good, 3=excellent)
        """
        if not self.winfo_exists() or not hasattr(self, "online_button"):
            return
        if not self.online_button.winfo_exists():
            return
        # Disable online button if no connection (strength == 0)
        if strength == 0:
            self.online_button.config(state=tk.DISABLED)
        else:
            self.online_button.config(state=tk.NORMAL)
