"""
Login / register dialog for user authentication.

This module provides the dialog interface for users to log in or register.
"""

from pathlib import Path
from tkinter import messagebox
from typing import TYPE_CHECKING, Callable
from io import BytesIO
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.filedialog as filedialog

import requests
import asyncio
import httpx
import threading
from PIL import Image, ImageTk

if TYPE_CHECKING:
    from gui.app import App
from gui.widgets import TopLevelWindow, TexturedButton, clear_image_cache

# API base URL
from config import BASE_URL, BASE_FOLDER_PATH


class MessageryFrame(ttk.Frame):
    """
    Dialog toplevel for messaging.

    Allows users to:
    - Send and receive messages.
    - View message history.
    """

    def __init__(self, parent: tk.Widget, app: "App"):
        """
        Initializes the messaging dialog.

        Args:
            parent: The container in which this frame is placed (e.g., dialog body)
            app (App): The main application instance.
        """
        self.ui = app.ui
        self.S = app.S

        super().__init__(parent)
        self.app = app
        loading = self.app.show_loading("Chargement...")

        # Content frame

        content_frame = ttk.Frame(self)
        content_frame.pack(fill=tk.BOTH, expand=True)
        content_frame.grid_rowconfigure(0, weight=1)
        content_frame.grid_columnconfigure(0, weight=1, uniform="column")
        content_frame.grid_columnconfigure(1, weight=2, uniform="column")

        # Left column with conversation list and search
        left_column = ttk.Frame(content_frame)
        left_column.grid(row=0, column=0, sticky="nsew")

        # Search conversation entry
        entry_frame = ttk.Frame(left_column)
        entry_frame.pack(
            pady=self.S((80, 0)),
            padx=self.S((20, 10)),
            fill=tk.X,
        )

        entry_frame.grid_rowconfigure(0, weight=1)
        entry_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(
            entry_frame,
            image=self.app.search_icon,
        ).grid(row=0, column=0, sticky="w", padx=self.S((0, 5)))

        self.conversation_var = tk.StringVar(value=self.app.name)
        self.conversation_entry = ttk.Entry(
            entry_frame,
            width=self.S(18),
            textvariable=self.conversation_var,
            font=self.ui.font(("Skranji", 14)) or ("Skranji", 14),
            takefocus=True,
        )
        self.conversation_entry.grid(row=0, column=1, sticky="ew", padx=0)

        # Conversation list frame
        main_canvas_frame_border = self.app.Frame(left_column, bg="black", bd=1)
        main_canvas_frame_border.pack(
            fill=tk.BOTH,
            expand=True,
            padx=self.S((20, 10)),
            pady=self.S(20),
        )
        main_canvas_frame = self.app.Frame(main_canvas_frame_border)
        main_canvas_frame.pack(
            pady=self.S(3),
            padx=self.S(3),
            fill=tk.BOTH,
            expand=True,
        )
        canvas_frame = tk.Frame(
            main_canvas_frame.content_frame,
            bd=0,
            highlightbackground="black",
            highlightthickness=self.S(1),
            bg="#1e1e1e",
        )
        canvas_frame.pack(
            fill=tk.BOTH,
            expand=True,
            padx=self.S(3),
            pady=self.S(3),
        )

        # Create canvas and scrollbar for scrollable content
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

        self._build_conversation_list(scrollable_frame)

        # Right column for conversation content
        self.right_column = ttk.Frame(content_frame)
        self.right_column.grid(row=0, column=1, sticky="nsew")

        main_message_frame_border = self.app.Frame(
            self.right_column, bg="black", bd=self.S(1)
        )
        main_message_frame_border.pack(
            fill=tk.BOTH,
            expand=True,
            padx=self.S((10, 20)),
            pady=self.S(20),
        )
        main_message_frame = self.app.Frame(main_message_frame_border)
        main_message_frame.pack(
            pady=self.S(3),
            padx=self.S(3),
            ipady=self.S(5),
            ipadx=self.S(5),
            fill=tk.BOTH,
            expand=True,
        )
        message_content_frame = tk.Frame(
            main_message_frame.content_frame,
            bd=0,
            highlightbackground="black",
            highlightthickness=self.S(1),
            bg="#1e1e1e",
        )
        message_content_frame.pack(
            fill=tk.BOTH,
            expand=True,
            padx=self.S(3),
            pady=self.S(3),
        )

        # Return button
        self.return_button = self.app.Button(
            self,
            text="Retour",
            overlay_path=self.app.return_icon_path,
            hover_overlay_path=self.app.hovered_return_icon_path,
            command=self._on_return,
            takefocus=False,
        )
        self.return_button.pack(
            pady=self.S(20),
            padx=self.S(20),
            anchor=tk.S,
        )

        self.app.hide_loading(loading)

        self.conversation_entry.bind("<KeyRelease>", self._update_list)

    def _fetch_conversations(self) -> list[dict]:
        """
        Fetch the list of conversations from the backend API.

        Returns:
            list[dict]: List of conversations with their details.
        """

        try:
            response = requests.get(
                f"{BASE_URL}/messages/{self.app.username}",
                timeout=5,
            )
            if response.status_code == 200:
                conversations = {}
                for type in ["received", "sent"]:
                    for message in response.json()[type]:
                        if type == "sent":
                            other_username = message.get("recipient")
                        else:
                            other_username = message.get("sender")
                        try:
                            other_user = requests.get(
                                f"{BASE_URL}/users/{other_username}",
                                timeout=5,
                            ).json()
                        except Exception:
                            other_user = {"name": other_username, "connected": False}

                        if other_username not in conversations:
                            conversations[other_username] = {
                                "name": other_user.get("name"),
                                "username": other_username,
                                "last_message": message.get("content"),
                                "last_message_time": message.get("timestamp"),
                                "is_connected": other_user.get("connected"),
                            }
                        else:
                            if message.get("timestamp") > conversations[
                                other_username
                            ].get("last_message_time", ""):
                                conversations[other_username]["last_message"] = (
                                    message.get("content")
                                )
                                conversations[other_username]["last_message_time"] = (
                                    message.get("timestamp")
                                )
                return list(conversations.values())

            else:
                return []

        except Exception as e:
            return []

    def _build_conversation_list(self, parent: tk.Widget) -> None:
        """
        Build the list of conversations with buttons to access each conversation.
        """

        conversations = self._fetch_conversations()
        print(conversations)
        for widget in parent.winfo_children():
            widget.destroy()

        if conversations == []:
            ttk.Label(
                parent,
                text="Aucune conversation trouvée.",
                font=self.app.ui.font(("Skranji", 12, "italic"))
                or ("Skranji", 12, "italic"),
                background="#1e1e1e",
                foreground="grey",
                anchor=tk.CENTER,
                wraplength=self.S(200),
            ).pack(
                fill=tk.BOTH,
                expand=True,
                padx=self.S(20),
                pady=self.S(20),
            )
            return

        else:
            for conversation in conversations:
                conversation_frame = ttk.Frame(parent, padding=self.S(10))
                conversation_frame.pack(fill=tk.X, expand=True)

                profile_photo = self.app.get_profile_photo(conversation.get("username"))
                label = ttk.Label(
                    conversation_frame,
                    image=profile_photo,
                )
                label.image = profile_photo  # type: ignore
                label.pack(side=tk.LEFT, padx=self.S((0, 10)))

    def _update_list(self, e):
        """
        Update the list of conversations of which the username starts with the text in the search entry.
        """

        pass

    def _on_logout(self) -> None:
        """
        Handle logout action to log the user out and return to the login screen.
        """

        self.app._logout()
        self._on_return()

    def _on_return(self) -> None:
        """
        Handle return action to go back to the previous frame.
        """

        # Close dialog
        dialog = self.winfo_toplevel()
        if isinstance(dialog, TopLevelWindow):
            dialog.close()
