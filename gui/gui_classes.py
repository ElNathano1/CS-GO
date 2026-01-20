import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox
import sys
from pathlib import Path
from PIL import Image, ImageTk

import pygame

import math
import random
import os

# Add parent directory to path to import goban
sys.path.insert(0, str(Path(__file__).parent.parent))
from gui.custom_tkinter_widgets import TexturedButton
from player.player_classes import Martin, Leo, Magnus
from game.game_classes import Goban, GoGame
from game.save_games import save_game
from gui.save_preferences import save_dictionnary


class SoundManager:
    """
    Manager for game sounds and music.

    Handles loading and playing sound effects for various game events.
    Uses pygame.mixer for cross-platform audio support.
    Falls back gracefully if pygame is not available.

    Attributes:
        enabled (bool): Whether sound is enabled.
        volume (float): Master volume level (0.0 to 1.0).
        sounds (dict): Dictionary storing loaded sound objects.
    """

    def __init__(self, enabled: bool = True):
        """
        Initialize the sound manager.

        Args:
            enabled (bool): Whether to enable sounds (default: True).
        """

        self.enabled = enabled
        self.volume = 0.7
        self.sounds = {}

        if self.enabled:
            try:
                pygame.mixer.init()
                self._load_sounds()
            except Exception as e:
                print(f"Warning: Could not initialize audio: {e}")
                self.enabled = False

    def _load_sounds(self) -> None:
        """
        Load all sound files from the assets directory.

        This method attempts to load sound files for various game events.
        If a file is not found, it continues without error.
        """

        sounds_dir = Path(__file__).parent / "sounds"

        # Define sound files for different events
        sound_files = {
            "background_music": "background_music.wav",
            "click_effect": "click.wav",
            "game_start_music": "game_start.wav",
            "stone_placed_effect": "stone_place.wav",
            "pass_effect": "pass.wav",
            "game_over_music": "game_over.wav",
            "invalid_move_effect": "invalid.wav",
            "capture_effect": "capture.wav",
            "resign_music": "resign.wav",
        }

        for event_name, filename in sound_files.items():
            sound_path = sounds_dir / filename
            try:
                if sound_path.exists():
                    self.sounds[event_name] = pygame.mixer.Sound(str(sound_path))
                    self.sounds[event_name].set_volume(self.volume)
            except Exception as e:
                print(f"Warning: Could not load {filename}: {e}")

    def play(self, event: str) -> None:
        """
        Play a sound effect for a game event.

        Args:
            event (str): The event name (e.g., 'stone_placed', 'pass', 'game_over').
        """

        if not self.enabled or event not in self.sounds:
            return

        try:
            self.sounds[event].play()
        except Exception as e:
            print(f"Warning: Could not play sound for {event}: {e}")

    def play_exclusive(self, event: str) -> None:
        """
        Play a sound effect for a game event, stopping any currently playing sound.

        Args:
            event (str): The event name (e.g., 'stone_placed', 'pass', 'game_over').
        """

        if not self.enabled or event not in self.sounds:
            return

        try:
            pygame.mixer.stop()  # Stop all currently playing sounds
            self.sounds[event].play()
        except Exception as e:
            print(f"Warning: Could not play exclusive sound for {event}: {e}")

    def stop(self, event: str) -> None:
        """
        Stop a sound effect for a game event.

        Args:
            event (str): The event name (e.g., 'stone_placed', 'pass', 'game_over').
        """

        if not self.enabled or event not in self.sounds:
            return

        try:
            self.sounds[event].stop()
        except Exception as e:
            print(f"Warning: Could not stop sound for {event}: {e}")

    def stop_all(self) -> None:
        """
        Stop all currently playing sounds.
        """

        if not self.enabled or not self.sounds:
            return

        try:
            for sound in self.sounds.values():
                sound.stop()
        except Exception as e:
            print(f"Warning: Could not stop sound: {e}")

    def set_volume(self, volume: float) -> None:
        """
        Set the master volume level.

        Args:
            volume (float): Volume level (0.0 to 1.0).
        """

        self.volume = max(0.0, min(1.0, volume))
        for sound in self.sounds.values():
            sound.set_volume(self.volume)

    def toggle(self) -> None:
        """
        Toggle sound on/off.
        """

        self.enabled = not self.enabled

    def is_enabled(self) -> bool:
        """
        Check if sound is enabled.

        Returns:
            bool: True if sound is enabled, False otherwise.
        """

        return self.enabled

    def is_playing(self, event: str) -> bool:
        """
        Check if a specific sound is currently playing.

        Args:
            event (str): The event name (e.g., 'stone_placed', 'pass', 'game_over').

        Returns:
            bool: True if the sound is currently playing, False otherwise.
        """

        if not self.enabled or event not in self.sounds:
            return False

        try:
            return self.sounds[event].get_volume() > 0 and pygame.mixer.get_busy()
        except Exception as e:
            print(f"Warning: Could not check if sound is playing for {event}: {e}")
            return False


