"""
Login / register dialog for user authentication.

This module provides the dialog interface for users to log in or register.
"""

from typing import TYPE_CHECKING
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.messagebox as messagebox

import requests
import asyncio
import httpx
import threading

if TYPE_CHECKING:
    from gui.app import App
from gui.widgets import TopLevelWindow, TexturedButton

# API base URL
from config import BASE_URL


class AISelectorFrame(ttk.Frame):
    """
    Dialog toplevel for AI selection actions.

    Allows users to select an AI for the game.
    """

    def __init__(
        self, parent: tk.Widget, app: "App", ai_selector_button: TexturedButton
    ):
        """
        Initializes the AI selector dialog.

        Args:
            parent: The container in which this frame is placed (e.g., dialog body)
            app (App): The main application instance.
        """
        self.ui = app.ui
        self.S = app.S

        super().__init__(parent)
        self.app = app
        self.ai_selector_button = ai_selector_button
        self._login_timeout_handle = None
        loading = self.app.show_loading("Chargement...")

        # Create canvas and scrollbar for scrollable content
        canvas_frame = ttk.Frame(self)
        canvas_frame.pack(
            fill=tk.BOTH, expand=True, padx=self.S(20), pady=self.S((30, 20))
        )

        canvas = tk.Canvas(canvas_frame, bg="#1e1e1e", highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        scrollable_window = canvas.create_window(
            (0, 0), window=scrollable_frame, anchor="n"
        )
        canvas.configure(yscrollcommand=scrollbar.set)

        def _on_canvas_configure(event):
            canvas.itemconfig(scrollable_window, width=event.width)
            canvas.coords(scrollable_window, event.width / 2, 0)

        canvas.bind("<Configure>", _on_canvas_configure)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Enable mouse wheel scrolling
        def _on_mousewheel(event):
            try:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except tk.TclError:
                # Canvas has been destroyed, binding will be cleaned up
                pass

        self._mousewheel_binding = self.bind_all("<MouseWheel>", _on_mousewheel)

        # AI selection frame
        main_ai_frame = self.app.Frame(scrollable_frame, bg="black", bd=1)
        main_ai_frame.pack(pady=self.S(20), fill=tk.X, padx=self.S(20))
        ai_frame = self.app.Frame(main_ai_frame)
        ai_frame.pack(pady=self.S(3), padx=self.S(3), fill=tk.X)

        # Martin
        self.app.Label(
            ai_frame,
            text="Débutant (coups aléatoires)",
        ).pack(pady=self.S((20, 5)), padx=self.S(20))
        self.martin_button = self.app.Button(
            ai_frame,
            overlay_path=self.app.martin_icon_path,
            hover_overlay_path=self.app.hovered_martin_icon_path,
            text="Martin",
            command=lambda: self._select_ai("Martin"),
            takefocus=False,
        )
        self.martin_button.pack(pady=self.S((5, 10)), padx=self.S(20))

        # Amina
        self.app.Label(
            ai_frame,
            text="Novice (-2950 FFG)",
        ).pack(pady=self.S((10, 5)), padx=self.S(20))
        self.amina_button = self.app.Button(
            ai_frame,
            overlay_path=self.app.amina_icon_path,
            hover_overlay_path=self.app.hovered_amina_icon_path,
            text="Amina",
            command=lambda: self._select_ai("Amina"),
            takefocus=False,
        )
        self.amina_button.pack(pady=self.S((5, 10)), padx=self.S(20))

        # Léo
        self.app.Label(
            ai_frame,
            text="Intermédiaire (-2000 FFG)",
        ).pack(pady=self.S((10, 5)), padx=self.S(20))
        self.leo_button = self.app.Button(
            ai_frame,
            overlay_path=self.app.leo_icon_path,
            hover_overlay_path=self.app.hovered_leo_icon_path,
            text="Léo",
            command=lambda: self._select_ai("Léo"),
            takefocus=False,
        )
        self.leo_button.pack(pady=self.S((5, 10)), padx=self.S(20))

        # Sofia
        self.app.Label(
            ai_frame,
            text="Confirmée (-1050 FFG)",
        ).pack(pady=self.S((10, 5)), padx=self.S(20))
        self.sofia_button = self.app.Button(
            ai_frame,
            overlay_path=self.app.sofia_icon_path,
            hover_overlay_path=self.app.hovered_sofia_icon_path,
            text="Sofia",
            command=lambda: self._select_ai("Sofia"),
            takefocus=False,
        )
        self.sofia_button.pack(pady=self.S((5, 10)), padx=self.S(20))

        # Ravi
        self.app.Label(
            ai_frame,
            text="Expert (-100 FFG)",
        ).pack(pady=self.S((10, 5)), padx=self.S(20))
        self.ravi_button = self.app.Button(
            ai_frame,
            overlay_path=self.app.ravi_icon_path,
            hover_overlay_path=self.app.hovered_ravi_icon_path,
            text="Ravi",
            command=lambda: self._select_ai("Ravi"),
            takefocus=False,
        )
        self.ravi_button.pack(pady=self.S((5, 10)), padx=self.S(20))

        # Ada
        self.app.Label(
            ai_frame,
            text="Grande Maître (850 FFG)",
        ).pack(pady=self.S((10, 5)), padx=self.S(20))
        self.ada_button = self.app.Button(
            ai_frame,
            overlay_path=self.app.ada_icon_path,
            hover_overlay_path=self.app.hovered_ada_icon_path,
            text="Ada",
            command=lambda: self._select_ai("Ada"),
            takefocus=False,
        )
        self.ada_button.pack(pady=self.S((5, 10)), padx=self.S(20))

        # Return button
        self.return_button = self.app.Button(
            self,
            text="Retour",
            overlay_path=self.app.return_icon_path,
            hover_overlay_path=self.app.hovered_return_icon_path,
            command=self._on_return,
            takefocus=False,
        )
        self.return_button.pack(pady=self.S((10, 20)), padx=self.S(20), side=tk.BOTTOM)

        self.app.hide_loading(loading)

    def _select_ai(self, ai_name: str) -> None:
        """
        Handle AI selection action.

        Args:
            ai_name (str): The name of the selected AI.
        """

        # Set selected AI in the main app
        self.ai_selector_button.configure(
            text=ai_name,
            overlay_path=getattr(
                self.app, f"hovered_{ai_name.lower().replace('é', 'e')}_icon_path"
            ),
            hover_overlay_path=getattr(
                self.app, f"hovered_{ai_name.lower().replace('é', 'e')}_icon_path"
            ),
        )

        # Clean up mousewheel binding
        if self._mousewheel_binding:
            self.unbind_all("<MouseWheel>")

        # Close dialog
        dialog = self.winfo_toplevel()
        if isinstance(dialog, TopLevelWindow):
            dialog.close()

    def _on_return(self) -> None:
        """
        Handle return action to go back to the previous frame.
        """

        # Close dialog
        dialog = self.winfo_toplevel()
        if isinstance(dialog, TopLevelWindow):
            dialog.close()
