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
        self._conversation_profile_images: list[ImageTk.PhotoImage] = []
        self._can_scroll_conversations = False
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

        self.conversation_var = tk.StringVar(value="")
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

        # Add a button to start a new conversation
        self.new_conversation_button = self.app.Button(
            canvas_frame,
            text="Nouvelle conversation",
        )
        self.new_conversation_button.pack(
            pady=self.S(10),
            padx=self.S(10),
            anchor=tk.N,
        )

        # Create canvas and scrollbar for scrollable content
        self.conversations_viewport_frame = ttk.Frame(canvas_frame)
        self.conversations_viewport_frame.pack(fill=tk.BOTH, expand=True)

        self.conversations_canvas = tk.Canvas(
            self.conversations_viewport_frame,
            bg="#1e1e1e",
            highlightthickness=0,
        )
        self.conversations_scrollbar = ttk.Scrollbar(
            self.conversations_viewport_frame,
            orient="vertical",
            command=self.conversations_canvas.yview,
        )
        self.scrollable_conversations_list_frame = ttk.Frame(self.conversations_canvas)

        self.scrollable_conversations_list_frame.bind(
            "<Configure>",
            lambda e: self._refresh_conversation_canvas_layout(),
        )

        self._scrollable_window = self.conversations_canvas.create_window(
            (0, 0), window=self.scrollable_conversations_list_frame, anchor="n"
        )
        self.conversations_canvas.configure(
            yscrollcommand=self.conversations_scrollbar.set
        )

        def _on_canvas_configure(event):
            self.conversations_canvas.itemconfig(
                self._scrollable_window, width=event.width
            )
            self.conversations_canvas.coords(
                self._scrollable_window, event.width / 2, 0
            )
            self._refresh_conversation_canvas_layout()

        self.conversations_canvas.bind("<Configure>", _on_canvas_configure)
        self.conversations_viewport_frame.bind(
            "<Configure>", lambda e: self._refresh_conversation_canvas_layout()
        )

        self.conversations_canvas.pack(
            side=tk.LEFT, fill=tk.X, expand=False, anchor=tk.N
        )

        # Enable mouse wheel scrolling
        def _on_mousewheel(event):
            if not self._can_scroll_conversations:
                return
            try:
                self.conversations_canvas.yview_scroll(
                    int(-1 * (event.delta / 120)), "units"
                )
            except tk.TclError:
                # Canvas has been destroyed, binding will be cleaned up
                pass

        self._mousewheel_binding = self.bind_all("<MouseWheel>", _on_mousewheel)

        self._build_conversation_list(self.scrollable_conversations_list_frame)
        self.after(0, self._refresh_conversation_canvas_layout)

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
                f"{BASE_URL}/messages/{self.app.username}/conversations",
                timeout=5,
            )
            if response.status_code == 200:
                conversations = []

                for username in response.json().keys():

                    user = requests.get(
                        f"{BASE_URL}/users/{username}", timeout=5
                    ).json()

                    if (
                        self.conversation_entry.get().strip()
                        and not username.startswith(
                            self.conversation_entry.get().strip().lower()
                        )
                        and not user.get("name", username)
                        .lower()
                        .startswith(self.conversation_entry.get().strip().lower())
                    ):
                        continue

                    conversation = {
                        "username": username,
                        "name": user.get("name", username),
                        "connected": user.get("connected", False),
                        "last_message": response.json()[username]
                        .get("last_message", "")
                        .get("content", ""),
                        "timestamp": response.json()[username]
                        .get("last_message", "")
                        .get("timestamp", ""),
                        "unread_count": response.json()[username].get(
                            "unread_count", 0
                        ),
                    }
                    conversations.append(conversation)

                return sorted(
                    conversations,
                    key=lambda c: c.get("timestamp", ""),
                    reverse=True,
                )

            else:
                return []

        except Exception as e:
            return []

    def _build_conversation_list(self, parent: tk.Widget) -> None:
        """
        Build the list of conversations with buttons to access each conversation.
        """

        conversations = self._fetch_conversations()

        for widget in parent.winfo_children():
            widget.destroy()

        # Keep strong references to PhotoImage objects used in conversation labels.
        self._conversation_profile_images.clear()

        if not conversations:
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

                conversation_frame = ttk.Frame(parent)
                conversation_frame.pack(fill=tk.X, expand=False)

                profile_photo = self.app.get_profile_photo(
                    conversation.get("username"), for_current_player=False
                )

                profile_photo_label = ttk.Label(
                    conversation_frame,
                    image=profile_photo,
                    takefocus=False,
                )
                self._conversation_profile_images.append(profile_photo)
                profile_photo_label.pack(side=tk.LEFT, padx=(10, 10), pady=5)
                profile_name_label = ttk.Label(
                    conversation_frame,
                    text=conversation.get("name", conversation.get("username")),  # type: ignore
                    takefocus=False,
                )
                profile_name_label.pack(side=tk.LEFT, padx=(0, 10), pady=5)
                last_message_label = ttk.Label(
                    conversation_frame,
                    text=conversation.get("last_message", ""),
                    takefocus=False,
                )
                last_message_label.pack(side=tk.LEFT, padx=(0, 10), pady=5)
                unread_count = conversation.get("unread_count", 0)
                if unread_count > 0:
                    unread_count_label = ttk.Label(
                        conversation_frame,
                        text=f"{unread_count} non lu(s)",
                        foreground="red",
                        takefocus=False,
                    )
                    unread_count_label.pack(side=tk.LEFT, padx=(0, 10), pady=5)

    def _update_list(self, e):
        """
        Update the list of conversations of which the username starts with the text in the search entry.
        """

        self._build_conversation_list(self.scrollable_conversations_list_frame)

    def _refresh_conversation_canvas_layout(self) -> None:
        """Resize conversations canvas to content and toggle scrolling only on overflow."""
        if not self.winfo_exists():
            return

        try:
            self.update_idletasks()
        except tk.TclError:
            return

        max_height = self.conversations_viewport_frame.winfo_height()
        content_height = self.scrollable_conversations_list_frame.winfo_reqheight()

        if max_height <= 1:
            return

        target_height = min(content_height, max_height)
        target_height = max(1, target_height)
        self.conversations_canvas.configure(height=target_height)
        self.conversations_canvas.configure(
            scrollregion=self.conversations_canvas.bbox("all")
        )

        self._can_scroll_conversations = content_height > max_height
        if self._can_scroll_conversations:
            if not self.conversations_scrollbar.winfo_ismapped():
                self.conversations_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            self.conversations_canvas.configure(
                yscrollcommand=self.conversations_scrollbar.set
            )
        else:
            if self.conversations_scrollbar.winfo_ismapped():
                self.conversations_scrollbar.pack_forget()
            self.conversations_canvas.yview_moveto(0)
            self.conversations_canvas.configure(yscrollcommand=None)

    def download_profile_picture(self) -> None:
        """
        Download the user's profile picture from the backend API and save it locally.
        """

        self.profile_picture_path = (
            Path(BASE_FOLDER_PATH)
            / "gui"
            / "images"
            / "profiles"
            / "current_profile_picture.webp"
        )
        default_profile_path = (
            Path(BASE_FOLDER_PATH)
            / "gui"
            / "images"
            / "profiles"
            / "default_profile_photo.png"
        )
        target_size = (236, 236)

        try:
            response = requests.get(
                f"{BASE_URL}/users/{self.app.username}/profile-picture",
                timeout=5,
            )
            if response.status_code == 200:
                image = Image.open(BytesIO(response.content)).convert("RGBA")
            else:
                image = Image.open(default_profile_path).convert("RGBA")

            image = image.resize(target_size, Image.Resampling.LANCZOS)
            image.save(self.profile_picture_path, format="WEBP")

        except Exception:
            try:
                image = Image.open(default_profile_path).convert("RGBA")
                image = image.resize(target_size, Image.Resampling.LANCZOS)
                image.save(self.profile_picture_path, format="WEBP")
            except Exception:
                self.profile_picture_path = default_profile_path

    def _on_change_profile_picture(self) -> None:
        """
        Handle change profile picture action.
        """

        new_profile_picture = filedialog.askopenfilename(
            title="Sélectionner une nouvelle photo de profil",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.webp")],
        )
        if not new_profile_picture:
            return

        try:
            picture = Image.open(new_profile_picture).convert("RGBA")
        except Exception:
            return

        dialog = TopLevelWindow(self.app, width=835, height=560)
        frame = UploadProfilePictureFrame(
            dialog.body_frame,
            self.app,
            picture,
            on_complete=self._on_profile_picture_uploaded,
        )
        frame.pack(fill=tk.BOTH, expand=True)
        dialog.show(wait=False)

    def _on_profile_picture_uploaded(self, picture_path: Path) -> None:
        """
        Refresh the local profile picture preview after a successful upload.
        """

        self.profile_picture_path = picture_path
        clear_image_cache(picture_path)
        self.change_profile_picture_button.configure(texture_path=picture_path)
        self.app.notify_profile_photo_updated()

    async def fetch_account_statistics(self) -> None:
        """
        Fetch the user's account statistics from the backend API.
        """

        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.get(f"{BASE_URL}/games/{self.app.username}")
                if response.status_code == 200:
                    data = response.json()
                    self.account_statistics = {
                        "games_played": len(data),
                        "games_won": sum(
                            1
                            for game in data
                            if game.get("result") == "1-0"
                            and game.get("black_player").get("username")
                            == self.app.username
                            or game.get("result") == "0-1"
                            and game.get("white_player").get("username")
                            == self.app.username
                        ),
                        "recent_games": data[:3],
                    }

                else:
                    pass

        except Exception as e:
            pass

    def _load_statistics_worker(self) -> None:
        asyncio.run(self.fetch_account_statistics())
        self.app.after(0, self._refresh_statistics_ui)

    def _refresh_statistics_ui(self) -> None:
        if not self.winfo_exists():
            return

        self.games_played_label.set_text(
            str(self.account_statistics.get("games_played", "0"))
        )
        self.games_won_label.set_text(
            str(self.account_statistics.get("games_won", "0"))
        )

        for child in self.statistics_frame.grid_slaves():
            row = int(child.grid_info().get("row", 0))
            if row >= 2:
                child.grid_forget()
        self.draw_recent_games(self.statistics_frame)

    def draw_recent_games(self, parent: tk.Widget) -> None:
        """
        Draw a list of the user's 3 most recent games with the result and opponent's name.
        """

        if not self.account_statistics:
            return

        for i in range(len(self.account_statistics.get("recent_games", []))):
            game = self.account_statistics["recent_games"][i]
            color = (
                "blancs"
                if game.get("white_player").get("username") == self.app.username
                else "noirs"
            )
            result = game.get("result", "N/A")
            opponent = (
                game.get("black_player").get("name")
                if game.get("white_player").get("username") == self.app.username
                else game.get("white_player").get("name")
            )
            frame = tk.Frame(
                parent,
                bg=(
                    "green"
                    if result == "1-0"
                    and color == "noirs"
                    or result == "0-1"
                    and color == "blancs"
                    else "red" if result in ["1-0", "0-1"] else "#f6a90d"
                ),
                bd=0,
                relief=tk.FLAT,
            )
            game_label = ttk.Label(
                frame,
                text=f"{"Gagné" if result == "1-0" and color == "noirs" or result == "0-1" and color == "blancs" else "Perdu"} avec les {color} contre {opponent} !",
                font=("Skranji", 8),
                background="#1e1e1e" if color == "noirs" else "white",
                foreground="white" if color == "noirs" else "black",
                anchor=tk.CENTER,
            )
            game_label.pack(fill=tk.BOTH, expand=True, padx=2, pady=2, ipadx=5, ipady=5)
            frame.grid(
                row=2 + i,
                column=0,
                columnspan=2,
                sticky="ew",
                padx=20,
                pady=(
                    (0, 20)
                    if i == len(self.account_statistics.get("recent_games", [])) - 1
                    else (0, 10)
                ),
            )

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