class StoneBowl:
    """
    A class managing the drawing of progressivly emptiying stone bowls from which to draw
    animations to the goban.
    """

    def __init__(
        self,
        canvas: tk.Canvas,
        center: tuple[int, int],
        radius: int,
        stone_color: int,
        stone_image: ImageTk.PhotoImage,
        bowl_back: ImageTk.PhotoImage,
        bowl_front: ImageTk.PhotoImage,
        initial_count: int,
    ):
        """
        Initialize the StoneBowl.

        Args:
            canvas (tk.Canvas): The canvas where the bowl is drawn.
            center (tuple[int, int]): The (x, y) center of the bowl.
            radius (int): The radius of the bowl.
            stone_color (int): The color of the stones in the bowl.
            stone_image (ImageTk.PhotoImage): The image of the stone.
            bowl_back (ImageTk.PhotoImage): The image of the back of the bowl.
            bowl_front (ImageTk.PhotoImage): The image of the front of the bowl.
            initial_count (int): The initial number of stones in the bowl.
        """

        self.canvas = canvas
        self.cx, self.cy = center
        self.radius = radius
        self.color = stone_color
        self.stone_image = stone_image
        self.count = initial_count

        self.bowl_back = bowl_back
        self.bowl_front = bowl_front

        self.stone_items: list[int] = []
        self.stone_coordinates: list[tuple[float, float]] = []

        self._generate_coordinates()

    def draw(self):
        """
        Draw the stone bowl on the canvas.
        """

        # Back of the bowl
        self.canvas.create_image(
            self.cx, self.cy, image=self.bowl_back, anchor="center", tags=("bowls",)
        )

        # Stones inside the bowl
        self._draw_stones()

        # Border/front of the bowl
        self.canvas.create_image(
            self.cx, self.cy, image=self.bowl_front, anchor="center"
        )

    def _generate_coordinates(self):
        """
        Generate random coordinates where to draw the stones
        """

        max_radius = self.radius - self.stone_image.height() / 2

        for _ in range(self.count):
            angle = random.uniform(0, 2 * 3.14159)
            r = random.uniform(0, max_radius)

            x = self.cx + r * math.cos(angle)
            y = self.cy + r * math.sin(angle)

            self.stone_coordinates.append((x, y))

    def _draw_stones(self):
        """
        Draw stones inside the bowl at random positions.
        """

        for i in range(self.count):
            x, y = self.stone_coordinates[i]
            w = self.stone_image.width()
            h = self.stone_image.height()

            item = self.canvas.create_image(
                x - w // 2,
                y - h // 2,
                image=self.stone_image,
                anchor="nw",
            )
            self.stone_items.append(item)

    def pop_stone(self) -> tuple[float, float] | None:
        """
        Remove and return the position of a stone from the bowl.

        Returns:
            tuple[float, float] | None: The (x, y) position of the removed stone, or None if no stones left.
        """

        if self.count <= 0 or not self.stone_items:
            return None

        item = self.stone_items.pop()
        self.count -= 1

        x, y = self.canvas.coords(item)
        self.canvas.delete(item)

        return x, y

    def pop_stone_item(self) -> int | None:
        """
        Remove and return a canvas item representing a stone.

        Returns:
            int | None: The canvas item ID of the removed stone, or None if no stones left.
        """

        if self.count <= 0 or not self.stone_items:
            return None

        self.count -= 1
        return self.stone_items.pop()


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

    def __init__(self, preferences: dict, current_game: GoGame | None = None):
        """
        Initialize the main application window.

        Args:
            preferences (dict): User preferences for the application.
            current_game (GoGame, optional): The current game instance for resuming later. Defaults to None.
        """

        super().__init__()

        self.title("CS Go")
        self.resizable(True, True)

        # Initialize sound manager
        self.sound_manager = SoundManager()

        # Store and apply preferences
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

        # Center window on screen
        self.update_idletasks()
        self._center_window()

        # Save current game state for resuming later
        self.current_game = current_game

        # Show lobby frame on startup
        self.show_frame(LobbyFrame)

        # Bind the click sound to all button clicks, except for placing stones and passing
        self.bind_all("<Button-1>", self._on_global_click, add="+")

        # Replace the default close behavior to save preferences
        self.protocol("WM_DELETE_WINDOW", self.return_to_desktop)

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

        # Apply sound preference
        if self.preferences["sound_enabled"]:
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

        # Fullscreen preference
        if self.preferences["fullscreen"]:
            self.attributes("-fullscreen", True)
        else:
            self.attributes("-fullscreen", False)
            self.wm_state(newstate="zoomed")

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


