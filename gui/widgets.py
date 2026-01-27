"""
Custom Tkinter widgets for the Go game application.

This module provides custom widgets that extend standard Tkinter components
with enhanced functionality and visual styling.

Classes:
    TexturedButton: Button with textured background, overlay image, and custom text
    TopLevelWindow: Base class for modal dialog windows with overlay effect
"""

from typing import TYPE_CHECKING
import tkinter as tk
import tkinter.ttk as ttk
from pathlib import Path
from PIL import Image, ImageTk, ImageDraw, ImageFont
import platform

if TYPE_CHECKING:
    from gui.app import App


def _get_font_path(font_name: str) -> str | None:
    """
    Try to find the full path to a font file by name.
    Searches common system font directories.

    Args:
        font_name: Font name (e.g., "Arial", "Helvetica")

    Returns:
        Full path to font file, or None if not found.
    """
    system = platform.system()
    font_filename = font_name.lower().replace(" ", "")

    search_dirs = []
    if system == "Windows":
        search_dirs = [
            Path("C:/Windows/Fonts"),
            Path("C:/winnt/Fonts"),
            Path(Path.home() / "AppData/Local/Microsoft/Windows/Fonts"),
        ]
        # Common Windows font filenames
        candidates = [
            f"{font_filename}.ttf",
            f"{font_filename}.otf",
            f"{font_name}.ttf",
            f"{font_name}.otf",
        ]
    elif system == "Darwin":  # macOS
        search_dirs = [
            Path("/Library/Fonts"),
            Path("/System/Library/Fonts"),
            Path(Path.home() / "Library/Fonts"),
        ]
        candidates = [f"{font_name}.ttf", f"{font_name}.otf"]
    else:  # Linux
        search_dirs = [
            Path("/usr/share/fonts"),
            Path("/usr/local/share/fonts"),
            Path(Path.home() / ".fonts"),
        ]
        candidates = [f"{font_name}.ttf", f"{font_name}.otf"]

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for candidate in candidates:
            font_path = search_dir / candidate
            if font_path.exists():
                return str(font_path)
            # Also search recursively
            for found in search_dir.rglob(candidate):
                return str(found)

    return None


