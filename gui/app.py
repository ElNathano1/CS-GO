"""
Main application class for the Go game.

This module contains the App class which is the main window and controller
for the entire application.
"""

import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox
import sys
from pathlib import Path
from PIL import Image, ImageTk
import os

import httpx
import requests
import asyncio
import threading

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import from reorganized modules
from gui.widgets import TexturedButton, TopLevelWindow
from gui.sound_manager import SoundManager
from gui.game_canvas import StoneBowl
from gui.utils import save_preferences as save_dictionnary  # Legacy name
from gui.frames import LobbyFrame
from gui.frames.login_dialog import LoginFrame

# Game logic imports
from player.ai import Martin, Leo, Magnus
from game.core import Goban, GoGame
from game.utils import save_game

# API base URL
BASE_URL = "https://cs-go-production.up.railway.app"


class App(tk.Tk):
    """
    The main application window for the Go game.

    Manages the whole application, including navigation between different frames
    (lobby and game).

    Attributes:
        sound_manager (SoundManager): The sound manager instance.
        current_frame: The currently displayed frame.
        preferences (dict): User preferences for the application.
        current_game (GoGame, optional): The current game instance for resuming later.
    """

    def __init__(
        self,
        preferences: dict,
        current_game: GoGame | None = None,
    ):
        """
        Initialize the main application window.

        Args:
            preferences (dict): User preferences for the application.
            current_game (GoGame, optional): The current game instance for resuming later. Defaults to None.
        """

        super().__init__()

        self.title("CS Go")
        self.resizable(False, False)
        self.overrideredirect(True)

        # Initialize sound manager
        self.sound_manager = SoundManager()

        # Store and apply preferences
        self.username = None
        self.token = None
        self.preferences = preferences
        self.apply_preferences()

        # Setup styles
        self._setup_styles()

        # Create main container
        self.container = ttk.Frame(self)
        self.container.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.current_frame = None

        # Apply full screen window
        try:
            self.state("zoomed")
        except tk.TclError:
            self.attributes("-fullscreen", True)
        self.update_idletasks()

        # Save current game state for resuming later
        self.current_game = current_game

        # Show lobby frame on startup
        self.show_frame(LobbyFrame)

        # Bind the click sound to all button clicks, except for placing stones and passing
        self.bind_all("<Button-1>", self._on_global_click, add="+")

        # Replace the default close behavior to save preferences
        self.protocol("WM_DELETE_WINDOW", self.return_to_desktop)

        # Defer login dialog opening until mainloop is active
        # Only show immediately if there's no saved token to verify
        if self.username is None or self.token is None:
            if self.preferences.get("stay_logged_in") and self.preferences.get("auth_token"):
                # Token verification in progress, wait for result
                # Fallback: show dialog after 3 seconds if verification takes too long
                self.after(3000, self._show_login_dialog_if_needed)
            else:
                # No token to verify, show dialog immediately
                self.after(100, self._show_login_dialog)

    def _on_global_click(self, event: tk.Event) -> None:
        """
        Play click sound on button clicks, except for specific buttons.

        Args:
            event (tk.Event): The click event.
        """

        widget = event.widget
        if isinstance(widget, ttk.Button):
            # Exclude specific buttons from click sound
            excluded_texts = {"Passer"}
            excluded_states = {tk.DISABLED, "disabled"}
            if (
                widget.cget("text") not in excluded_texts
                and widget.cget("state") not in excluded_states
            ):
                self.sound_manager.play("click_effect")
            if widget.cget("state") == "disabled":
                self.sound_manager.play("invalid_move_effect")

        if isinstance(widget, TexturedButton):
            # Exclude specific buttons from click sound
            excluded_texts = {"Passer"}
            excluded_states = {tk.DISABLED, "disabled"}
            if (
                widget.cget("text") not in excluded_texts
                and widget.cget("state") not in excluded_states
            ):
                self.sound_manager.play("click_effect")
            if widget.is_disabled():
                self.sound_manager.play("invalid_move_effect")

    def _load_banners(self) -> None:
        """
        Load banner image for the application.
        """

        banner_dir = Path(__file__).parent / "images/banners"

        # Load welcome banner
        self.welcome_banner_path = banner_dir / "cs_go_banner.png"
        if self.welcome_banner_path.exists():
            self.welcome_banner = ImageTk.PhotoImage(
                Image.open(self.welcome_banner_path).resize(
                    (1000, 300), Image.Resampling.LANCZOS
                )
            )

    def _load_icons(self) -> None:
        """
        Load icons for the widgets.
        """

        images_dir = Path(__file__).parent / "images/icons"

        # Load application icon
        self.icon_path = images_dir / "app_icon.ico"
        if self.icon_path.exists():
            self.iconbitmap(self.icon_path)

        # Load AI icon
        self.ai_icon_path = images_dir / "ai.png"
        if self.ai_icon_path.exists():
            self.ai_icon = ImageTk.PhotoImage(
                Image.open(self.ai_icon_path).resize((32, 32), Image.Resampling.LANCZOS)
            )

        # Load pass icon
        self.pass_icon_path = images_dir / "pass.png"
        if self.pass_icon_path.exists():
            self.pass_icon = ImageTk.PhotoImage(
                Image.open(self.pass_icon_path).resize(
                    (32, 32), Image.Resampling.LANCZOS
                )
            )

        # Load preferences icon
        self.prefs_icon_path = images_dir / "preferences.png"
        if self.prefs_icon_path.exists():
            self.prefs_icon = ImageTk.PhotoImage(
                Image.open(self.prefs_icon_path).resize(
                    (32, 32), Image.Resampling.LANCZOS
                )
            )

        # Load resign icon
        self.resign_icon_path = images_dir / "resign.png"
        if self.resign_icon_path.exists():
            self.resign_icon = ImageTk.PhotoImage(
                Image.open(self.resign_icon_path).resize(
                    (32, 32), Image.Resampling.LANCZOS
                )
            )

        # Load return icon
        self.return_icon_path = images_dir / "return.png"
        if self.return_icon_path.exists():
            self.return_icon = ImageTk.PhotoImage(
                Image.open(self.return_icon_path).resize(
                    (32, 32), Image.Resampling.LANCZOS
                )
            )

        # Load revenge icon
        self.revenge_icon_path = images_dir / "revenge.png"
        if self.revenge_icon_path.exists():
            self.revenge_icon = ImageTk.PhotoImage(
                Image.open(self.revenge_icon_path).resize(
                    (32, 32), Image.Resampling.LANCZOS
                )
            )

        # Load rules icon
        self.rules_icon_path = images_dir / "rules.png"
        if self.rules_icon_path.exists():
            self.rules_icon = ImageTk.PhotoImage(
                Image.open(self.rules_icon_path).resize(
                    (32, 32), Image.Resampling.LANCZOS
                )
            )

    def _load_textures(self) -> None:
        """
        Load textures for the widgets.
        """

        textures_dir = Path(__file__).parent / "images/textures"

        # Load light wood texture
        light_wood_path = textures_dir / "light_wood_texture.png"
        if light_wood_path.exists():
            self.light_wood_texture = light_wood_path

        # Load dark wood texture
        dark_wood_path = textures_dir / "dark_wood_texture.png"
        if dark_wood_path.exists():
            self.dark_wood_texture = dark_wood_path

    def _setup_styles(self) -> None:
        """
        Configure ttk styles for buttons, labels, and other widgets.

        Sets up consistent colors, fonts, and appearance for the application.
        """

        self._load_icons()
        self._load_textures()

        style = ttk.Style()
        style.theme_use("clam")

        # Configure button style
        style.configure("TButton", font=("Spell of Asia", 18), padding=5)

        # Configure label style
        style.configure("TLabel", font=("Spell of Asia", 18), background="#f0f0f0")

        # Configure title label style
        style.configure(
            "Title.TLabel", font=("Spell of Asia", 24, "bold"), background="#f0f0f0"
        )

    def Button(
        self,
        parent,
        texture_path: str | Path = Path(__file__).parent
        / "images/textures/light_wood_texture.png",
        text: str = "",
        overlay_path: str | Path | None = None,
        width: int = 230,
        height: int = 40,
        overlay_compound: str = "left",
        overlay_padding: int = 8,
        text_color: str = "black",
        font: tuple[str, int] | None = ("Spell of Asia", 16),
        font_dpi_scale: float = 96 / 72,
        bd: int = 2,
        highlightthickness: int = 0,
        bg: str = "black",
        relief=tk.FLAT,
        cursor: str = "hand2",
        disabled: bool = False,
        **kwargs,
    ) -> TexturedButton:
        """
        Create a default textured button for the application.

        Returns:
            TexturedButton: Default texture button for the app.
        """

        return TexturedButton(
            parent=parent,
            texture_path=texture_path,
            text=text,
            overlay_path=overlay_path,
            width=width,
            height=height,
            overlay_compound=overlay_compound,
            overlay_padding=overlay_padding,
            text_color=text_color,
            font=font,
            font_dpi_scale=font_dpi_scale,
            bd=bd,
            highlightthickness=highlightthickness,
            bg=bg,
            relief=relief,
            cursor=cursor,
            disabled=disabled,
            **kwargs,
        )

    def show_frame(self, frame_class) -> None:
        """
        Switch to a different frame.

        Args:
            frame_class: The frame class to display.
        """

        if self.current_frame is not None:
            self.current_frame.destroy()

        self.current_frame = frame_class(self.container, self)
        self.current_frame.grid(row=0, column=0, sticky="nsew")

    def apply_preferences(self) -> None:
        """
        Apply user preferences to the application.
        """

        # Ensure expected preference keys exist
        self.preferences.setdefault("stay_logged_in", True)
        self.preferences.setdefault("auth_token", None)

        # Apply sound preference
        if self.preferences.get("sound_enabled", True):
            if not self.sound_manager.is_enabled():
                self.sound_manager.toggle()

            for event in self.sound_manager.sounds:
                if "music" in event:
                    self.sound_manager.sounds[event].set_volume(
                        self.preferences["master_volume"]
                        * self.preferences["music_volume"]
                        / 10000
                    )

            for event in self.sound_manager.sounds:
                if "effect" in event:
                    self.sound_manager.sounds[event].set_volume(
                        self.preferences["master_volume"]
                        * self.preferences["effects_volume"]
                        / 10000
                    )
        else:
            if self.sound_manager.is_enabled():
                self.sound_manager.toggle()

            for event in self.sound_manager.sounds:
                self.sound_manager.sounds[event].set_volume(0)

        # Apply account preferences
        if self.preferences.get("stay_logged_in"):
            token = self.preferences.get("auth_token")
            if token is not None:
                thread = threading.Thread(
                    target=lambda: asyncio.run(self._verify_token(token))
                )
                thread.start()

    async def _verify_token(self, token: str) -> None:
        """
        Verify the authentication token with the backend API.

        Args:
            token (str): The authentication token to verify.
        """

        try:
            async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
                response = await client.get(
                    f"{BASE_URL}/auth/verify",
                    params={"token": token},
                )

                if response.status_code == 200:
                    data = response.json()
                    # Update in main thread
                    self.after(0, self._on_token_verified, data, token)
                else:
                    # Invalid token, clear it
                    self.after(0, self._on_token_invalid)

        except Exception as e:
            # Network error or invalid token
            print(f"Token verification error: {e}")
            self.after(0, self._on_token_invalid)

    def _on_token_verified(self, data: dict, token: str) -> None:
        """Called in main thread when token is verified."""
        self.username = data.get("username")
        self.token = token

    def _on_token_invalid(self) -> None:
        """Called in main thread when token is invalid."""
        self.preferences["auth_token"] = None
        # Show login dialog since token is invalid
        self._show_login_dialog()

    def open_dialog(
        self, dialog: TopLevelWindow, frame_class: type[tk.Frame] | None = None
    ) -> None:
        """
        Open a dialog window and optionally mount a frame inside.

        Args:
            dialog: An initialized TopLevelWindow instance
            frame_class: Optional frame class to display inside the dialog
        """

        if frame_class is not None:
            frame = frame_class(dialog.body_frame, self)  # type: ignore
            frame.pack(fill=tk.BOTH, expand=True)
        dialog.show(wait=False)

    def _show_login_dialog(self) -> None:
        """
        Show the login dialog (called after mainloop is active).
        """

        self.open_dialog(TopLevelWindow(self, width=400, height=600), LoginFrame)  # type: ignore

    def _show_login_dialog_if_needed(self) -> None:
        """
        Show login dialog only if user is still not logged in (fallback after token verification timeout).
        """

        if self.username is None or self.token is None:
            self._show_login_dialog()

    def _center_window(self) -> None:
        """
        Center the application window on the screen.
        """
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"+{x}+{y}")

    def return_to_desktop(self) -> None:
        """
        Return to the desktop by closing the application.
        """

        result = messagebox.askyesno(
            "Quitter le jeu",
            "Voulez-vous retourner au bureau ?",
        )
        if result:
            save_dictionnary(self.preferences, "preferences.prefs")
            if self.current_game is not None:
                save_game(self.current_game, "saves/autosave.csgogame")
            else:
                try:
                    os.remove("saves/autosave.csgogame")
                except:
                    pass
            self.quit()