class LobbyFrame(ttk.Frame):
    """
    Frame for initiating a lobby.

    Allows the user to start a new game, consult the game rules and go to parameters.
    """

    def __init__(self, parent: ttk.Frame, app: App):
        """
        Initialize the lobby frame.

        Args:
            parent (ttk.Frame): The parent frame.
            app (App): The main application instance.
        """

        super().__init__(parent)

        self.app = app

        # Play background music if sound is not already playing
        if (
            self.app.sound_manager.is_enabled()
            and not self.app.sound_manager.is_playing("background_music")
        ):
            self.app.sound_manager.play_exclusive("background_music")

        # Title
        title = ttk.Label(
            self, text="CS Go", font=("Arial", 24, "bold"), background="#f0f0f0"
        )
        title.pack(pady=(40, 20))

        # Options frame
        option_frame = ttk.LabelFrame(self, padding=20)
        option_frame.pack(pady=20)

        # Buttons for different options
        self.app.Button(
            option_frame,
            text="Continuer la partie",
            command=lambda: self._resume_game(game=self.app.current_game),  # type: ignore
            disabled=True if self.app.current_game is None else False,
            takefocus=False,
        ).pack(pady=10, fill=tk.X)
        self.app.Button(
            option_frame,
            text="Nouvelle partie",
            command=lambda: self._open_game(),
            takefocus=False,
        ).pack(pady=10, fill=tk.X)
        self.app.Button(
            option_frame,
            overlay_path=self.app.prefs_icon_path,
            text="Paramètres",
            command=lambda: self._open_settings(),
            takefocus=False,
        ).pack(pady=10, fill=tk.X)
        self.app.Button(
            option_frame,
            overlay_path=self.app.rules_icon_path,
            text="Règles du jeu",
            command=lambda: self._open_rules(),
            takefocus=False,
        ).pack(pady=10, fill=tk.X)

        # Return to Desktop button
        self.app.Button(
            option_frame,
            overlay_path=self.app.return_icon_path,
            text="Retour au bureau",
            command=lambda: self.app.return_to_desktop(),
            takefocus=False,
        ).pack(pady=10, fill=tk.X)

    def _open_game(self) -> None:
        """
        Open the game starting window.

        Args:
            game (GoGame, optional): The game instance to resume. Defaults to None.
        """

        self.app.show_frame(lambda parent, app: GameLobbyFrame(parent, app))

    def _resume_game(self, game: GoGame) -> None:
        """
        Resume an existing game.

        Args:
            game (GoGame): The game instance to resume.
        """

        board_size = game.goban.size
        if not game.singleplayer:
            self.app.show_frame(
                lambda parent, app: GameFrame(parent, app, board_size, game)
            )
        else:
            self.app.show_frame(
                lambda parent, app: SingleplayerGameFrame(parent, app, board_size, game)
            )

    def _open_settings(self) -> None:
        """
        Open settings window.
        """

        self.app.show_frame(lambda parent, app: SettingsFrame(parent, app))

    def _open_rules(self) -> None:
        """
        Open game rules window.
        """

        rules_text = (
            "Règles du jeu de Go:\n\n"
            "1. Le jeu se joue sur une grille de 9x9, 13x13 ou 19x19 intersections.\n"
            "2. Deux joueurs (Noir et Blanc) placent alternativement des pierres sur les intersections.\n"
            "3. L'objectif est de contrôler le plus de territoire en encerclant des zones.\n"
            "4. Les pierres entourées sans libertés sont capturées et retirées du plateau.\n"
            "5. Le jeu se termine lorsque les deux joueurs passent consécutivement.\n"
            "6. Le score est calculé en fonction du territoire contrôlé et des pierres capturées.\n\n"
            "Pour plus de détails, consultez les règles officielles du jeu de Go."
        )

        messagebox.showinfo("Règles du jeu", rules_text)