class TexturedButton(tk.Button):
    """
    A Button with a textured background, overlay image, and text all rendered in PIL.
    The overlay and text are positioned together as a group, centered in the texture.
    Supports a custom 'disabled' state that prevents interaction without changing appearance.
    """

    def __init__(
        self,
        parent,
        texture_path: str | Path,
        text: str = "",
        overlay_path: str | Path | None = None,
        width: int = 120,
        height: int = 40,
        overlay_compound: str = "left",
        overlay_padding: int = 6,
        text_color: str = "black",
        hover_text_color: str | None = "white",
        hover_border_color: str | None = "white",
        font: tuple[str, int] | None = None,
        font_dpi_scale: float = 96 / 72,
        bd: int = 0,
        bg: str = "black",
        highlightthickness: int = 0,
        disabled: bool = False,
        **kwargs,
    ):
        """
        Args:
            texture_path: Path to the large texture image (e.g., 1920x1080).
            text: Button text (drawn in PIL, not Tkinter).
            overlay_path: Optional path to an image to draw next to the text.
            width, height: Button size in pixels.
            overlay_compound: Position of overlay relative to text ("left", "right", "top", "bottom", "center").
            overlay_padding: Spacing between overlay and text in pixels.
            text_color: Color of the text (e.g., "white", "black", "#ffffff").
            hover_text_color: Text color on hover (default: same as text_color).
            font: Tuple (font_name, font_size) for PIL. If None, uses default.
            bd: Border width in pixels (default: 0).
            hover_border_color: Border color on hover (default: same as background).
            font_dpi_scale: Scale factor for font size based on DPI (default: 96
            highlightthickness: Highlight border thickness in pixels (default: 0).            **kwargs: Other tk.Button arguments (command, etc.) — NOT compound, padx, pady, or text.
        """
        # Initialize button with empty text (all rendering is in PIL)
        super().__init__(parent, text="", width=width, height=height, bg=bg, **kwargs)

        self.width = width
        self.height = height
        self.texture_path = Path(texture_path)
        self.overlay_path = Path(overlay_path) if overlay_path else None
        self.overlay_compound = overlay_compound
        self.overlay_padding = overlay_padding
        self.text = text
        self.text_color = text_color
        self.hover_text_color = hover_text_color
        self.hover_border_color = hover_border_color
        self.font = font or ("Arial", 12)
        self.font_dpi_scale = font_dpi_scale
        self.bd = bd
        self.bg = bg
        self.highlightthickness = highlightthickness

        # Custom state management
        self._is_disabled = False
        self._original_command = None
        self._original_text_color = text_color

        # Set_disabled
        self.set_disabled(disabled)

        # Load and adapt texture
        self._update_texture()

        # Bindings
        self._original_bg = self.bg
        self.bind("<Enter>", self.hover_effect_on_enter)
        self.bind("<Leave>", self.hover_effect_on_leave)

    def _update_texture(self):
        """Crop texture, render text+overlay in PIL, and composite everything."""
        # Load and crop texture to button size
        tex_img = Image.open(self.texture_path).convert("RGBA")
        tex_w, tex_h = tex_img.size
        left = max(0, (tex_w - self.width) // 2)
        top = max(0, (tex_h - self.height) // 2)
        right = min(tex_w, left + self.width)
        bottom = min(tex_h, top + self.height)

        cropped = tex_img.crop((left, top, right, bottom))
        texture = cropped.resize((self.width, self.height), Image.Resampling.LANCZOS)

        # Create drawable canvas (same size as button)
        final_img = texture.convert("RGBA")
        draw = ImageDraw.Draw(final_img)

        # Load PIL font
        try:
            font_path = _get_font_path(self.font[0])
            pil_font_size = int(self.font[1] * self.font_dpi_scale)
            if font_path:
                pil_font = ImageFont.truetype(font_path, pil_font_size)
            else:
                pil_font = ImageFont.load_default()
        except (OSError, TypeError):
            pil_font = ImageFont.load_default()

        # Measure text size
        text_bbox = draw.textbbox((0, 0), self.text, font=pil_font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

        # Load and resize overlay if provided
        overlay = None
        overlay_width = 0
        overlay_height = 0
        if self.overlay_path and self.overlay_path.exists():  # type: ignore
            overlay = Image.open(self.overlay_path).convert("RGBA")
            overlay_max_size = min(self.width, self.height) - 2 * self.overlay_padding
            overlay.thumbnail(
                (overlay_max_size, overlay_max_size), Image.Resampling.LANCZOS
            )
            overlay_width = overlay.width
            overlay_height = overlay.height

        # Calculate total bounding box for (overlay + text) group
        if self.overlay_compound == "left":
            total_width = (
                overlay_width + self.overlay_padding + text_width
                if overlay
                else text_width
            )
            total_height = max(overlay_height, text_height)
        elif self.overlay_compound == "right":
            total_width = (
                text_width + self.overlay_padding + overlay_width
                if overlay
                else text_width
            )
            total_height = max(overlay_height, text_height)
        elif self.overlay_compound == "top":
            total_width = max(overlay_width, text_width)
            total_height = (
                overlay_height + self.overlay_padding + text_height
                if overlay
                else text_height
            )
        elif self.overlay_compound == "bottom":
            total_width = max(overlay_width, text_width)
            total_height = (
                text_height + self.overlay_padding + overlay_height
                if overlay
                else text_height
            )
        else:  # center
            total_width = max(overlay_width, text_width)
            total_height = max(overlay_height, text_height)

        # Calculate centered position for the group
        group_x = (self.width - total_width) // 2
        group_y = (self.height - total_height) // 2

        # Position overlay and text within the group
        if self.overlay_compound == "left" and overlay:
            overlay_x = group_x
            overlay_y = group_y + (total_height - overlay_height) // 2
            text_x = group_x + overlay_width + self.overlay_padding
            text_y = group_y + (total_height - text_height) // 2
        elif self.overlay_compound == "right" and overlay:
            text_x = group_x
            text_y = group_y + (total_height - text_height) // 2
            overlay_x = group_x + text_width + self.overlay_padding
            overlay_y = group_y + (total_height - overlay_height) // 2
        elif self.overlay_compound == "top" and overlay:
            overlay_x = group_x + (total_width - overlay_width) // 2
            overlay_y = group_y
            text_x = group_x + (total_width - text_width) // 2
            text_y = group_y + overlay_height + self.overlay_padding
        elif self.overlay_compound == "bottom" and overlay:
            text_x = group_x + (total_width - text_width) // 2
            text_y = group_y
            overlay_x = group_x + (total_width - overlay_width) // 2
            overlay_y = group_y + text_height + self.overlay_padding
        else:  # center or no overlay
            text_x = group_x + (total_width - text_width) // 2
            text_y = group_y + (total_height - text_height) // 2
            overlay_x = group_x + (total_width - overlay_width) // 2
            overlay_y = group_y + (total_height - overlay_height) // 2

        # Composite overlay onto texture
        if overlay:
            final_img.paste(overlay, (int(overlay_x), int(overlay_y)), overlay)

        # Draw text
        draw.text(
            (int(text_x), int(text_y)), self.text, fill=self.text_color, font=pil_font
        )

        # Convert to PhotoImage
        photo = ImageTk.PhotoImage(final_img)
        self._photo = photo  # Keep reference

        # Set as background
        self.config(image=photo, bd=self.bd, highlightthickness=self.highlightthickness)

    def resize(self, new_width: int, new_height: int):
        """Dynamically resize button and re-render texture."""
        self.width = new_width
        self.height = new_height
        self._update_texture()

    def set_overlay(self, overlay_path: str | Path | None):
        """Change or remove the overlay image."""
        self.overlay_path = Path(overlay_path) if overlay_path else None
        self._update_texture()

    def set_text(self, new_text: str):
        """Change the button text and re-render."""
        self.text = new_text
        self._update_texture()

    def set_disabled(self, disabled: bool = True):
        """
        Set custom disabled state without changing appearance.

        Args:
            disabled (bool): True to disable, False to enable.
        """
        self._is_disabled = disabled

        if disabled:
            # Store the original command and replace it with a no-op
            self._original_command = self.cget("command")
            self.text_color = "gray"
            self._update_texture()
        else:
            # Restore the original command
            if self._original_command:
                self.configure(
                    command=self._original_command, text_color=self._original_text_color
                )
            self._original_command = None

    def is_disabled(self) -> bool:
        """Check if button is in disabled state."""
        return self._is_disabled

    def configure(
        self,
        texture_path: str | Path | None = None,
        text: str | None = None,
        overlay_path: str | Path | None = None,
        width: int | None = None,
        height: int | None = None,
        overlay_compound: str | None = None,
        overlay_padding: int | None = None,
        text_color: str | None = None,
        font: tuple[str, int] | None = None,
        font_dpi_scale: float | None = None,
        bd: int | None = None,
        highlightthickness: int | None = None,
        **kwargs,
    ) -> None:
        """Config the arguments of the textured button."""

        if texture_path is not None:
            self.texture_path = texture_path
        if text is not None:
            super().configure(text=text)
            self.text = text
        if overlay_path is not None:
            self.overlay_path = overlay_path
        if width is not None:
            super().configure(width=width)
            self.width = width
        if height is not None:
            super().configure(height=height)
            self.height = height
        if overlay_compound is not None:
            overlay_compound = overlay_compound
        if overlay_padding is not None:
            self.overlay_padding = overlay_padding
        if text_color is not None:
            self.text_color = text_color
        if font is not None:
            self.font = font
        if font_dpi_scale is not None:
            self.font_dpi_scale = font_dpi_scale
        if bd is not None:
            self.bd = bd
        if highlightthickness is not None:
            self.highlightthickness = highlightthickness

        super().config(**kwargs)
        self._original_text_color = self.text_color
        self._original_bg = self.bg
        self._update_texture()

    def hover_effect_on_enter(self, event):
        """
        Change text_color and border color on hover.

        Args:
            event: Tkinter event object.
            text_color: Text color on hover.
            border_color: Border color on hover.
        """

        if not self.is_disabled():
            self.config(bg=self.hover_border_color)  # type: ignore
            self.text_color = self.hover_text_color
            self._update_texture()

    def hover_effect_on_leave(self, event):
        """
        Change text_color and border color on hover.

        Args:
            event: Tkinter event object.
            text_color: Text color on hover.
            border_color: Border color on hover.
        """

        if not self.is_disabled():
            self.config(bg=self._original_bg)
            self.text_color = self._original_text_color
            self._update_texture()


class TopLevelWindow(tk.Toplevel):
    """
    A custom top level window for dialogs with no toolbar, modal behavior,
    and standard dialog features.

    Features:
    - No title bar (overrideredirect)
    - Modal (blocks parent window)
    - Centered on screen
    - Keyboard shortcuts (Escape to close)
    - Result value support
    - Semi-transparent overlay/shadow
    - Fade-in animation
    - Standardized button area
    """

    def __init__(
        self,
        master: "App",  # Forward reference to avoid circular import
        width: int,
        height: int,
        fade_in: bool = True,
        overlay: bool = True,
        overlay_color: str = "#000000",
        overlay_alpha: float = 0.5,
        **kwargs,
    ):
        """
        Initializes the window

        Args:
            master (App): The parent application
            width (int): The width of the window
            height (int): The height of the window
            fade_in (bool): Enable fade-in animation
            overlay (bool): Create a semi-transparent overlay behind the dialog
            overlay_color (str): Color of the overlay
            overlay_alpha (float): Opacity of the overlay (0.0 to 1.0)
        """

        # Create overlay window first (before the dialog)
        self.overlay_window = None
        if overlay:
            self.overlay_window = self._create_overlay(
                master, overlay_color, overlay_alpha
            )

        super().__init__(**kwargs)
        self.master = master
        self.result = None
        self.transient(master)
        self.overrideredirect(True)
        self.withdraw()

        self.geometry(f"{width}x{height}")

        # Create main container
        self.container = ttk.Frame(self)
        self.container.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Body frame (for content)
        self.body_frame = ttk.Frame(self.container)
        self.body_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Button frame (at bottom)
        self.button_frame = ttk.Frame(self.container)
        self.button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)

        # Keyboard shortcuts
        self.bind("<Escape>", lambda e: self.close(None))
        self.bind("<Return>", lambda e: self.on_validate())

        # Drawing the body (override in subclasses)
        self.body(**kwargs)

        # Center window on screen
        self.update_idletasks()
        self._center_window()

        # Show window
        self.wm_deiconify()

        # Fade-in animation
        if fade_in:
            self._fade_in()

        # Grab/wait are deferred so callers can attach content before showing

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

    def _create_overlay(self, master: tk.Tk, color: str, alpha: float) -> tk.Toplevel:
        """
        Create a semi-transparent overlay window that covers the parent.

        Args:
            master: Parent window to cover
            color: Overlay color
            alpha: Opacity (0.0 to 1.0)

        Returns:
            The overlay Toplevel window
        """
        overlay = tk.Toplevel(master)
        overlay.overrideredirect(True)
        overlay.configure(bg=color)

        # Apply full screen window
        try:
            overlay.state("zoomed")
        except tk.TclError:
            overlay.attributes("-fullscreen", True)
        overlay.update_idletasks()

        # Set transparency
        overlay.attributes("-alpha", alpha)

        # Make it stay below the dialog but above the parent
        overlay.transient(master)
        overlay.lift(master)

        return overlay

    def _fade_in(self, alpha: float = 0.0, step: float = 0.15) -> None:
        """
        Fade-in animation for window appearance.

        Args:
            alpha (float): Current alpha value (0.0 to 1.0)
            step (float): Increment step for each frame
        """
        if alpha < 1.0:
            self.attributes("-alpha", alpha)
            self.after(20, lambda: self._fade_in(alpha + step, step))
        else:
            self.attributes("-alpha", 1.0)

    def _add_icon(self, icon_type: str = "info", size: int = 32) -> tk.Label:
        """
        Add a standard icon to the dialog.

        Args:
            icon_type (str): One of 'info', 'warning', 'error', 'question'
            size (int): Icon size in pixels

        Returns:
            tk.Label: The icon label widget
        """
        icons = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "question": "❓"}

        icon_text = icons.get(icon_type, "ℹ️")
        icon_label = tk.Label(
            self.body_frame,
            text=icon_text,
            font=("Segoe UI Emoji", size),
            bg=self.body_frame["bg"],
        )
        return icon_label

    def show(self, wait: bool = True) -> None:
        """
        Display the dialog, grab focus, and optionally block until closed.

        Args:
            wait (bool): When True, block until the dialog is closed (blocking mode).
                        When False, show dialog non-blocking without grab.
        """

        # Make dialog visible
        self.deiconify()

        # Ensure dialog is above overlay and parent
        if self.overlay_window:
            self.overlay_window.lift(self.master)
        self.lift()
        self.focus_force()

        if wait:
            # Blocking mode: grab input and wait for closure
            self.grab_set()
            self.wait_visibility()
            self.wait_window(self)
        else:
            # Non-blocking mode: just show without grab
            # Allow parent to remain responsive
            pass

    def close(self, result=None) -> None:
        """
        Close the dialog with an optional result.

        Args:
            result: The result value to return to caller
        """
        self.result = result

        try:
            # Release grab
            try:
                self.grab_release()
            except (tk.TclError, RuntimeError):
                pass  # Grab already released or window already destroyed

            # Return focus to parent
            try:
                self.master.focus_set()
            except (tk.TclError, RuntimeError):
                pass

            # Destroy overlay window if it exists
            if self.overlay_window:
                try:
                    self.overlay_window.destroy()
                except (tk.TclError, RuntimeError):
                    pass  # Already destroyed
        finally:
            # Always destroy self
            try:
                self.destroy()
            except (tk.TclError, RuntimeError):
                pass

    def on_validate(self) -> None:
        """
        Called when the user validates the dialog (e.g., presses Enter).
        Override in subclasses to handle validation.
        By default, closes the dialog with result=True.
        """
        self.close(result=True)

    def body(self, **kwargs) -> None:
        """
        Override this method in subclasses to create dialog content.
        Use self.body_frame as the parent for content widgets.
        Use self._create_button_area() to add buttons.
        """
        pass
