"""
Canvas components for rendering the game board.

This module provides classes for managing visual elements that appear
on the game canvas, such as stone bowls.
"""

import tkinter as tk
import math
import random
from PIL import ImageTk


class StoneBowl:
    """
    Visual representation of a stone bowl that progressively empties as stones are played.

    The stone bowl displays a collection of stones that can be drawn from during gameplay.
    It handles rendering the bowl (back and front), and manages the stones inside with
    random positioning for a natural appearance.

    Attributes:
        canvas (tk.Canvas): The canvas widget where the bowl is drawn
        cx (int): X-coordinate of the bowl center
        cy (int): Y-coordinate of the bowl center
        radius (int): Radius of the bowl in pixels
        color (int): Color identifier for the stones (0 for black, 1 for white)
        stone_image (ImageTk.PhotoImage): Image to use for individual stones
        count (int): Current number of stones remaining in the bowl
        bowl_back (ImageTk.PhotoImage): Image for the back/bottom of the bowl
        bowl_front (ImageTk.PhotoImage): Image for the front/rim of the bowl
        stone_items (list[int]): Canvas item IDs for rendered stones
        stone_coordinates (list[tuple[float, float]]): Pre-calculated positions for stones
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
        Initialize the stone bowl.

        Args:
            canvas (tk.Canvas): The canvas where the bowl will be drawn
            center (tuple[int, int]): The (x, y) center coordinates of the bowl
            radius (int): The radius of the bowl in pixels
            stone_color (int): Color identifier for stones (0=black, 1=white)
            stone_image (ImageTk.PhotoImage): Image to render for each stone
            bowl_back (ImageTk.PhotoImage): Image for the bowl's back layer
            bowl_front (ImageTk.PhotoImage): Image for the bowl's front layer
            initial_count (int): Initial number of stones in the bowl
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

    def draw(self) -> None:
        """
        Draw the complete stone bowl on the canvas.

        This renders the bowl in three layers:
        1. Back/bottom of the bowl
        2. Stones at randomized positions
        3. Front/rim of the bowl (for depth effect)
        """
        # Back layer of the bowl
        self.canvas.create_image(
            self.cx, self.cy, image=self.bowl_back, anchor="center", tags=("bowls",)
        )

        # Stones inside the bowl
        self._draw_stones()

        # Front layer/rim of the bowl
        self.canvas.create_image(
            self.cx, self.cy, image=self.bowl_front, anchor="center"
        )

    def _generate_coordinates(self) -> None:
        """
        Generate random coordinates for stone positions within the bowl.

        Uses polar coordinates (angle and radius) to distribute stones
        naturally within the bowl's circular boundary, accounting for
        stone size to prevent overflow.
        """
        # Leave space for stone size at the edges
        max_radius = self.radius * 0.9 - self.stone_image.height() / 2

        for _ in range(self.count):
            # Random angle (0 to 2π radians)
            angle = random.uniform(0, 2 * 3.14159)
            # Random radius from center
            r = random.uniform(0, max_radius)

            # Convert polar to Cartesian coordinates
            x = self.cx + r * math.cos(angle)
            y = self.cy + r * math.sin(angle)

            self.stone_coordinates.append((x, y))

    def _draw_stones(self) -> None:
        """
        Draw all stones at their pre-calculated positions.

        Creates canvas image items for each stone and stores their IDs
        for later manipulation (e.g., removal when stone is played).
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
        Remove a stone from the bowl and return its position.

        This removes the topmost stone from the bowl's visual representation
        and returns its coordinates, typically for animating the stone being
        placed on the board.

        Returns:
            tuple[float, float] | None: The (x, y) coordinates of the removed stone,
                                       or None if the bowl is empty
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
        Remove a stone and return its canvas item ID without deleting it.

        This is useful for animating a stone being moved from the bowl to
        the board, where the caller needs to control the item's deletion timing.

        Returns:
            int | None: The canvas item ID of the removed stone,
                       or None if the bowl is empty
        """
        if self.count <= 0 or not self.stone_items:
            return None

        self.count -= 1
        return self.stone_items.pop()