class SettingsFrame(ttk.Frame):
    """
    Frame for application settings.

    Allows the user to adjust sound settings and other preferences.
    """

    def __init__(self, parent: ttk.Frame, app: App):
        """
        Initialize the settings frame.

        Args:
            parent (ttk.Frame): The parent frame.
            app (App): The main application instance.
        """

        super().__init__(parent)

        self.app = app

        # Title
        title = ttk.Label(
            self, text="Paramètres", font=("Arial", 24, "bold"), background="#f0f0f0"
        )
        title.pack(pady=(40, 20))

        # Sound options frame
        option_frame = ttk.LabelFrame(self, padding=20)
        option_frame.pack(pady=20)

        # Sound settings
        self.sound_enabled = tk.BooleanVar(value=self.app.preferences["sound_enabled"])
        sound_enabled = ttk.Checkbutton(
            option_frame,
            text="Activer le son",
            variable=self.sound_enabled,
            takefocus=False,
        )
        sound_enabled.pack(pady=10, fill=tk.X)

        # Volume controls
        master_volume_frame = ttk.Frame(option_frame)
        master_volume_frame.pack(pady=10, fill=tk.X)

        ttk.Label(master_volume_frame, text="Volume principal:").pack()
        self.master_volume_slider = ttk.Scale(
            master_volume_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            variable=tk.IntVar(value=self.app.preferences["master_volume"]),
            takefocus=False,
        )
        self.master_volume_slider.pack(fill=tk.X, expand=True)

        music_volume_frame = ttk.Frame(option_frame)
        music_volume_frame.pack(pady=10, fill=tk.X)

        ttk.Label(music_volume_frame, text="Volume de la musique:").pack()
        self.music_volume_slider = ttk.Scale(
            music_volume_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            variable=tk.IntVar(value=self.app.preferences["music_volume"]),
            takefocus=False,
        )
        self.music_volume_slider.pack(fill=tk.X, expand=True)

        effects_volume_frame = ttk.Frame(option_frame)
        effects_volume_frame.pack(pady=10, fill=tk.X)
        ttk.Label(effects_volume_frame, text="Volume des effets:").pack()
        self.effects_volume_slider = ttk.Scale(
            effects_volume_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            variable=tk.IntVar(value=self.app.preferences["effects_volume"]),
            takefocus=False,
        )
        self.effects_volume_slider.pack(fill=tk.X, expand=True)

        # Return to Lobby button
        self.app.Button(
            self,
            text="Retour au Lobby",
            overlay_path=self.app.return_icon_path,
            command=lambda: self.app.show_frame(LobbyFrame),
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


class GameLobbyFrame(ttk.Frame):
    """
    Frame for game lobby before starting a game.

    Allows the user to select game options before starting the game.
    """

    def __init__(self, parent: ttk.Frame, app: App):
        """
        Initialize the game lobby frame.

        Args:
            parent (ttk.Frame): The parent frame.
            app (App): The main application instance.
        """

        super().__init__(parent)

        self.app = app

        self.board_size = tk.IntVar(value=19)
        self.multiplayer = tk.BooleanVar(value=True)
        self.ai = None

        # Title
        title = ttk.Label(
            self, text="Game Lobby", font=("Arial", 24, "bold"), background="#f0f0f0"
        )
        title.pack(pady=(40, 20))

        # Number of players selection frame
        player_frame = ttk.LabelFrame(self, padding=20)
        player_frame.pack(pady=20)

        # Buttons for number of players
        ttk.Radiobutton(
            player_frame,
            text="Un joueur (contre IA)",
            variable=self.multiplayer,
            value=False,
            takefocus=False,
        ).pack(pady=10, fill=tk.X)
        ttk.Radiobutton(
            player_frame,
            text="Deux joueurs (local)",
            variable=self.multiplayer,
            value=True,
            takefocus=False,
        ).pack(pady=10, fill=tk.X)

        # Board size selection frame
        size_frame = ttk.LabelFrame(self, padding=20)
        size_frame.pack(pady=20)

        # Buttons for different board sizes
        ttk.Radiobutton(
            size_frame,
            text="9x9",
            variable=self.board_size,
            value=9,
            takefocus=False,
        ).pack(pady=10, fill=tk.X)
        ttk.Radiobutton(
            size_frame,
            text="13x13",
            variable=self.board_size,
            value=13,
            takefocus=False,
        ).pack(pady=10, fill=tk.X)
        ttk.Radiobutton(
            size_frame,
            text="19x19",
            variable=self.board_size,
            value=19,
            takefocus=False,
        ).pack(pady=10, fill=tk.X)

        # Start Game button
        self.app.Button(
            self,
            text="Démarrer la partie",
            command=self._start_game,
            takefocus=False,
        ).pack(pady=20)

        # Return to Lobby button
        self.app.Button(
            self,
            text="Retour au Lobby",
            overlay_path=self.app.return_icon_path,
            command=lambda: self.app.show_frame(LobbyFrame),
            takefocus=False,
        ).pack(pady=20)

    def _start_game(self) -> None:
        """
        Start a new game with the selected board size.

        Args:
            board_size (int): The size of the board (9, 13, or 19).
            multiplayer (bool): Whether the game is multiplayer. Defaults to True.
            ai (int | None): The AI difficulty level if applicable. Defaults to None.
        """

        if self.multiplayer.get():
            self.app.show_frame(
                lambda parent, app: GameFrame(parent, app, self.board_size.get())
            )

        if not self.multiplayer.get():
            self.app.show_frame(
                lambda parent, app: SingleplayerGameFrame(
                    parent, app, self.board_size.get()
                )
            )


class GameFrame(ttk.Frame):
    """
    Frame for actually playing the game.

    Handles the game board display, controls, and game state updates.
    """

    def __init__(
        self, parent: ttk.Frame, app: App, board_size: int, game: GoGame | None = None
    ):
        """
        Initialize the game frame.

        Args:
            parent (ttk.Frame): The parent frame.
            app (App): The main application instance.
            board_size (int): The size of the board (9, 13, or 19).
            game (GoGame, optional): An existing game instance to resume. Defaults to None.
        """
        super().__init__(parent)

        self.app = app
        self.board_size = board_size
        self.sound_manager = app.sound_manager
        self.cell_size = 50
        self.stone_size = self.cell_size // 2 - 2
        self.last_move = None
        self.border_pixels_resized = 0  # Will be set in _load_images()

        # Manage the animations
        self.animating = False

        # Initialize the game
        self.game = GoGame(board_size) if game is None else game

        # Load images
        self._load_images()

        # Create layout
        self._create_layout()

        # Play game start sound
        self.sound_manager.play_exclusive("game_start_music")

        # Resume game if provided
        if game is not None:
            self._resume_game()

    def _load_images(self) -> None:
        """
        Load the goban and stone images from the images directory.

        Dynamically calculates cell_size based on window size and board size.
        The grid on the image is 1800 pixels, so each cell on the image is:
        1800 // (board_size - 1)

        Important: Each goban image has a 100-pixel border that needs to be accounted for.
        The full image is 2000x2000 pixels (100 border + 1800 grid + 100 border).
        """
        images_dir = Path(__file__).parent / "images/board"

        # Original image dimensions and border
        self.border_pixels_original = 105  # 100-pixel border on the original image
        self.image_grid_size = 1800  # The grid on the image is 1800 pixels
        self.image_total_size = 2010  # Total image size (border + grid + border)

        # Get available window width and height
        self.app.update_idletasks()
        available_width = (
            self.app.winfo_width() - 710
        )  # Leave space for controls - Found experimentally
        available_height = self.app.winfo_height() - 100  # Leave space for padding

        # Fixed board size: calculate based on available space
        # The full image is 2010x2010 pixels (105 border + 1800 grid + 105 border)
        # We want to maximize the board size while fitting in available space
        max_board_size = min(available_width, available_height)

        # Use a reasonable minimum/maximum
        board_size_px = max(300, min(900, max_board_size))

        # Now calculate cell_size based on board_size and the grid size (1800 pixels)
        # The grid has (board_size - 1) cells
        # So: cell_size = 1800 / (board_size - 1)
        cell_size_original = self.image_grid_size / (self.board_size - 1)

        # Calculate the scale ratio: how much the image will be resized
        # scale_ratio = final_size / original_size
        # We want the final board to be board_size_px pixels
        # Original board size is 2010 pixels
        self.scale_ratio = board_size_px / self.image_total_size

        # Recalculate cell_size after scaling (keep as float for precision)
        self.cell_size = cell_size_original * self.scale_ratio

        # Calculate actual board dimensions (full image with border)
        board_width = board_size_px
        board_height = board_size_px

        # Calculate the border size on the resized image
        self.border_pixels_resized = self.border_pixels_original * self.scale_ratio

        # Load goban image
        goban_path = images_dir / f"{self.board_size}x{self.board_size}_goban.png"
        if goban_path.exists():
            goban_img = Image.open(goban_path)
            # Resize goban to calculated dimensions (full image with border)
            goban_img = goban_img.resize(
                (board_width, board_height), Image.Resampling.LANCZOS
            )
            self.goban_photo = ImageTk.PhotoImage(goban_img)

        # Load black stone image
        black_stone_path = images_dir / "black_stone.png"
        if black_stone_path.exists():
            black_stone_img = Image.open(black_stone_path)
            # Resize stone to match cell size with a margin
            stone_size = int(self.cell_size * 0.85)  # 85% of cell size for margin
            black_stone_img = black_stone_img.resize(
                (stone_size, stone_size), Image.Resampling.LANCZOS
            )
            self.black_stone_photo = ImageTk.PhotoImage(black_stone_img)
            self.stone_size = stone_size

        # Load white stone image
        white_stone_path = images_dir / "white_stone.png"
        if white_stone_path.exists():
            white_stone_img = Image.open(white_stone_path)
            # Resize stone to match cell size with a margin
            stone_size = int(self.cell_size * 0.85)  # 85% of cell size for margin
            white_stone_img = white_stone_img.resize(
                (stone_size, stone_size), Image.Resampling.LANCZOS
            )
            self.white_stone_photo = ImageTk.PhotoImage(white_stone_img)

        # Load bowl images
        bowl_back_path = images_dir / "bowl.png"
        bowl_front_path = images_dir / "bowl_border.png"
        if bowl_back_path.exists() and bowl_front_path.exists():
            bowl_back_img = Image.open(bowl_back_path)
            bowl_front_img = Image.open(bowl_front_path)
            bowl_size = int(board_size_px / 4)  # Bowl size relative to board size
            bowl_back_img = bowl_back_img.resize(
                (bowl_size, bowl_size), Image.Resampling.LANCZOS
            )
            bowl_front_img = bowl_front_img.resize(
                (bowl_size, bowl_size), Image.Resampling.LANCZOS
            )
            self.bowl_back_photo = ImageTk.PhotoImage(bowl_back_img)
            self.bowl_front_photo = ImageTk.PhotoImage(bowl_front_img)

    def _create_bowls(self) -> None:
        """
        Place the stone bowls on the canvas.
        """

        board_width = int(self.image_total_size * self.scale_ratio)
        board_height = int(self.image_total_size * self.scale_ratio)

        bowl_size = int(board_width / 4)
        margin = bowl_size + 20

        canvas_width = board_width + margin * 2
        canvas_height = board_height

        # Center of the two bowls
        white_bowl_center = (
            bowl_size // 2,
            bowl_size // 2,
        )
        black_bowl_center = (
            canvas_width - bowl_size // 2,
            canvas_height - bowl_size // 2,
        )

        # Bowls
        self.white_bowl = StoneBowl(
            canvas=self.canvas,
            center=white_bowl_center,
            radius=bowl_size // 2,
            stone_color=Goban.WHITE,
            stone_image=self.white_stone_photo,  # type: ignore
            bowl_back=self.bowl_back_photo,
            bowl_front=self.bowl_front_photo,
            initial_count=self.board_size**2,
        )

        self.black_bowl = StoneBowl(
            canvas=self.canvas,
            center=black_bowl_center,
            radius=bowl_size // 2,
            stone_color=Goban.BLACK,
            stone_image=self.black_stone_photo,  # type: ignore
            bowl_back=self.bowl_back_photo,
            bowl_front=self.bowl_front_photo,
            initial_count=self.board_size**2,
        )

    def _create_layout(self) -> None:
        """
        Create the layout for the game frame.
        """

        # Main container
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Left side: Game board
        board_frame = ttk.LabelFrame(main_frame, padding=20)
        board_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Create canvas for drawing the board using calculated dimensions
        board_width = int(self.image_total_size * self.scale_ratio)
        board_height = int(self.image_total_size * self.scale_ratio)
        bowl_size = int(board_width / 4)
        margin = bowl_size + 20

        canvas_width = board_width + margin * 2
        canvas_height = board_height

        self.canvas = tk.Canvas(
            board_frame,
            width=canvas_width,
            height=canvas_height,
            relief=tk.SOLID,
            bd=0,
            highlightthickness=0,  # Remove canvas border highlight
        )
        self.canvas.pack(anchor="center", expand=True)
        self.canvas.bind("<Button-1>", self._on_board_click)

        # Origin for drawing the board
        self.board_origin_x = margin
        self.board_origin_y = 0

        # Create bowls
        self._create_bowls()

        # Right side: Controls and info panel
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(10, 0))

        # Game status frame
        status_frame = ttk.LabelFrame(right_frame, padding=20)
        status_frame.pack(fill=tk.X, pady=(0, 10))

        # Current player display
        self.player_label = ttk.Label(status_frame, text=self._get_player_text())
        self.player_label.pack(pady=5)

        # Move count display
        self.moves_label = ttk.Label(status_frame, text="Aucun coup joué")
        self.moves_label.pack(pady=5)

        # Control buttons frame
        buttons_frame = ttk.LabelFrame(right_frame, padding=20)
        buttons_frame.pack(fill=tk.X, pady=(0, 10))

        # Pass button
        self.pass_button = self.app.Button(
            buttons_frame,
            text="Passer",
            overlay_path=self.app.pass_icon_path,
            command=lambda: self._on_pass(),
            takefocus=False,
        )
        self.pass_button.pack(fill=tk.X, pady=3)

        # Resign button
        self.resign_button = self.app.Button(
            buttons_frame,
            text="Abandon",
            overlay_path=self.app.resign_icon_path,
            command=lambda: self._on_resign(),
            takefocus=False,
        )
        self.resign_button.pack(fill=tk.X, pady=3)

        # New game button
        self.new_game_button = self.app.Button(
            buttons_frame,
            text="Revanche",
            overlay_path=self.app.revenge_icon_path,
            command=lambda: self._on_new_game(),
            takefocus=False,
        )
        self.new_game_button.pack(fill=tk.X, pady=3)

        # Back to Lobby button
        self.back_button = self.app.Button(
            buttons_frame,
            text="Retour au lobby",
            overlay_path=self.app.return_icon_path,
            command=lambda: self._on_back_to_lobby(),
            takefocus=False,
        )
        self.back_button.pack(fill=tk.X, pady=3)

        # Draw the initial board state
        self._draw_board()
        self.app.current_game = self.game

    def _draw_board(self) -> None:
        """
        Draw the Go board with grid lines and stones.
        """

        self.canvas.delete("background")
        self.canvas.delete("bowls")
        self.canvas.delete("stones")
        self.canvas.delete("overlay")

        # Draw goban image as background
        # Position image at (board_origin, board_origin) - image already includes border
        self.canvas.create_image(
            self.board_origin_x,
            self.board_origin_y,
            image=self.goban_photo,
            anchor="nw",
            tags=("background",),
        )

        # Draw bowls
        self.white_bowl.draw()
        self.black_bowl.draw()

        # Draw stones
        for x in range(self.board_size):
            for y in range(self.board_size):
                if self.game.goban.board[x, y] != Goban.EMPTY:
                    self._draw_stone(x, y, self.game.goban.board[x, y])

        self.canvas.tag_raise("stones")
        self.canvas.tag_raise("overlay")

    def _draw_stone(self, x: int, y: int, color: int) -> None:
        """
        Draw a single stone on the board.

        Args:
            x (int): The x-coordinate (row) of the stone.
            y (int): The y-coordinate (column) of the stone.
            color (int): The stone color (Goban.BLACK=1 or Goban.WHITE=2).
        """
        cx = self.board_origin_x + self.border_pixels_resized + y * self.cell_size
        cy = self.board_origin_y + self.border_pixels_resized + x * self.cell_size

        image = (
            self.black_stone_photo if color == Goban.BLACK else self.white_stone_photo
        )

        self.canvas.create_image(
            cx,
            cy,
            image=image,
            anchor="center",
            tags=("stones",),
        )

    def _highlight_last_move(self) -> None:
        """
        Highlight the last move played on the board with a small square.
        """
        if self.last_move:
            x, y = self.last_move
            cx = self.board_origin_x + self.border_pixels_resized + y * self.cell_size
            cy = self.board_origin_y + self.border_pixels_resized + x * self.cell_size
            marker_size = 4
            self.canvas.delete("overlay")
            self.canvas.create_rectangle(
                cx - marker_size,
                cy - marker_size,
                cx + marker_size,
                cy + marker_size,
                outline="red",
                width=2,
                tags=("overlay",),
            )

    def _animate_pass(self, steps: int = 40, delay: int = 20) -> None:
        """
        Animate a pass action.
        """

        self.animating = True
        self.canvas.delete("overlay")

        def step(i: int = 0):
            if i >= steps:
                self._draw_board()
                self.sound_manager.play_exclusive("pass_effect")
                self._update_display()
                self.animating = False
                return

            t = i / steps
            # Simple animation effect (e.g., fade in/out)
            alpha = 1 - abs(t - 0.5) * 2
            self.canvas.delete("overlay")
            self.canvas.create_rectangle(
                self.board_origin_x + self.border_pixels_resized,
                self.board_origin_y + self.border_pixels_resized,
                self.board_origin_x
                + self.border_pixels_resized
                + (self.board_size - 1) * self.cell_size,
                self.board_origin_y
                + self.border_pixels_resized
                + (self.board_size - 1) * self.cell_size,
                outline="red",
                width=2,
                tags=("overlay",),
            )
            # Schedule next step
            self.after(delay, lambda: step(i + 1))

        step()

    def _animate_stone(
        self,
        item: int,
        target: tuple[float, float],
        steps: int = 40,
        delay: int = 20,
        capture: bool = False,
    ) -> None:
        """
        Animate a stone canvas item toward a target position.
        """

        x0, y0 = self.canvas.coords(item)
        x1, y1 = target

        def ease_out(t: float) -> float:
            return 1 - (1 - t) ** 3

        self.animating = True
        self.canvas.tag_raise(item)

        def step(i: int = 0):
            if i >= steps:
                self.canvas.coords(item, x1, y1)
                self.canvas.delete(item)

                self._draw_stone(*self.last_move, self.game.goban.board[self.last_move])  # type: ignore

                if capture:
                    self._draw_board()
                    self.sound_manager.play_exclusive("capture_effect")
                else:
                    self.sound_manager.play_exclusive("stone_placed_effect")

                self._update_display()

                self.animating = False
                return

            t = ease_out(i / steps)
            nx = x0 + (x1 - x0) * t
            ny = y0 + (y1 - y0) * t

            self.canvas.coords(item, nx, ny)
            self.after(delay, lambda: step(i + 1))

        step()

    def _intersection_coords(self, x: int, y: int) -> tuple[float, float]:
        """
        Get the canvas coordinates of a board intersection.

        Args:
            x (int): The x-coordinate (row) of the intersection.
            y (int): The y-coordinate (column) of the intersection.

        Returns:
            tuple[float, float]: The (cx, cy) canvas coordinates of the intersection.
        """
        cx = self.board_origin_x + self.border_pixels_resized + y * self.cell_size
        cy = self.board_origin_y + self.border_pixels_resized + x * self.cell_size

        w = self.black_stone_photo.width()  # type: ignore
        h = self.black_stone_photo.height()  # type: ignore

        return cx - w // 2, cy - h // 2

    def _on_board_click(self, event: tk.Event) -> None:
        """
        Handle mouse clicks on the board.

        Args:
            event (tk.Event): The click event containing mouse coordinates.
        """

        # Check if an animation is running
        if self.animating:
            return

        # Subtract the border offset to get position within the grid
        # Then divide by cell_size to get the grid position
        # The intersections are at: border + i * cell_size for i = 0 to board_size-1
        grid_x = (
            event.x - self.border_pixels_resized - self.board_origin_x
        ) / self.cell_size
        grid_y = (
            event.y - self.border_pixels_resized - self.board_origin_y
        ) / self.cell_size

        # Round to nearest intersection
        y = round(grid_x)
        x = round(grid_y)

        # Validate coordinates are within board bounds
        if 0 <= x < self.board_size and 0 <= y < self.board_size:
            successfull, capture = self.game.take_move(x, y)
            if successfull:
                self.last_move = (x, y)

                bowl = (
                    self.black_bowl
                    if self.game.current_color == Goban.WHITE
                    else self.white_bowl
                )
                item = bowl.pop_stone_item()

                if item:
                    target = self._intersection_coords(x, y)
                    self.last_move = (x, y)
                    self._animate_stone(item, target, capture=capture)
                else:
                    self._draw_stone(x, y, self.game.goban.board[x, y])
                    if capture:
                        self._draw_board()
                        self.sound_manager.play_exclusive("capture_effect")
                    else:
                        self.sound_manager.play_exclusive("stone_placed_effect")
                    self._update_display()

                # Check if game is over
                if self.game.game_over():
                    self._show_game_over_dialog()
            else:
                # Play invalid move sound
                self.sound_manager.play_exclusive("invalid_move_effect")

    def _on_pass(self) -> None:
        """
        Handle the Pass button click.

        Records a pass move and updates the display.
        """
        self.game.pass_move()
        # Play pass sound
        self.sound_manager.play_exclusive("pass_effect")
        self._update_display()

        # Check if game is over after pass
        if self.game.game_over():
            self._show_game_over_dialog()

    def _on_new_game(self) -> None:
        """
        Handle the New Game button click.

        Resets the game to the starting position with an empty board.
        """
        result = messagebox.askyesno(
            "Revanche",
            "Voulez-vous commencer une nouvelle partie avec la même taille de plateau ?",
        )
        if result:
            self.app.show_frame(
                lambda parent, app: GameFrame(parent, app, self.board_size)
            )

    def _on_resign(self) -> None:
        """
        Handle the Resign button click.

        Allows the current player to resign and end the game.
        """
        current_player = (
            "les Noirs" if self.game.current_color == Goban.BLACK else "les Blancs"
        )
        opponent = (
            "Les Blancs" if self.game.current_color == Goban.BLACK else "Les Noirs"
        )

        result = messagebox.askyesno(
            "Abandon",
            f"Êtes-vous sûr que {current_player} veut abandonner ?\n\n{opponent} gagnera la partie !",
        )

        if result:
            self.sound_manager.play_exclusive("resign_music")
            self._show_game_over_dialog(resigned_by=self.game.current_color)

    def _on_back_to_lobby(self) -> None:
        """
        Handle the Back to Lobby button click.

        Returns to the lobby screen.
        """
        result = messagebox.askyesno(
            "Retour au lobby", "Êtes-vous sûr de vouloir retourner au lobby ?"
        )
        if result:
            self.app.show_frame(LobbyFrame)

    def _update_display(self) -> None:
        """
        Update all GUI elements to reflect the current game state.

        Redraws the board and updates labels for player, moves, and scores.
        """
        self._highlight_last_move()
        self.player_label.config(text=self._get_player_text())
        self.moves_label.config(
            text=(
                f"{self.game.nbr_moves} coup joué"
                if self.game.nbr_moves == 1
                else f"{self.game.nbr_moves} coups joués"
            )
        )

        # Save current game state to app for resuming later
        self.app.current_game = self.game  # type: ignore

    def _resume_game(self) -> None:
        """
        Resume the game by redrawing the board and updating the display.
        """
        self._draw_board()
        self.player_label.config(text=self._get_player_text())
        self.moves_label.config(
            text=(
                f"{self.game.nbr_moves} coup joué"
                if self.game.nbr_moves == 1
                else f"{self.game.nbr_moves} coups joués"
            )
        )

    def _get_player_text(self) -> str:
        """
        Get a formatted string showing the current player.

        Returns:
            str: A formatted string like "Aux Noirs de jouer".
        """
        color = " Aux Noirs" if self.game.current_color == Goban.BLACK else "Aux Blancs"
        return f"{color} de jouer"

    def _show_game_over_dialog(self, resigned_by: int | None = None) -> None:
        """
        Display the game-over dialog with scores and winner information.

        Args:
            resigned_by (int, optional): If set, indicates which color resigned.
        """

        black_score = self.game.get_score()[Goban.BLACK]
        white_score = self.game.get_score()[Goban.WHITE]

        if resigned_by is not None:
            winner = "Les Noirs" if resigned_by == Goban.WHITE else "Les Blancs"
            message = f"{winner} gagnent par abandon !"
        else:
            if black_score > white_score:
                winner = "Les Noirs"
                margin = black_score - white_score
                message = f"Les Noirs gagnent avec une avance de {margin} points !"
            elif white_score > black_score:
                winner = "Les Blancs"
                margin = white_score - black_score
                message = f"Les Blancs gagnent avec une avance de {margin} points !"
            else:
                winner = None
                message = "Egalité !"

        # Play game over sound if not resigned
        if resigned_by is None:
            self.sound_manager.play_exclusive("game_over_music")

        # Show detailed score
        score_details = f"\nNoirs: {black_score}\nBlancs: {white_score}"
        messagebox.showinfo("Fin de la partie !", message + score_details)

        # Lock further moves
        self.canvas.unbind("<Button-1>")
        self.pass_button.config(state=tk.DISABLED)
        self.resign_button.config(state=tk.DISABLED)

        # No current game to continue
        self.app.current_game = None


