"""
Responsive sizing helpers for the GUI.

This module centralizes screen-based scaling so widget sizes, paddings,
and fonts can adapt to different monitor resolutions while preserving
existing proportions on the reference layout.
"""

from __future__ import annotations

from numbers import Number
from typing import Any


class ScaledLength(int):
    """Integer pixel length produced by UIScaler with scale metadata."""

    raw_value: float
    scale_factor: float

    def __new__(
        cls, value: int, raw_value: float, scale_factor: float
    ) -> "ScaledLength":
        obj = int.__new__(cls, int(value))
        obj.raw_value = raw_value
        obj.scale_factor = scale_factor
        return obj


class UIScaler:
    """Scale UI numeric values from a reference resolution."""

    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        base_width: int = 1280,
        base_height: int = 720,
        min_scale: float = 0.75,
    ) -> None:
        print(f"Screen resolution: {screen_width}x{screen_height}")
        self.scale_w = max(min_scale, screen_width / float(base_width))
        self.scale_h = max(min_scale, screen_height / float(base_height))
        self.scale = min(self.scale_w, self.scale_h)

    def px(
        self, value: int | float | ScaledLength | None, min_value: int = 1
    ) -> ScaledLength | None:
        """Scale a pixel value. Keeps None unchanged."""
        if value is None:
            return None
        if isinstance(value, ScaledLength):
            return value
        raw_value = float(value)
        scaled = int(round(raw_value * self.scale))
        if raw_value == 0:
            return ScaledLength(0, raw_value, self.scale)
        return ScaledLength(max(min_value, scaled), raw_value, self.scale)

    def px_w(
        self, value: int | float | ScaledLength | None, min_value: int = 1
    ) -> ScaledLength | None:
        """Scale a width value using horizontal screen ratio."""
        if value is None:
            return None
        if isinstance(value, ScaledLength):
            return value
        raw_value = float(value)
        scaled = int(round(raw_value * self.scale_w))
        if raw_value == 0:
            return ScaledLength(0, raw_value, self.scale_w)
        return ScaledLength(max(min_value, scaled), raw_value, self.scale_w)

    def px_h(
        self, value: int | float | ScaledLength | None, min_value: int = 1
    ) -> ScaledLength | None:
        """Scale a height value using vertical screen ratio."""
        if value is None:
            return None
        if isinstance(value, ScaledLength):
            return value
        raw_value = float(value)
        scaled = int(round(raw_value * self.scale_h))
        if raw_value == 0:
            return ScaledLength(0, raw_value, self.scale_h)
        return ScaledLength(max(min_value, scaled), raw_value, self.scale_h)

    def maybe(self, value: Any) -> Any:
        """Scale ints/floats recursively inside tuples/lists."""
        if isinstance(value, Number):
            return self.px(float(value))  # type: ignore
        if isinstance(value, tuple):
            return tuple(self.maybe(v) for v in value)
        if isinstance(value, list):
            return [self.maybe(v) for v in value]
        return value

    def font(self, font_value: tuple[Any, ...] | None) -> tuple[Any, ...] | None:
        """Scale the size entry in a Tk font tuple."""
        if font_value is None:
            return None
        if len(font_value) < 2:
            return font_value

        family = font_value[0]
        size = font_value[1]
        rest = font_value[2:]

        if isinstance(size, ScaledLength):
            return (family, int(size), *rest)

        if isinstance(size, Number):
            scaled_size = self.px(abs(float(size))) or 1  # type: ignore
            if float(size) < 0:  # type: ignore
                scaled_size = -scaled_size
            return (family, scaled_size, *rest)

        return font_value

    def image_size(self, image_size: tuple[int, int] | None) -> tuple[int, int] | None:
        """Scale a (width, height) image tuple."""
        if image_size is None:
            return None
        return (self.px(image_size[0]) or 1, self.px(image_size[1]) or 1)
