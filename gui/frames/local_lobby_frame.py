"""
Game lobby frame for the Go game application.

This module provides the game setup interface where users can select
board size and game mode (single player vs multiplayer) before starting a game.
"""

from typing import TYPE_CHECKING
import tkinter as tk
import tkinter.ttk as ttk

from game.core import Goban
from gui.frames.game_frame import GameFrame, SingleplayerGameFrame
from gui.frames.ai_selector_frame import AISelectorFrame
from gui.utils import random_username
from player.ai import Player, load_ai
from random import randint

from game.core import GoGame

if TYPE_CHECKING:
    from gui.app import App
from gui.widgets import TopLevelWindow, TexturedButton


class LocalLobbyFrame(ttk.Frame):
    """
    Frame for game lobby before starting a game.

    Allows the user to select game options before starting the game.
    """

    def __init__(self, parent: ttk.Frame, app: "App"):
        """
        Initialize the game lobby frame.

        Args:
            parent (ttk.Frame): The parent frame.
            app (App): The main application instance.
        """
        self.ui = app.ui
        self.S = app.S

        super().__init__(parent)

        self.app = app
        self._loading = self.app.show_loading("Chargement du lobby local...")

        self.board_size = tk.IntVar(value=19)
        self.multiplayer = tk.BooleanVar(value=True)
        self.played_color = tk.IntVar(value=randint(Goban.BLACK, Goban.WHITE))
        self.after(0, self._build_step_1)

    def _build_step_1(self) -> None:
        # Title
        title = ttk.Label(self, text="Game Lobby", style="Title.TLabel")
        title.pack(pady=40)

        self.container = ttk.Frame(self)
        self.container.pack()

        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_columnconfigure(1, weight=1)
        self.container.grid_columnconfigure(2, weight=1)

        # Ensure account panel is visible on this frame
        if hasattr(self.app, "account_panel") and self.app.account_panel:
            self.app.account_panel.lift()

        self.after(0, self._build_step_2)

    def _build_step_2(self) -> None:
        # Number of players selection frame
        main_player_frame = self.app.Frame(self.container, bg="black", bd=1)
        main_player_frame.grid(
            row=0, column=0, pady=self.S(20), padx=self.S(5), sticky="nes"
        )
        player_frame = self.app.Frame(main_player_frame)
        player_frame.pack(pady=self.S(3), padx=self.S(3), fill=tk.BOTH, expand=True)

        # Buttons for number of players
        self.multiplayer_button = self.app.Button(
            player_frame.content_frame,
            overlay_path=self.app.multiplayer_icon_path,
            hover_overlay_path=self.app.hovered_multiplayer_icon_path,
            text="Deux joueurs",
            command=lambda: self._select_player("multiplayer"),
            takefocus=False,
        )
        self.multiplayer_button.pack(padx=self.S(30), pady=self.S((20, 10)), fill=tk.X)
        self.singleplayer_button = self.app.Button(
            player_frame.content_frame,
            overlay_path=self.app.singleplayer_icon_path,
            hover_overlay_path=self.app.hovered_singleplayer_icon_path,
            text="Un joueur",
            command=lambda: self._select_player("singleplayer"),
            takefocus=False,
        )
        self.singleplayer_button.pack(padx=self.S(30), pady=self.S(10), fill=tk.X)
        self._select_player("multiplayer")

        # Button to select AI difficulty (only visible in singleplayer mode)
        self.ai_button = self.app.Button(
            player_frame.content_frame,
            overlay_path=self.app.hovered_martin_icon_path,
            hover_overlay_path=self.app.hovered_martin_icon_path,
            text="Martin",
            command=self._show_ai_selector_dialog,
            takefocus=False,
        )
        if self.multiplayer.get():
            self.ai_button.pack_forget()
        else:
            self.ai_button.pack(padx=self.S(30), pady=self.S((10, 20)), fill=tk.X)

        self.after(0, self._build_step_3)

    def _build_step_3(self) -> None:
        # Board size selection frame
        main_size_frame = self.app.Frame(self.container, bg="black", bd=1)
        main_size_frame.grid(
            row=0, column=1, pady=self.S(20), padx=self.S(5), sticky="nws"
        )
        size_frame = self.app.Frame(main_size_frame)
        size_frame.pack(pady=self.S(3), padx=self.S(3), fill=tk.BOTH, expand=True)

        # Buttons for different board sizes
        self.nine_button = self.app.Button(
            size_frame.content_frame,
            overlay_path=self.app.untoggle_icon_path,
            hover_overlay_path=self.app.hovered_untoggle_icon_path,
            text="9 × 9  ",
            width=150,
            command=lambda: self._select_size(9),
            takefocus=False,
        )
        self.nine_button.pack(padx=self.S(30), pady=self.S((20, 10)), fill=tk.X)
        self.thirteen_button = self.app.Button(
            size_frame.content_frame,
            overlay_path=self.app.untoggle_icon_path,
            hover_overlay_path=self.app.hovered_untoggle_icon_path,
            text="13 × 13",
            width=150,
            command=lambda: self._select_size(13),
            takefocus=False,
        )
        self.thirteen_button.pack(padx=self.S(30), pady=self.S(10), fill=tk.X)
        self.nineteen_button = self.app.Button(
            size_frame.content_frame,
            overlay_path=self.app.toggle_icon_path,
            hover_overlay_path=self.app.hovered_toggle_icon_path,
            text="19 × 19",
            width=150,
            command=lambda: self._select_size(19),
            takefocus=False,
        )
        self.nineteen_button.pack(padx=self.S(30), pady=self.S((10, 20)), fill=tk.X)

        self.after(0, self._build_step_4)

    def _build_step_4(self) -> None:
        # Color selection frame
        main_color_frame = self.app.Frame(self.container, bg="black", bd=1)
        main_color_frame.grid(
            row=0, column=2, pady=self.S(20), padx=self.S(5), sticky="nws"
        )
        color_frame = self.app.Frame(main_color_frame)
        color_frame.pack(pady=self.S(3), padx=self.S(3), fill=tk.BOTH, expand=True)

        # Buttons for different board sizes
        self.black_button = self.app.Button(
            color_frame.content_frame,
            overlay_path=self.app.untoggle_icon_path,
            hover_overlay_path=self.app.hovered_untoggle_icon_path,
            text="Jouer les noirs",
            command=lambda: self._select_color(Goban.BLACK),
            takefocus=False,
        )
        self.black_button.pack(padx=self.S(30), pady=self.S((20, 10)), fill=tk.X)
        self.white_button = self.app.Button(
            color_frame.content_frame,
            overlay_path=self.app.untoggle_icon_path,
            hover_overlay_path=self.app.hovered_untoggle_icon_path,
            text="Jouer les blancs",
            command=lambda: self._select_color(Goban.WHITE),
            takefocus=False,
        )
        self.white_button.pack(padx=self.S(30), pady=self.S(10), fill=tk.X)
        self.indifferent_button = self.app.Button(
            color_frame.content_frame,
            overlay_path=self.app.toggle_icon_path,
            hover_overlay_path=self.app.hovered_toggle_icon_path,
            text="Indifférent    ",
            command=lambda: self._select_color(3),
            takefocus=False,
        )
        self.indifferent_button.pack(padx=self.S(30), pady=self.S((10, 20)), fill=tk.X)

        self.after(0, self._build_step_5)

    def _build_step_5(self) -> None:
        self.app.Button(
            self,
            text="Continuer la partie",
            command=lambda: self._resume_game(game=self.app.current_game),  # type: ignore
            state=tk.DISABLED if self.app.current_game is None else tk.NORMAL,
            takefocus=False,
        ).pack(pady=self.S((20, 10)))

        # Start Game button
        self.app.Button(
            self,
            text="Démarrer la partie",
            command=self._start_game,
            takefocus=False,
        ).pack(pady=self.S(10))

        # Return to Lobby button
        self.app.Button(
            self,
            text="Retour au Lobby",
            overlay_path=self.app.return_icon_path,
            hover_overlay_path=self.app.hovered_return_icon_path,
            command=self._return_to_lobby,
            takefocus=False,
        ).pack(pady=self.S((10, 20)))

        self.app.hide_loading(self._loading)

    def _select_player(self, mode: str) -> None:
        """
        Emulates the behavior of radiobuttons for player mode selection.

        Args:
            mode (str): The game mode to select ("singleplayer" or "multiplayer").
        """

        if mode == "singleplayer":
            self.multiplayer.set(False)
            self.multiplayer_button.configure(
                overlay_path=self.app.multiplayer_icon_path,
                hover_overlay_path=self.app.hovered_multiplayer_icon_path,
            )
            self.singleplayer_button.configure(
                overlay_path=self.app.hovered_singleplayer_icon_path,
                hover_overlay_path=self.app.hovered_singleplayer_icon_path,
            )

            try:
                if not self.ai_button.winfo_ismapped():
                    self.ai_button.pack(
                        padx=self.S(30), pady=self.S((10, 20)), fill=tk.X
                    )
            except:
                pass

        elif mode == "multiplayer":
            self.multiplayer.set(True)
            self.multiplayer_button.configure(
                overlay_path=self.app.hovered_multiplayer_icon_path,
                hover_overlay_path=self.app.hovered_multiplayer_icon_path,
            )
            self.singleplayer_button.configure(
                overlay_path=self.app.singleplayer_icon_path,
                hover_overlay_path=self.app.hovered_singleplayer_icon_path,
            )

            try:
                if self.ai_button.winfo_ismapped():
                    self.ai_button.pack_forget()
            except:
                pass

    def _show_ai_selector_dialog(self) -> None:
        """
        Show the aiselector dialog (called after mainloop is active).
        """

        self.app.open_dialog(TopLevelWindow(self.app, width=400, height=700), AISelectorFrame, ai_selector_button=self.ai_button)  # type: ignore

    def _select_size(self, size: int) -> None:
        """
        Emulates the behavior of radiobuttons

        Args:
            size (int): The size of the board to select (9, 13, or 19).
        """

        self.board_size.set(size)

        match size:
            case 9:
                self.nine_button.configure(
                    overlay_path=self.app.toggle_icon_path,
                    hover_overlay_path=self.app.hovered_toggle_icon_path,
                )
                self.thirteen_button.configure(
                    overlay_path=self.app.untoggle_icon_path,
                    hover_overlay_path=self.app.hovered_untoggle_icon_path,
                )
                self.nineteen_button.configure(
                    overlay_path=self.app.untoggle_icon_path,
                    hover_overlay_path=self.app.hovered_untoggle_icon_path,
                )
            case 13:
                self.nine_button.configure(
                    overlay_path=self.app.untoggle_icon_path,
                    hover_overlay_path=self.app.hovered_untoggle_icon_path,
                )
                self.thirteen_button.configure(
                    overlay_path=self.app.toggle_icon_path,
                    hover_overlay_path=self.app.hovered_toggle_icon_path,
                )
                self.nineteen_button.configure(
                    overlay_path=self.app.untoggle_icon_path,
                    hover_overlay_path=self.app.hovered_untoggle_icon_path,
                )
            case 19:
                self.nine_button.configure(
                    overlay_path=self.app.untoggle_icon_path,
                    hover_overlay_path=self.app.hovered_untoggle_icon_path,
                )
                self.thirteen_button.configure(
                    overlay_path=self.app.untoggle_icon_path,
                    hover_overlay_path=self.app.hovered_untoggle_icon_path,
                )
                self.nineteen_button.configure(
                    overlay_path=self.app.toggle_icon_path,
                    hover_overlay_path=self.app.hovered_toggle_icon_path,
                )

    def _select_color(self, color: int) -> None:
        """
        Emulates the behavior of radiobuttons

        Args:
            color (int): The color to select (Goban.BLACK or Goban.WHITE).
        """

        self.played_color.set(
            color
            if color in (Goban.BLACK, Goban.WHITE)
            else randint(Goban.BLACK, Goban.WHITE)
        )

        match color:
            case Goban.BLACK:
                self.black_button.configure(
                    overlay_path=self.app.toggle_icon_path,
                    hover_overlay_path=self.app.hovered_toggle_icon_path,
                )
                self.white_button.configure(
                    overlay_path=self.app.untoggle_icon_path,
                    hover_overlay_path=self.app.hovered_untoggle_icon_path,
                )
                self.indifferent_button.configure(
                    overlay_path=self.app.untoggle_icon_path,
                    hover_overlay_path=self.app.hovered_untoggle_icon_path,
                )
            case Goban.WHITE:
                self.black_button.configure(
                    overlay_path=self.app.untoggle_icon_path,
                    hover_overlay_path=self.app.hovered_untoggle_icon_path,
                )
                self.white_button.configure(
                    overlay_path=self.app.toggle_icon_path,
                    hover_overlay_path=self.app.hovered_toggle_icon_path,
                )
                self.indifferent_button.configure(
                    overlay_path=self.app.untoggle_icon_path,
                    hover_overlay_path=self.app.hovered_untoggle_icon_path,
                )
            case 3:
                self.black_button.configure(
                    overlay_path=self.app.untoggle_icon_path,
                    hover_overlay_path=self.app.hovered_untoggle_icon_path,
                )
                self.white_button.configure(
                    overlay_path=self.app.untoggle_icon_path,
                    hover_overlay_path=self.app.hovered_untoggle_icon_path,
                )
                self.indifferent_button.configure(
                    overlay_path=self.app.toggle_icon_path,
                    hover_overlay_path=self.app.hovered_toggle_icon_path,
                )

    def _resume_game(self, game: "GoGame") -> None:
        """
        Resume an existing game.

        Args:
            game (GoGame): The game instance to resume.
        """

        board_size = game.goban.size
        color_played = game.played_color
        display_name = self.app._get_display_name()
        opponent_username = game.opponent_username

        if not game.singleplayer:

            if color_played == Goban.BLACK:
                black_player = Player(
                    display_name,
                    self.app.get_profile_photo(display_name.split(" ")[0]),
                    color=Goban.BLACK,
                    level=-3000,
                )
                white_player = Player(
                    opponent_username,
                    self.app._get_default_profile_photo(
                        opponent_username.split(" ")[0]
                    ),
                    color=Goban.WHITE,
                    level=-3000,
                )

            else:
                white_player = Player(
                    display_name,
                    self.app.get_profile_photo(display_name.split(" ")[0]),
                    color=Goban.WHITE,
                    level=-3000,
                )
                black_player = Player(
                    opponent_username,
                    self.app._get_default_profile_photo(
                        opponent_username.split(" ")[0]
                    ),
                    color=Goban.BLACK,
                    level=-3000,
                )

            self.app.show_frame(
                lambda parent, app: GameFrame(
                    parent,
                    app,
                    board_size,
                    black_player,
                    white_player,
                    game,
                    game.played_color,
                ),
                show_social_panel=False,
            )

        else:
            print("Resuming singleplayer game...")

            if color_played == Goban.BLACK:
                black_player = Player(
                    display_name,
                    self.app.get_profile_photo(display_name.split(" ")[0]),
                    color=Goban.BLACK,
                    level=-3000,
                )
                white_player = load_ai(opponent_username, game, Goban.WHITE)

            else:
                white_player = Player(
                    display_name,
                    self.app.get_profile_photo(display_name.split(" ")[0]),
                    color=Goban.WHITE,
                    level=-3000,
                )
                black_player = load_ai(opponent_username, game, Goban.BLACK)

            self.app.show_frame(
                lambda parent, app: SingleplayerGameFrame(
                    parent,
                    app,
                    board_size,
                    black_player,
                    white_player,
                    game,
                    color_played,
                ),
                show_social_panel=False,
            )

    def _start_game(self) -> None:
        """
        Start a new game with the selected board size.

        Args:
            board_size (int): The size of the board (9, 13, or 19).
            multiplayer (bool): Whether the game is multiplayer. Defaults to True.
            ai (int | None): The AI difficulty level if applicable. Defaults to None.
        """
        from gui.frames.game_frame import GameFrame, SingleplayerGameFrame

        if self.multiplayer.get():
            display_name = self.app._get_display_name()
            opponent_username = random_username()
            game = GoGame(self.board_size.get())

            if self.played_color.get() == Goban.BLACK:
                black_player = Player(
                    display_name,
                    self.app.get_profile_photo(display_name.split(" ")[0]),
                    color=Goban.BLACK,
                    level=-3000,
                )
                white_player = Player(
                    opponent_username,
                    self.app._get_default_profile_photo(
                        opponent_username.split(" ")[0]
                    ),
                    color=Goban.WHITE,
                    level=-3000,
                )

            else:
                white_player = Player(
                    display_name,
                    self.app.get_profile_photo(display_name.split(" ")[0]),
                    color=Goban.WHITE,
                    level=-3000,
                )
                black_player = Player(
                    opponent_username,
                    self.app._get_default_profile_photo(
                        opponent_username.split(" ")[0]
                    ),
                    color=Goban.BLACK,
                    level=-3000,
                )

            self.app.show_frame(
                lambda parent, app: GameFrame(
                    parent,
                    app,
                    self.board_size.get(),
                    black_player,
                    white_player,
                    game,
                    self.played_color.get(),
                ),
                show_social_panel=False,
            )

        if not self.multiplayer.get():
            display_name = self.app._get_display_name()
            game = GoGame(self.board_size.get())

            if self.played_color.get() == Goban.BLACK:
                black_player = Player(
                    display_name,
                    self.app.get_profile_photo(display_name.split(" ")[0]),
                    color=Goban.BLACK,
                    level=-3000,
                )
                white_player = load_ai(self.ai_button.text, game, Goban.WHITE)

            else:
                white_player = Player(
                    display_name,
                    self.app.get_profile_photo(display_name.split(" ")[0]),
                    color=Goban.WHITE,
                    level=-3000,
                )
                black_player = load_ai(self.ai_button.text, game, Goban.BLACK)

            self.app.show_frame(
                lambda parent, app: SingleplayerGameFrame(
                    parent,
                    app,
                    self.board_size.get(),
                    black_player,
                    white_player,
                    game,
                    self.played_color.get(),
                ),
                show_social_panel=False,
            )

    def _return_to_lobby(self) -> None:
        """
        Return to the lobby frame.
        """
        from gui.frames.lobby_frame import LobbyFrame

        self.app.show_frame_with_loading(LobbyFrame, "Chargement du lobby...")