class SingleplayerGameFrame(GameFrame):
    """
    Frame for actually playing the single player game.

    Handles the game board display, controls, and game state updates.
    """

    def __init__(
        self, parent: ttk.Frame, app: App, board_size: int, game: GoGame | None = None
    ):
        """
        Initialize the game frame.

        Args:
            parent (ttk.Frame): The parent frame.
            app (App): The main application instance.
            board_size (int): The size of the board (9, 13, or 19).
            game (GoGame, optional): An existing game instance to resume. Defaults to None.
        """
        super().__init__(parent, app, board_size, game)

        self.game.set_singleplayer(Goban.BLACK, -2)
        match self.game.ai_id:
            case -1:
                self.ai = Martin(self.game, Goban.BLACK)
            case -2:
                self.ai = Leo(self.game, Goban.BLACK)
            case -3:
                self.ai = Magnus(self.game, Goban.BLACK)
            case _:
                self.ai = Martin(self.game, Goban.BLACK)

        self.after(100, self._ai_move)

    def _create_bowls(self) -> None:
        """
        Place the stone bowls on the canvas.
        """

        board_width = int(self.image_total_size * self.scale_ratio)
        board_height = int(self.image_total_size * self.scale_ratio)

        bowl_size = int(board_width / 4)
        margin = bowl_size + 20

        canvas_width = board_width + margin * 2
        canvas_height = board_height

        # Center of the two bowls
        black_bowl_center = (
            bowl_size // 2,
            bowl_size // 2,
        )
        white_bowl_center = (
            canvas_width - bowl_size // 2,
            canvas_height - bowl_size // 2,
        )

        # Bowls
        self.white_bowl = StoneBowl(
            canvas=self.canvas,
            center=white_bowl_center,
            radius=bowl_size // 2,
            stone_color=Goban.WHITE,
            stone_image=self.white_stone_photo,  # type: ignore
            bowl_back=self.bowl_back_photo,
            bowl_front=self.bowl_front_photo,
            initial_count=self.board_size**2,
        )

        self.black_bowl = StoneBowl(
            canvas=self.canvas,
            center=black_bowl_center,
            radius=bowl_size // 2,
            stone_color=Goban.BLACK,
            stone_image=self.black_stone_photo,  # type: ignore
            bowl_back=self.bowl_back_photo,
            bowl_front=self.bowl_front_photo,
            initial_count=self.board_size**2,
        )

    def _on_pass(self) -> None:
        """
        Handle the Pass button click.

        Records a pass move and updates the display.
        """

        if self.game.current_color == Goban.WHITE:
            super()._on_pass()

            if not self.game.game_over():
                # Wait for animation to complete before letting AI play
                self._wait_and_play_ai()

    def _on_new_game(self) -> None:
        """
        Handle the New Game button click.

        Resets the game to the starting position with an empty board.
        """
        result = messagebox.askyesno(
            "Revanche",
            "Voulez-vous commencer une nouvelle partie avec la même taille de plateau ?",
        )
        if result:
            self.app.show_frame(
                lambda parent, app: SingleplayerGameFrame(parent, app, self.board_size)
            )

    def _on_resign(self) -> None:
        """
        Handle the Resign button click.
        """
        if self.game.current_color == Goban.WHITE:
            return super()._on_resign()

    def _on_board_click(self, event: tk.Event) -> None:
        """
        Handle mouse clicks on the board.

        Args:
            event (tk.Event): The click event containing mouse coordinates.
        """

        if self.game.current_color == Goban.WHITE:
            super()._on_board_click(event)

            if not self.game.game_over():
                # Wait for animation to complete before letting AI play
                self._wait_and_play_ai()

    def _wait_and_play_ai(self) -> None:
        """
        Wait until no animation is running, then let the AI play its move.
        """

        if self.animating:
            self.after(100, self._wait_and_play_ai)
        else:
            self._ai_move()

    def _ai_move(self) -> None:
        """
        Let the AI take a move
        """

        if self.game.current_color == Goban.BLACK:
            move = self.ai.choose_move()

            if move != "pass" and move != "resign":
                x, y = move
                successfull, capture = self.game.take_move(x, y)  # type: ignore
                if successfull:
                    self.last_move = (x, y)

                    # Get the bowl corresponding to the color that JUST played (before color switch)
                    bowl = (
                        self.white_bowl
                        if self.game.current_color == Goban.BLACK
                        else self.black_bowl
                    )
                    item = bowl.pop_stone_item()

                    if item:
                        target = self._intersection_coords(x, y)  # type: ignore
                        self.last_move = (x, y)
                        self._animate_stone(item, target, capture=capture)
                    else:
                        self._draw_stone(x, y, self.game.goban.board[x, y])  # type: ignore
                        if capture:
                            self._draw_board()
                            self.sound_manager.play_exclusive("capture_effect")
                        else:
                            self.sound_manager.play_exclusive("stone_placed_effect")
                        self._update_display()

                    # Check if game is over
                    if self.game.game_over():
                        self._show_game_over_dialog()
                else:
                    # Play invalid move sound
                    self.sound_manager.play_exclusive("invalid_move_effect")

            elif move == "pass":
                super()._on_pass()

            elif move == "resign":
                self._show_game_over_dialog(resigned_by=Goban.BLACK)
