"""
Main application class for the Go game.

This module contains the App class which is the main window and controller
for the entire application.
"""

from io import BytesIO
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
from gui.widgets import TexturedButton, TexturedFrame, TopLevelWindow, TransparentLabel
from gui.sound_manager import SoundManager
from gui.game_canvas import StoneBowl
from gui.utils import (
    save_preferences as save_dictionnary,
    random_username,
)  # Legacy name
from gui.frames import LobbyFrame
from gui.frames.login_dialog import LoginFrame

# Game logic imports
from player.ai import Martin, Leo, Magnus
from game.core import Goban, GoGame
from game.utils import save_game

# API base URL
from config import BASE_URL, APP_NAME, WS_URL


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

        self.title(APP_NAME)
        self.resizable(False, False)

        # Initialize sound manager
        self.sound_manager = SoundManager()

        # Store and apply preferences
        self.username = None
        self.name = None
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
        self.attributes("-fullscreen", True)
        self.update_idletasks()

        # Save current game state for resuming later
        self.current_game = current_game

        # Initialize callback attributes
        self.username_updated_callback = None
        self.profile_photo_updated_callback = None
        self.connection_strength_callback = None

        # Connection monitoring
        self._connection_monitor_running = True
        self._connection_strength = 0  # 0-3: no signal, weak, medium, strong
        self._start_connection_monitor()

        # Show lobby frame on startup
        self.show_frame(LobbyFrame)

        # Bind the click sound to all button clicks, except for placing stones and passing
        self.bind_all("<Button-1>", self._on_global_click, add="+")

        # Replace the default close behavior to save preferences
        self.protocol("WM_DELETE_WINDOW", self.return_to_desktop)

        # Defer login dialog opening until mainloop is active
        # First, start token verification if applicable
        if self.preferences.get("stay_logged_in") and self.preferences.get(
            "auth_token"
        ):
            # Start token verification after mainloop is active
            self.after(50, self._start_token_verification)
            # Show login dialog after timeout if verification takes too long
            self.after(3000, self._show_login_dialog_if_needed)
        elif self.username is None or self.token is None:
            # No token to verify, show dialog immediately
            self.after(100, self._show_login_dialog)

        # Create account panel once (will be shown/hidden by frames)
        self._create_account_panel()

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
            widget_state = str(widget.cget("state"))
            if widget.cget("text") not in excluded_texts and widget_state != "disabled":
                self.sound_manager.play("click_effect")
            if widget_state == "disabled":
                self.sound_manager.play("invalid_move_effect")

        if isinstance(widget, TexturedButton):
            # Exclude specific buttons from click sound
            excluded_texts = {"Passer"}
            widget_state = str(widget.cget("state"))
            if widget.cget("text") not in excluded_texts and widget_state != "disabled":
                self.sound_manager.play("click_effect")
            if widget.is_disabled():
                self.sound_manager.play("invalid_move_effect")

    def _load_banners(self) -> None:
        """
        Load banner image for the application.
        """

        banner_dir = Path(__file__).parent / "images/banners"

        # Load welcome banner
        self.cs_go_banner_path = banner_dir / "cs_go_banner.png"
        if self.cs_go_banner_path.exists():
            self.cs_go_banner = ImageTk.PhotoImage(
                Image.open(self.cs_go_banner_path).resize(
                    (600, 182), Image.Resampling.LANCZOS
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

        # Load local icon
        self.local_icon_path = images_dir / "local.png"
        if self.local_icon_path.exists():
            self.local_icon = ImageTk.PhotoImage(
                Image.open(self.local_icon_path).resize(
                    (32, 32), Image.Resampling.LANCZOS
                )
            )
        self.hovered_local_icon_path = images_dir / "hovered_local.png"
        if self.hovered_local_icon_path.exists():
            self.hovered_local_icon = ImageTk.PhotoImage(
                Image.open(self.hovered_local_icon_path).resize(
                    (32, 32), Image.Resampling.LANCZOS
                )
            )

        # Load multiplayer icon
        self.multiplayer_icon_path = images_dir / "multiplayer.png"
        if self.multiplayer_icon_path.exists():
            self.multiplayer_icon = ImageTk.PhotoImage(
                Image.open(self.multiplayer_icon_path).resize(
                    (32, 32), Image.Resampling.LANCZOS
                )
            )
        self.hovered_multiplayer_icon_path = images_dir / "hovered_multiplayer.png"
        if self.hovered_multiplayer_icon_path.exists():
            self.hovered_multiplayer_icon = ImageTk.PhotoImage(
                Image.open(self.hovered_multiplayer_icon_path).resize(
                    (32, 32), Image.Resampling.LANCZOS
                )
            )

        # Load online icon
        self.online_icon_path = images_dir / "online.png"
        if self.online_icon_path.exists():
            self.online_icon = ImageTk.PhotoImage(
                Image.open(self.online_icon_path).resize(
                    (32, 32), Image.Resampling.LANCZOS
                )
            )
        self.hovered_online_icon_path = images_dir / "hovered_online.png"
        if self.hovered_online_icon_path.exists():
            self.hovered_online_icon = ImageTk.PhotoImage(
                Image.open(self.hovered_online_icon_path).resize(
                    (32, 32), Image.Resampling.LANCZOS
                )
            )

        # Load pass icon
        self.pass_icon_path = images_dir / "pass.png"
        if self.pass_icon_path.exists():
            self.pass_icon = ImageTk.PhotoImage(
                Image.open(self.pass_icon_path).resize(
                    (32, 32), Image.Resampling.LANCZOS
                )
            )
        self.hovered_pass_icon_path = images_dir / "hovered_pass.png"
        if self.hovered_pass_icon_path.exists():
            self.hovered_pass_icon = ImageTk.PhotoImage(
                Image.open(self.hovered_pass_icon_path).resize(
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
        self.hovered_prefs_icon_path = images_dir / "hovered_preferences.png"
        if self.hovered_prefs_icon_path.exists():
            self.hovered_prefs_icon = ImageTk.PhotoImage(
                Image.open(self.hovered_prefs_icon_path).resize(
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
        self.hovered_resign_icon_path = images_dir / "hovered_resign.png"
        if self.hovered_resign_icon_path.exists():
            self.hovered_resign_icon = ImageTk.PhotoImage(
                Image.open(self.hovered_resign_icon_path).resize(
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
        self.hovered_return_icon_path = images_dir / "hovered_return.png"
        if self.hovered_return_icon_path.exists():
            self.hovered_return_icon = ImageTk.PhotoImage(
                Image.open(self.hovered_return_icon_path).resize(
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
        self.hovered_revenge_icon_path = images_dir / "hovered_revenge.png"
        if self.hovered_revenge_icon_path.exists():
            self.hovered_revenge_icon = ImageTk.PhotoImage(
                Image.open(self.hovered_revenge_icon_path).resize(
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
        self.hovered_rules_icon_path = images_dir / "hovered_rules.png"
        if self.hovered_rules_icon_path.exists():
            self.hovered_rules_icon = ImageTk.PhotoImage(
                Image.open(self.hovered_rules_icon_path).resize(
                    (32, 32), Image.Resampling.LANCZOS
                )
            )

        # Load singleplayer icon
        self.singleplayer_icon_path = images_dir / "singleplayer.png"
        if self.singleplayer_icon_path.exists():
            self.singleplayer_icon = ImageTk.PhotoImage(
                Image.open(self.singleplayer_icon_path).resize(
                    (32, 32), Image.Resampling.LANCZOS
                )
            )
        self.hovered_singleplayer_icon_path = images_dir / "hovered_singleplayer.png"
        if self.hovered_singleplayer_icon_path.exists():
            self.hovered_singleplayer_icon = ImageTk.PhotoImage(
                Image.open(self.hovered_singleplayer_icon_path).resize(
                    (32, 32), Image.Resampling.LANCZOS
                )
            )

        # Load preferences icons
        # Load main volume icon
        self.sound_icon_path = images_dir / "sound.png"
        if self.sound_icon_path.exists():
            self.sound_icon = ImageTk.PhotoImage(
                Image.open(self.sound_icon_path).resize(
                    (32, 32), Image.Resampling.LANCZOS
                )
            )
        self.hovered_sound_icon_path = images_dir / "hovered_sound.png"
        if self.hovered_sound_icon_path.exists():
            self.hovered_sound_icon = ImageTk.PhotoImage(
                Image.open(self.hovered_sound_icon_path).resize(
                    (32, 32), Image.Resampling.LANCZOS
                )
            )
        self.no_sound_icon_path = images_dir / "no_sound.png"
        if self.no_sound_icon_path.exists():
            self.no_sound_icon = ImageTk.PhotoImage(
                Image.open(self.no_sound_icon_path).resize(
                    (32, 32), Image.Resampling.LANCZOS
                )
            )
        self.hovered_no_sound_icon_path = images_dir / "hovered_no_sound.png"
        if self.hovered_no_sound_icon_path.exists():
            self.hovered_no_sound_icon = ImageTk.PhotoImage(
                Image.open(self.hovered_no_sound_icon_path).resize(
                    (32, 32), Image.Resampling.LANCZOS
                )
            )

        # Load music icon
        self.music_icon_path = images_dir / "music.png"
        if self.music_icon_path.exists():
            self.music_icon = ImageTk.PhotoImage(
                Image.open(self.music_icon_path).resize(
                    (32, 32), Image.Resampling.LANCZOS
                )
            )
        self.hovered_music_icon_path = images_dir / "hovered_music.png"
        if self.hovered_music_icon_path.exists():
            self.hovered_music_icon = ImageTk.PhotoImage(
                Image.open(self.hovered_music_icon_path).resize(
                    (32, 32), Image.Resampling.LANCZOS
                )
            )
        self.no_music_icon_path = images_dir / "no_music.png"
        if self.no_music_icon_path.exists():
            self.no_music_icon = ImageTk.PhotoImage(
                Image.open(self.no_music_icon_path).resize(
                    (32, 32), Image.Resampling.LANCZOS
                )
            )
        self.hovered_no_music_icon_path = images_dir / "hovered_no_music.png"
        if self.hovered_no_music_icon_path.exists():
            self.hovered_no_music_icon = ImageTk.PhotoImage(
                Image.open(self.hovered_no_music_icon_path).resize(
                    (32, 32), Image.Resampling.LANCZOS
                )
            )

        # Load effects icon
        self.effects_icon_path = images_dir / "effects.png"
        if self.effects_icon_path.exists():
            self.effects_icon = ImageTk.PhotoImage(
                Image.open(self.effects_icon_path).resize(
                    (32, 32), Image.Resampling.LANCZOS
                )
            )
        self.hovered_effects_icon_path = images_dir / "hovered_effects.png"
        if self.hovered_effects_icon_path.exists():
            self.hovered_effects_icon = ImageTk.PhotoImage(
                Image.open(self.hovered_effects_icon_path).resize(
                    (32, 32), Image.Resampling.LANCZOS
                )
            )
        self.no_effects_icon_path = images_dir / "no_effects.png"
        if self.no_effects_icon_path.exists():
            self.no_effects_icon = ImageTk.PhotoImage(
                Image.open(self.no_effects_icon_path).resize(
                    (32, 32), Image.Resampling.LANCZOS
                )
            )
        self.hovered_no_effects_icon_path = images_dir / "hovered_no_effects.png"
        if self.hovered_no_effects_icon_path.exists():
            self.hovered_no_effects_icon = ImageTk.PhotoImage(
                Image.open(self.hovered_no_effects_icon_path).resize(
                    (32, 32), Image.Resampling.LANCZOS
                )
            )

        # Load wifi signal icons
        self.wifi_signal_icons = []
        for i in range(4):
            wifi_icon_path = images_dir / f"wifi_signal_{i}.png"
            if wifi_icon_path.exists():
                wifi_icon = ImageTk.PhotoImage(
                    Image.open(wifi_icon_path).resize(
                        (32, 32), Image.Resampling.LANCZOS
                    )
                )
                self.wifi_signal_icons.append(wifi_icon)

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

        self._load_banners()
        self._load_icons()
        self._load_textures()

        style = ttk.Style()
        style.theme_use("clam")

        # Configure frame style
        style.configure("TFrame", background="#1e1e1e")

        # Configure framed frame style
        style.configure(
            "Framed.TFrame",
            background="#1e1e1e",
            ipadx=10,
            ipady=10,
            relief=tk.RIDGE,
            borderwidth=2,
            bordercolor="#f6a90d",
        )

        # Configure button style
        style.configure(
            "TButton",
            font=("Skranji", 14, "bold"),
            background="#1e1e1e",
            foreground="white",
            borderwidth=0,
            relief=tk.FLAT,
        )
        style.map(
            "TButton",
            background=[("active", "#1e1e1e"), ("!active", "#1e1e1e")],
            foreground=[("disabled", "gray")],
        )

        # Configure account button style
        style.configure(
            "Account.TButton",
            font=("Skranji", 14, "bold"),
            background="#1e1e1e",
            foreground="white",
            padding=5,
            borderwidth=0,
            relief=tk.FLAT,
        )
        style.map(
            "Account.TButton",
            background=[("active", "#1e1e1e"), ("!active", "#1e1e1e")],
            foreground=[("disabled", "gray")],
        )

        # Configure label style
        style.configure(
            "TLabel",
            font=("Skranji", 14, "bold"),
            background="#1e1e1e",
            foreground="white",
        )

        # Configure title label style
        style.configure(
            "Title.TLabel",
            font=("Spell of Asia", 30, "bold"),
            background="#1e1e1e",
            foreground="white",
        )

        # Configure account label style
        style.configure(
            "Account.TLabel",
            font=("Skranji-Bold", 12),
            background="#1e1e1e",
            foreground="white",
        )

        # Configure error label style
        style.configure(
            "Error.TLabel",
            font=("Skranji", 8),
            background="#1e1e1e",
            foreground="red",
        )

        # Configure entry style
        style.configure(
            "TEntry",
            foreground="white",
            fieldbackground="#1e1e1e",
            borderwidth=2,
            relief=tk.SOLID,
            bordercolor="black",
            padding=2,
            insertcolor="white",
        )
        style.map(
            "TEntry",
            lightcolor=[("focus", "white"), ("!focus", "black")],
            lightthickness=[("focus", 2), ("!focus", 2)],
            bordercolor=[("focus", "white"), ("!focus", "black")],
        )

        # Configure error entry style
        style.configure(
            "Error.TEntry",
            foreground="white",
            fieldbackground="#1e1e1e",
            borderwidth=2,
            relief=tk.SOLID,
            bordercolor="red",
            padding=2,
            insertcolor="white",
        )
        style.map(
            "Error.TEntry",
            lightcolor=[("focus", "red"), ("!focus", "red")],
            lightthickness=[("focus", 2), ("!focus", 2)],
            bordercolor=[("focus", "red"), ("!focus", "red")],
        )

    def Button(
        self,
        parent,
        texture_path: str | Path = Path(__file__).parent
        / "images/textures/light_wood_texture.png",
        text: str = "",
        overlay_path: str | Path | None = None,
        hover_overlay_path: str | Path | None = None,
        width: int = 230,
        height: int = 50,
        overlay_compound: str = "left",
        overlay_padding: int = 10,
        text_color: str = "black",
        font: tuple[str, int] | None = ("Skranji-Bold", 14),
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
            hover_overlay_path=hover_overlay_path,
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

    def Frame(
        self,
        parent,
        texture_path: str | Path = Path(__file__).parent
        / "images/textures/dark_wood_texture.png",
        width: int | None = None,
        height: int | None = None,
        bd: int = 2,
        padx: int = 20,
        pady: int = 20,
        highlightthickness: int = 0,
        bg: str = "#d79a10",
        relief=tk.FLAT,
        **kwargs,
    ) -> TexturedFrame:
        """
        Create a default textured frame for the application.

        Returns:
            TexturedFrame: Default texture frame for the app.
        """

        return TexturedFrame(
            parent=parent,
            texture_path=texture_path,
            width=width,
            height=height,
            bd=bd,
            padx=padx,
            pady=pady,
            bg=bg,
            relief=relief,
            highlightthickness=highlightthickness,
            **kwargs,
        )

    def Label(
        self,
        parent,
        text: str = "",
        image_path: str | Path | None = None,
        font: tuple[str, int] | None = ("Skranji-Bold", 14),
        text_color: str = "white",
        font_dpi_scale: float = 96 / 72,
        compound: str = "left",
        padding: int = 6,
        width: int | None = None,
        height: int | None = None,
        image_size: tuple[int, int] | None = None,
        **kwargs,
    ) -> TransparentLabel:
        """
        Create a default transparent label for the application.

        Returns:
            TransparentLabel: Transparent label with text and/or image rendered via PIL.
        """

        return TransparentLabel(
            parent=parent,
            text=text,
            image_path=image_path,
            image_size=image_size,
            font=font,
            text_color=text_color,
            font_dpi_scale=font_dpi_scale,
            compound=compound,
            padding=padding,
            width=width,
            height=height,
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

        # Ensure account panel stays on top if it exists
        if hasattr(self, "account_panel") and self.account_panel:
            self.account_panel.lift()

    def _create_account_panel(self) -> None:
        """
        Create account info panel in top right corner (created once, reused across frames).
        """
        self.account_panel = ttk.Frame(self)

        self.wifi_signal = ttk.Label(
            self.account_panel,
            image=self.wifi_signal_icons[3] if self.name else self.wifi_signal_icons[0],  # type: ignore
            style="Account.TLabel",
            takefocus=False,
        )
        self.wifi_signal.pack(side=tk.RIGHT, padx=(5, 0))

        # Account info button
        initial_photo = self.get_profile_photo()
        self.account_profile_photo = ttk.Button(
            self.account_panel,
            text=(f"{self.name} " if self.name else f"{random_username()} "),
            image=initial_photo,
            command=self._show_account_dialog,
            compound=tk.RIGHT,
            takefocus=False,
            cursor="hand2",
            style="Account.TButton",
            padding=3,
        )
        self.account_profile_photo.pack(side=tk.RIGHT)
        # Keep reference to prevent garbage collection
        self.account_profile_photo.image = initial_photo  # type: ignore

    def apply_preferences(self) -> None:
        """
        Apply user preferences to the application.
        """

        # Ensure expected preference keys exist
        self.preferences.setdefault("stay_logged_in", True)
        self.preferences.setdefault("auth_token", None)

        # Apply sound preference
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

    def _start_token_verification(self) -> None:
        """Start token verification in a background thread."""
        token = self.preferences.get("auth_token")
        if token:
            thread = threading.Thread(
                target=lambda: asyncio.run(self._verify_token(token))
            )
            thread.start()

    def _on_token_verified(self, data: dict, token: str) -> None:
        """Called in main thread when token is verified."""
        self.username = data.get("username")
        self.token = token

        # Fetch full user data to get the name
        self._fetch_user_data()

        # Mark user as connected in database
        self._mark_user_connected()

        # Notify listeners that username and profile photo have been updated
        self.notify_username_updated()
        self.notify_profile_photo_updated()
        
        # Notify connection change (trigger callback if registered)
        self._update_wifi_signal()

    def _fetch_user_data(self) -> None:
        """Fetch user data from API to get the name."""
        if self.username:
            try:
                response = requests.get(
                    f"{BASE_URL}/users/{self.username}",
                    timeout=5,
                )
                if response.status_code == 200:
                    data = response.json()
                    self.name = data.get("name")
                    # Update account panel with real name
                    self.after(0, self._update_account_panel)
            except Exception as e:
                print(f"Error fetching user data: {e}")
                self.name = None

    def _update_account_panel(self) -> None:
        """Update account panel button text with current user info."""
        if (
            hasattr(self, "account_profile_photo")
            and self.account_profile_photo.winfo_exists()
        ):
            new_text = f"{self.name} " if self.name else f"{random_username()} "
            self.account_profile_photo.config(text=new_text)

    def _mark_user_connected(self) -> None:
        """Mark user as connected in the database."""
        if self.username:
            try:
                response = requests.post(
                    f"{BASE_URL}/users/{self.username}/connect",
                    timeout=5,
                )
                if response.status_code == 200:
                    print(f"User {self.username} marked as connected")
            except Exception as e:
                print(f"Error marking user as connected: {e}")

    def _on_token_invalid(self) -> None:
        """Called in main thread when token is invalid."""
        self.preferences["auth_token"] = None
        # Show login dialog since token is invalid
        self._show_login_dialog()

    def open_dialog(
        self,
        dialog: TopLevelWindow,
        frame_class: type[tk.Frame] | None = None,
        show_account_panel: bool = True,
    ) -> None:
        """
        Open a dialog window and optionally mount a frame inside.

        Args:
            dialog: An initialized TopLevelWindow instance
            frame_class: Optional frame class to display inside the dialog
            show_account_panel: Whether to display the account panel (default: True)
        """

        if frame_class is not None:
            frame = frame_class(dialog.body_frame, self)  # type: ignore
            frame.pack(fill=tk.BOTH, expand=True)

        # If account panel should be shown, display it
        if show_account_panel:
            self.account_panel.place(relx=0.98, rely=0.04, anchor="ne")
        else:
            # Otherwise, schedule to show it after dialog closes
            def show_panel_on_close():
                if dialog.winfo_exists():
                    # Dialog still exists, wait and check again
                    self.after(100, show_panel_on_close)
                else:
                    # Dialog has closed, show the panel
                    self.account_panel.place(relx=0.98, rely=0.04, anchor="ne")

            self.after(100, show_panel_on_close)

        dialog.show(wait=False)

    def _show_login_dialog(self) -> None:
        """
        Show the login dialog (called after mainloop is active).
        """

        self.open_dialog(TopLevelWindow(self, width=400, height=650), LoginFrame, show_account_panel=False)  # type: ignore

    def _show_login_dialog_if_needed(self) -> None:
        """
        Show login dialog only if user is still not logged in (fallback after token verification timeout).
        """

        if self.username is None or self.token is None:
            self._show_login_dialog()

    def get_profile_photo(self, size: int = 32) -> ImageTk.PhotoImage:
        """
        Get the user's profile photo as a PhotoImage.

        Returns:
            ImageTk.PhotoImage: The profile photo image.
        """

        # Try to load user's profile photo from the web API
        if self.username:
            try:
                response = requests.get(
                    f"{BASE_URL}/users/{self.username}/profile-picture/thumb",
                    timeout=5,
                )
                if response.status_code == 200:
                    image_data = response.content
                    if size:
                        image = Image.open(BytesIO(image_data)).resize(
                            (size, size), Image.Resampling.LANCZOS
                        )
                    else:
                        image = Image.open(BytesIO(image_data))
                    return ImageTk.PhotoImage(image)

            except Exception as e:
                pass

        return self._get_default_profile_photo()

    def _get_default_profile_photo(self) -> ImageTk.PhotoImage:
        """
        Get the default profile photo.

        Returns:
            ImageTk.PhotoImage: The default profile photo image.
        """

        images_dir = Path(__file__).parent / "images/profiles"
        default_photo_path = images_dir / "default_profile_photo.png"

        if default_photo_path.exists():
            return ImageTk.PhotoImage(
                Image.open(default_photo_path).resize(
                    (32, 32), Image.Resampling.LANCZOS
                )
            )
        else:
            # Create a blank image if default not found
            blank_image = Image.new("RGBA", (32, 32), (255, 255, 255, 0))
            return ImageTk.PhotoImage(blank_image)

    def _show_account_dialog(self) -> None:
        """
        Show the account dialog (called when clicking on profile photo).
        """

        print("Account dialog opened")

    def notify_username_updated(self) -> None:
        """
        Notify listeners that the username has been updated.
        """
        if self.username_updated_callback:
            self.username_updated_callback()

    def notify_profile_photo_updated(self) -> None:
        """
        Notify listeners that the profile photo has been updated.
        """
        if self.profile_photo_updated_callback:
            self.profile_photo_updated_callback()

    def _start_connection_monitor(self) -> None:
        """
        Start the connection monitoring thread.
        """
        monitor_thread = threading.Thread(
            target=self._monitor_connection_loop, daemon=True
        )
        monitor_thread.start()

    def _monitor_connection_loop(self) -> None:
        """
        Monitor connection status in background thread.
        Checks connection every 5 seconds and updates signal strength using WebSocket health endpoint.
        """
        import time
        import json

        while self._connection_monitor_running:

            # Only monitor if user is logged in
            if self.name is None:
                time.sleep(5)
                continue

            try:
                # Test connection with timeout using WebSocket health endpoint
                start_time = time.time()

                async def test_ws_health():
                    try:
                        import websockets

                        async with websockets.connect(
                            f"{WS_URL}/health", ping_interval=None, ping_timeout=None
                        ) as ws:
                            # Send ping message
                            await ws.send(json.dumps({"message": "ping"}))
                            # Wait for response
                            response = await asyncio.wait_for(ws.recv(), timeout=2.0)
                            return True
                    except Exception as e:
                        print(f"WebSocket health check error: {e}")
                        return False

                # Run async function in thread
                result = asyncio.run(test_ws_health())
                elapsed_time = time.time() - start_time

                if result:
                    # Determine signal strength based on response time
                    # Adjusted for realistic network latency
                    if elapsed_time < 1.5:
                        strength = 3  # Excellent (< 1.5s)
                    elif elapsed_time < 2.5:
                        strength = 2  # Good (1.5s - 2.5s)
                    elif elapsed_time < 3.5:
                        strength = 1  # Weak (2.5s - 3.5s)
                    else:
                        strength = 0  # Poor (> 3.5s)
                    print(f"Connection OK: {elapsed_time:.3f}s - Signal: {strength}")
                else:
                    strength = 0  # No connection
                    print(f"Connection FAILED")

            except Exception as e:
                # Connection failed
                strength = 0
                print(f"Monitor error: {e}")

            # Update UI in main thread if strength changed
            if strength != self._connection_strength:
                self._connection_strength = strength
                self.after(0, self._update_wifi_signal)

            # Wait before next check
            time.sleep(5)

    def _update_wifi_signal(self) -> None:
        """
        Update the WiFi signal icon in the account panel (called in main thread).
        """
        if hasattr(self, "wifi_signal") and self.wifi_signal.winfo_exists():
            if len(self.wifi_signal_icons) > self._connection_strength:
                self.wifi_signal.config(
                    image=self.wifi_signal_icons[self._connection_strength]
                )
        
        # Call connection strength callback (e.g., to disable online button)
        if self.connection_strength_callback:
            self.connection_strength_callback(self._connection_strength)

    def return_to_desktop(self) -> None:
        """
        Return to the desktop by closing the application.
        """

        result = messagebox.askyesno(
            "Quitter le jeu",
            "Voulez-vous retourner au bureau ?",
        )
        if result:
            # Stop connection monitor
            self._connection_monitor_running = False

            # Mark user as disconnected before closing
            if self.username:
                try:
                    requests.post(
                        f"{BASE_URL}/users/{self.username}/disconnect",
                        timeout=5,
                    )
                except Exception as e:
                    print(f"Error marking user as disconnected: {e}")

            save_dictionnary(self.preferences, "preferences.prefs")
            if self.current_game is not None:
                save_game(self.current_game, "saves/autosave.csgogame")
            else:
                try:
                    os.remove("saves/autosave.csgogame")
                except:
                    pass
            self.quit()
