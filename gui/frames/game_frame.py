"""
Game frame for the Go game application.

This module provides the game interface where users actually play Go games.
Includes both multiplayer and single-player game frames with full game logic,
board rendering, stone animations, and game controls.
"""

from typing import TYPE_CHECKING
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox
from pathlib import Path
from PIL import Image, ImageTk

from gui.game_canvas import StoneBowl
from game.core import Goban, GoGame
from player.ai import Martin, Leo, Magnus

if TYPE_CHECKING:
    from gui.app import App


class GameFrame(ttk.Frame):
    """
    Frame for actually playing the game.

    Handles the game board display, controls, and game state updates.
    """

    def __init__(
        self, parent: ttk.Frame, app: "App", board_size: int, game: GoGame | None = None
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
        images_dir = Path(__file__).parent.parent / "images/board"

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
        board_frame = ttk.Frame(main_frame, style="Framed.TFrame", padding=20)
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
            bg="#1e1e1e",
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
        status_frame = ttk.Frame(right_frame, style="Framed.TFrame", padding=20)
        status_frame.pack(fill=tk.X, pady=(0, 10))

        # Current player display
        self.player_label = ttk.Label(status_frame, text=self._get_player_text())
        self.player_label.pack(pady=5)

        # Move count display
        self.moves_label = ttk.Label(status_frame, text="Aucun coup joué")
        self.moves_label.pack(pady=5)

        # Control buttons frame
        main_buttons_frame = self.app.Frame(right_frame, bg="black", bd=1)
        main_buttons_frame.pack(fill=tk.X, pady=(0, 10))
        buttons_frame = self.app.Frame(main_buttons_frame)
        buttons_frame.pack(pady=3, padx=3, expand=True)

        # Pass button
        self.pass_button = self.app.Button(
            buttons_frame,
            text="Passer",
            overlay_path=self.app.pass_icon_path,
            hover_overlay_path=self.app.hovered_pass_icon_path,
            command=lambda: self._on_pass(),
            takefocus=False,
        )
        self.pass_button.pack(fill=tk.X, pady=(20, 10), padx=20)

        # Resign button
        self.resign_button = self.app.Button(
            buttons_frame,
            text="Abandon",
            overlay_path=self.app.resign_icon_path,
            hover_overlay_path=self.app.hovered_resign_icon_path,
            command=lambda: self._on_resign(),
            takefocus=False,
        )
        self.resign_button.pack(fill=tk.X, pady=10, padx=20)

        # New game button
        self.new_game_button = self.app.Button(
            buttons_frame,
            text="Revanche",
            overlay_path=self.app.revenge_icon_path,
            hover_overlay_path=self.app.hovered_revenge_icon_path,
            command=lambda: self._on_new_game(),
            takefocus=False,
        )
        self.new_game_button.pack(fill=tk.X, pady=10, padx=20)

        # Back to Lobby button
        self.back_button = self.app.Button(
            buttons_frame,
            text="Retour au lobby",
            overlay_path=self.app.return_icon_path,
            hover_overlay_path=self.app.hovered_return_icon_path,
            command=lambda: self._on_back_to_lobby(),
            takefocus=False,
        )
        self.back_button.pack(fill=tk.X, pady=(10, 20), padx=20)

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
        from gui.frames.lobby_frame import LobbyFrame

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
        self, parent: ttk.Frame, app: "App", board_size: int, game: GoGame | None = None
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
