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
from datetime import datetime

if TYPE_CHECKING:
    from gui.app import App
from gui.widgets import TexturedFrame, TopLevelWindow, TexturedButton, clear_image_cache

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
        self._can_scroll_messages = False
        self._conversation_search_job = None

        self.current_conversation_username = None
        self.last_date = ""

        def _pointer_in_widget(target: tk.Widget) -> bool:
            """Return True when the mouse pointer is over target or one of its children."""
            try:
                hovered_widget = self.winfo_containing(
                    self.winfo_pointerx(), self.winfo_pointery()
                )
            except tk.TclError:
                return False

            while hovered_widget is not None:
                if hovered_widget == target:
                    return True
                hovered_widget = hovered_widget.master

            return False

        self.app.register_conversation_cache_callback(self._on_conversations_updated)

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
        entry_frame.grid_columnconfigure(1, weight=0)
        entry_frame.grid_columnconfigure(0, weight=1)

        self.conversation_var = tk.StringVar(value="")
        self.conversation_entry = ttk.Entry(
            entry_frame,
            width=self.S(18),
            textvariable=self.conversation_var,
            font=self.ui.font(("Skranji", 14)) or ("Skranji", 14),
            takefocus=True,
        )
        self.conversation_entry.grid(row=0, column=0, sticky="ew")

        self.new_conversation_button = ttk.Button(
            entry_frame,
            image=self.app.hovered_new_conversation_icon,
            command=self.new_conversation,
            style="Account.TButton",
            takefocus=False,
            cursor="hand2",
        )
        self.new_conversation_button.grid(
            row=0, column=1, sticky="e", padx=(self.S(10), 0)
        )

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
            if not self._can_scroll_conversations or not _pointer_in_widget(
                self.conversations_viewport_frame
            ):
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
        self.message_content_frame = tk.Frame(
            main_message_frame.content_frame,
            bd=0,
            highlightbackground="black",
            highlightcolor="black",
            highlightthickness=self.S(1),
            bg="#1e1e1e",
            takefocus=False,
        )
        self.message_content_frame.pack(
            fill=tk.BOTH,
            expand=True,
            padx=self.S(3),
            pady=self.S(3),
        )

        self.message_content_frame.grid_rowconfigure(0, weight=0)
        self.message_content_frame.grid_rowconfigure(1, weight=1)
        self.message_content_frame.grid_rowconfigure(2, weight=0)
        self.message_content_frame.grid_columnconfigure(0, weight=1)

        # Messages list frame with scrollbar
        self.messages_viewport_frame = ttk.Frame(self.message_content_frame)

        self.messages_canvas = tk.Canvas(
            self.messages_viewport_frame,
            bg="#1e1e1e",
            highlightthickness=0,
            bd=0,
        )
        self.messages_list_frame = ttk.Frame(self.messages_canvas)

        self.messages_list_frame.bind(
            "<Configure>",
            lambda e: self._refresh_messages_canvas_layout(),
        )

        self._messages_scrollable_window = self.messages_canvas.create_window(
            (0, 0), window=self.messages_list_frame, anchor="nw"
        )

        def _on_messages_canvas_configure(event):
            content_height = self.messages_list_frame.winfo_reqheight()
            y_offset = max(0, event.height - content_height)
            self.messages_canvas.itemconfig(
                self._messages_scrollable_window,
                width=event.width,
                height=content_height,
            )
            self.messages_canvas.coords(self._messages_scrollable_window, 0, y_offset)
            self._refresh_messages_canvas_layout()

        self.messages_canvas.bind("<Configure>", _on_messages_canvas_configure)
        self.messages_viewport_frame.bind(
            "<Configure>",
            lambda e: self._refresh_messages_canvas_layout(),
        )

        self.messages_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        def _on_messages_mousewheel(event):
            if not _pointer_in_widget(self.messages_viewport_frame):
                return
            if not self._can_scroll_messages:
                return
            try:
                self.messages_canvas.yview_scroll(
                    int(-1 * (event.delta / 120)), "units"
                )
            except tk.TclError:
                pass
            return "break"

        self.bind_all("<MouseWheel>", _on_messages_mousewheel, add="+")

        self.after(0, self._refresh_messages_canvas_layout)

        self.messages_list_frame.grid_columnconfigure(0, weight=1, uniform="column")
        self.messages_list_frame.grid_columnconfigure(1, weight=1, uniform="column")
        self.messages_list_frame.grid_columnconfigure(2, weight=1, uniform="column")

        # Default message when no conversation is selected
        self.default_message_label = ttk.Label(
            self.message_content_frame,
            text="Sélectionnez une conversation pour voir les messages.",
            font=self.ui.font(("Skranji", 12, "italic")) or ("Skranji", 12, "italic"),
            background="#1e1e1e",
            foreground="grey",
            anchor=tk.CENTER,
            wraplength=self.S(200),
        )
        self.default_message_label.grid(
            row=1,
            column=0,
            columnspan=3,
            sticky="nsew",
            padx=self.S(10),
            pady=self.S(10),
        )

        # Message entry frame
        self.message_entry_frame = ttk.Frame(
            self.message_content_frame,
            style="MessageEntry.TFrame",
        )
        self.message_entry_frame.grid(
            row=2, column=0, sticky="ew", padx=self.S(10), pady=self.S(10)
        )

        # Send message button
        self.send_message_button = ttk.Button(
            self.message_entry_frame,
            image=self.app.send_icon,
            command=self.send_message,
            style="Account.TButton",
            takefocus=False,
            cursor="hand2",
        )
        self.send_message_button.pack(
            side=tk.RIGHT, padx=self.S((5, 10)), pady=self.S(10)
        )

        self.message_text_entry = tk.Text(
            self.message_entry_frame,
            height=1,
            font=self.ui.font(("Skranji", 12)) or ("Skranji", 12),
            wrap=tk.WORD,
            bd=0,
            highlightthickness=0,
            bg="#1e1e1e",
            fg="white",
            insertbackground="white",
            state=tk.DISABLED if not self.current_conversation_username else tk.NORMAL,
        )
        self.message_text_entry.pack(
            fill=tk.X, expand=True, padx=self.S((10, 5)), pady=self.S(10), side=tk.LEFT
        )

        self.message_text_entry.bind("<Return>", lambda e: self.send_message())
        self.message_text_entry.bind(
            "<Shift-Return>", lambda e: self.message_text_entry.insert(tk.INSERT, "\n")
        )
        self.message_text_entry.bind("<KeyRelease>", self._on_message_entry_change)
        self.message_text_entry.bind(
            "<FocusIn>",
            lambda e: (
                self.message_entry_frame.configure(style="MessageEntryFocused.TFrame")
                if self.message_text_entry["state"] == tk.NORMAL
                else None
            ),
        )
        self.message_text_entry.bind(
            "<FocusOut>",
            lambda e: self.message_entry_frame.configure(style="MessageEntry.TFrame"),
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

        self.conversation_entry.bind("<KeyRelease>", self._update_list)

    def _on_message_entry_change(self, event) -> None:
        """
        Adjust the height of the message entry based on its content.
        """

        content = self.message_text_entry.get("1.0", tk.END)
        lines = content.splitlines()
        num_lines = len(lines)
        new_height = min(max(num_lines, 1), 5)  # Limit height between 1 and 5 lines
        self.message_text_entry.configure(height=new_height)

    def _get_filtered_conversations(self) -> list[dict]:
        """Return conversations from the app cache, filtered by the search text."""

        return self.app.get_cached_conversations(self.conversation_entry.get())

    def _set_conversation_row_hover(
        self,
        conversation_frame: ttk.Frame,
        profile_photo_label: ttk.Label,
        profile_name_label: ttk.Label,
        last_message_label: ttk.Label,
        timestamp_label: ttk.Label,
        unread_icon_label: ttk.Label | None,
        unread: bool,
        hovered: bool,
    ) -> None:
        """Apply hover styles to an entire conversation row."""

        conversation_frame.configure(
            style="ConversationHover.TFrame" if hovered else "Conversation.TFrame"
        )
        profile_photo_label.configure(
            style="ConversationHover.TLabel" if hovered else "Conversation.TLabel"
        )
        profile_name_label.configure(
            style=(
                "AccountConversationHover.TLabel"
                if hovered
                else "AccountConversation.TLabel"
            )
        )

        body_style = "ConversationUnread.TLabel" if unread else "Conversation.TLabel"
        hover_body_style = (
            "ConversationUnreadHover.TLabel" if unread else "ConversationHover.TLabel"
        )
        last_message_label.configure(style=hover_body_style if hovered else body_style)
        timestamp_label.configure(style=hover_body_style if hovered else body_style)

        if unread_icon_label is not None:
            unread_icon_label.configure(
                style=("ConversationHover.TLabel" if hovered else "Conversation.TLabel")
            )

    def _bind_conversation_row_hover(
        self,
        widgets: list[tk.Widget],
        on_enter,
        on_leave,
    ) -> None:
        """Bind hover enter/leave to the row container and all its children."""

        for widget in widgets:
            widget.bind("<Enter>", on_enter, add="+")
            widget.bind("<Leave>", on_leave, add="+")

    def _build_conversation_list(self, parent: tk.Widget) -> None:
        """
        Build the list of conversations with buttons to access each conversation.
        """

        conversations = self._get_filtered_conversations()

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

                conversation_frame = ttk.Frame(
                    parent, cursor="hand2", style="Conversation.TFrame"
                )
                conversation_frame.pack(fill=tk.X, expand=False)

                conversation_frame.grid_rowconfigure(0, weight=1)
                conversation_frame.grid_rowconfigure(1, weight=1)
                conversation_frame.grid_columnconfigure(0, weight=0)
                conversation_frame.grid_columnconfigure(1, weight=1)
                conversation_frame.grid_columnconfigure(2, weight=0)

                profile_photo = self.app.get_profile_photo(
                    conversation.get("username"), for_current_player=False
                )
                name = conversation.get("name", conversation.get("username"))

                conversation_frame.bind(
                    "<Button-1>",
                    lambda e, username=conversation.get(
                        "username", ""
                    ), profile_photo=profile_photo, name=name: self.open_conversation(
                        username, profile_photo, name  # type: ignore
                    ),
                )

                profile_photo_label = ttk.Label(
                    conversation_frame,
                    image=profile_photo,
                    takefocus=False,
                    style="Conversation.TLabel",
                )
                self._conversation_profile_images.append(profile_photo)
                profile_photo_label.grid(
                    row=0,
                    column=0,
                    rowspan=2,
                    padx=self.S(10),
                    pady=self.S(10),
                    sticky="w",
                )

                unread_count = conversation.get("unread_count", 0)
                unread = unread_count > 0

                profile_name_label = ttk.Label(
                    conversation_frame,
                    text=name,  # type: ignore
                    takefocus=False,
                    style=("AccountConversation.TLabel"),
                )
                profile_name_label.grid(
                    row=0,
                    column=1,
                    padx=(0, self.S(10)),
                    pady=(self.S(10), self.S(2)),
                    sticky="w",
                )

                last_message_label = ttk.Label(
                    conversation_frame,
                    text=conversation.get("last_message", "")[:50] + ("..." if len(conversation.get("last_message", "")) > 50 else ""),  # type: ignore
                    takefocus=False,
                    style=(
                        "Conversation.TLabel"
                        if not unread
                        else "ConversationUnread.TLabel"
                    ),
                )
                last_message_label.grid(
                    row=1,
                    column=1,
                    columnspan=2,
                    padx=(0, self.S(10)),
                    pady=(self.S(2), self.S(10)),
                    sticky="w",
                )

                timestamp = conversation.get("timestamp", "")
                date = timestamp.split("T")[0] if "T" in timestamp else timestamp
                time = (
                    timestamp.split("T")[1].split(".")[0][:5]
                    if "T" in timestamp
                    else ""
                )

                if date and date == datetime.today().isoformat().split("T")[0]:
                    timestamp = time
                elif date:
                    timestamp = date[8:10] + "/" + date[5:7]

                timestamp_label = ttk.Label(
                    conversation_frame,
                    text=timestamp,
                    takefocus=False,
                    style=(
                        "Conversation.TLabel"
                        if not unread
                        else "ConversationUnread.TLabel"
                    ),
                )
                timestamp_label.grid(
                    row=0,
                    column=2,
                    padx=(0, self.S(10)),
                    pady=(self.S(10), self.S(2)),
                    sticky="e",
                )

                if unread:
                    unread_icon_label = ttk.Label(
                        conversation_frame,
                        image=self.app.unread_icon,
                        takefocus=False,
                        style="Conversation.TLabel",
                    )
                    unread_icon_label.grid(
                        row=1,
                        column=2,
                        padx=(0, self.S(10)),
                        pady=(self.S(2), self.S(10)),
                        sticky="e",
                    )
                else:
                    unread_icon_label = None

                self._set_conversation_row_hover(
                    conversation_frame,
                    profile_photo_label,
                    profile_name_label,
                    last_message_label,
                    timestamp_label,
                    unread_icon_label,
                    unread,
                    False,
                )

                def _on_enter(
                    _event,
                    row_frame=conversation_frame,
                    photo_label=profile_photo_label,
                    name_label=profile_name_label,
                    message_label=last_message_label,
                    time_label=timestamp_label,
                    unread_label=unread_icon_label,
                    has_unread=unread,
                ):
                    self._set_conversation_row_hover(
                        row_frame,
                        photo_label,
                        name_label,
                        message_label,
                        time_label,
                        unread_label,
                        has_unread,
                        True,
                    )

                def _on_leave(
                    _event,
                    row_frame=conversation_frame,
                    photo_label=profile_photo_label,
                    name_label=profile_name_label,
                    message_label=last_message_label,
                    time_label=timestamp_label,
                    unread_label=unread_icon_label,
                    has_unread=unread,
                ):
                    self._set_conversation_row_hover(
                        row_frame,
                        photo_label,
                        name_label,
                        message_label,
                        time_label,
                        unread_label,
                        has_unread,
                        False,
                    )

                row_widgets = [
                    conversation_frame,
                    profile_photo_label,
                    profile_name_label,
                    last_message_label,
                    timestamp_label,
                ]
                if unread_icon_label is not None:
                    row_widgets.append(unread_icon_label)
                self._bind_conversation_row_hover(row_widgets, _on_enter, _on_leave)

    def _update_list(self, e):
        """
        Update the list of conversations of which the username starts with the text in the search entry.
        """

        if self._conversation_search_job is not None:
            try:
                self.after_cancel(self._conversation_search_job)
            except tk.TclError:
                pass

        self._conversation_search_job = self.after(
            150, self._refresh_conversation_list_from_search
        )

    def _refresh_conversation_list_from_search(self) -> None:
        """Refresh the conversation list after the search debounce delay."""

        self._conversation_search_job = None
        if not self.winfo_exists():
            return

        self._build_conversation_list(self.scrollable_conversations_list_frame)
        self._refresh_conversation_canvas_layout()

    def _on_conversations_updated(self) -> None:
        """Refresh the conversation list when the application cache changes."""

        if not self.winfo_exists():
            return

        self._build_conversation_list(self.scrollable_conversations_list_frame)
        self._refresh_conversation_canvas_layout()

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
            self.conversations_canvas.configure(yscrollcommand=None)  # type: ignore

    def _refresh_messages_canvas_layout(self) -> None:
        """Resize messages canvas to content and toggle scrolling only on overflow."""
        if not self.winfo_exists():
            return

        try:
            self.update_idletasks()
        except tk.TclError:
            return

        max_height = self.messages_viewport_frame.winfo_height()
        max_width = self.messages_viewport_frame.winfo_width()
        content_height = self.messages_list_frame.winfo_reqheight()

        if max_height <= 1:
            return

        y_offset = max(0, max_height - content_height)

        self.messages_canvas.itemconfig(
            self._messages_scrollable_window,
            width=max(max_width, 1),
            height=content_height,
        )
        self.messages_canvas.coords(self._messages_scrollable_window, 0, y_offset)

        self.messages_canvas.configure(scrollregion=self.messages_canvas.bbox("all"))

        self._can_scroll_messages = content_height > max_height
        if not self._can_scroll_messages:
            self.messages_canvas.yview_moveto(0)

    def _scroll_messages_to_bottom(self) -> None:
        """Scroll the messages canvas to the latest message."""
        if not self.winfo_exists():
            return

        try:
            self._refresh_messages_canvas_layout()
            self.messages_canvas.yview_moveto(1.0)
        except tk.TclError:
            return

    def open_conversation(
        self, username: str, user_profile_photo: ImageTk.PhotoImage, name: str
    ) -> None:
        """
        Open a conversation with the specified username.

        Args:
            username (str): The username of the user to open a conversation with.
        """

        self.current_conversation_username = username
        self.message_text_entry.configure(
            state=tk.NORMAL if self.current_conversation_username else tk.DISABLED
        )
        self.message_text_entry.delete("1.0", tk.END)
        self._refresh_conversation_canvas_layout()

        self.build_messages_from_conversation(user_profile_photo, name)
        self._refresh_messages_canvas_layout()

    def build_messages_from_conversation(
        self, user_profile_photo: ImageTk.PhotoImage, name: str
    ) -> None:
        """
        Fetch and display messages from the specified conversation.

        Args:
            user_profile_photo (ImageTk.PhotoImage): The profile photo of the user.
            name (str): The name of the user to open a conversation with.
        """

        profile_photo = self.app.get_profile_photo()
        self.profile_photo = profile_photo

        for widget in self.message_content_frame.grid_slaves(row=0):
            widget.grid_forget()

        # Descriptive labels for the conversation
        descriptive_frame = ttk.Frame(self.message_content_frame)
        descriptive_frame.grid(
            row=0, column=0, sticky="nsew", padx=self.S(10), pady=self.S(10)
        )

        profile_photo_label = ttk.Label(
            descriptive_frame,
            image=user_profile_photo,
            takefocus=False,
            style="Conversation.TLabel",
        )
        profile_photo_label.pack(side=tk.LEFT, padx=self.S((0, 10)))
        profile_name_label = ttk.Label(
            descriptive_frame,
            text=name,
            takefocus=False,
            style=("AccountConversation.TLabel"),
        )
        profile_name_label.pack(side=tk.LEFT, padx=self.S((0, 10)))

        response = requests.get(
            f"{BASE_URL}/messages/{self.app.username}",
            timeout=5,
        )
        if response.status_code != 200:
            pass

        messages = response.json().get(self.current_conversation_username, [])
        messages.sort(key=lambda x: x.get("timestamp", ""))

        if not messages:

            if self.messages_viewport_frame.winfo_ismapped():
                self.messages_viewport_frame.grid_remove()
                self.default_message_label.grid(
                    row=1, column=0, sticky="nsew", padx=self.S(10), pady=self.S(10)
                )
            self.default_message_label.configure(
                text="Aucun message dans cette conversation."
            )

            return

        if self.default_message_label.winfo_ismapped():
            self.default_message_label.grid_remove()
            self.messages_viewport_frame.grid(
                row=1, column=0, sticky="nsew", padx=self.S(10), pady=self.S(10)
            )

        for widget in self.messages_list_frame.winfo_children():
            widget.destroy()

        self.last_date = ""
        for message in messages:
            if message.get("send"):
                self.sent_message(message, profile_photo)
            else:
                self.received_message(message, user_profile_photo)

        self.after_idle(self._scroll_messages_to_bottom)

    def sent_message(
        self, message: dict[str, str | bool], profile_photo: ImageTk.PhotoImage
    ) -> None:
        """
        Draw a new sent message in the messages list frame.
        """
        row_index = self.messages_list_frame.grid_size()[1]
        texture = self.app.light_wood_texture
        foreground = "black"

        date_str = (
            message.get("timestamp", "").split("T")[0]  # type: ignore
            if "T" in message.get("timestamp", "")  # type: ignore
            else ""
        )
        hour_str = (
            message.get("timestamp", "").split("T")[1]  # type: ignore
            if "T" in message.get("timestamp", "")  # type: ignore
            else ""
        )
        if date_str == datetime.today().isoformat().split("T")[0]:
            date_str = "Aujourd'hui"

        if self.last_date == "" or self.last_date != date_str:
            self.last_date = date_str
            date_label = ttk.Label(
                self.messages_list_frame,
                text=self.last_date,
                takefocus=False,
                style="Conversation.TLabel",
                anchor=tk.CENTER,
                justify=tk.CENTER,
            )
            date_label.grid(
                row=row_index,
                column=0,
                columnspan=3,
                sticky="ew",
                pady=self.S(10),
            )
            row_index += 1

        main_message_frame = self.app.Frame(
            self.messages_list_frame, texture_path=texture, bg="black", bd=1
        )
        main_message_frame.grid(
            row=row_index,
            column=1,
            columnspan=2,
            sticky="ew",
            pady=self.S(10),
        )
        message_frame = self.app.Frame(main_message_frame, texture_path=texture)
        message_frame.pack(
            pady=self.S(3),
            padx=self.S(3),
            fill=tk.BOTH,
            expand=True,
        )

        up_frame = self.app.Frame(message_frame, texture_path=texture, bd=0)
        up_frame.pack(
            pady=self.S(3),
            padx=self.S(3),
            fill=tk.X,
            expand=True,
        )
        profile_photo_label = self.app.Label(
            up_frame,
            image=profile_photo,
            takefocus=False,
        )
        profile_photo_label.pack(side=tk.LEFT, padx=self.S((0, 3)))

        hour_label = self.app.Label(
            up_frame,
            text=hour_str.split(".")[0][:5] if hour_str else "",
            text_color=foreground,
            takefocus=False,
        )
        hour_label.pack(side=tk.RIGHT, padx=self.S((0, 3)))

        content_label = self.app.Label(
            message_frame,
            text=message.get("content", ""),  # type: ignore
            text_color=foreground,
            takefocus=False,
            wraplength=self.S(400),
        )
        content_label.pack(anchor=tk.NW, padx=self.S(3), pady=self.S(3))

    def received_message(
        self, message: dict[str, str | bool], profile_photo: ImageTk.PhotoImage
    ) -> None:
        """
        Draw a new received message in the messages list frame.
        """
        row_index = self.messages_list_frame.grid_size()[1]
        texture = self.app.dark_wood_texture
        foreground = "white"

        date_str = (
            message.get("timestamp", "").split("T")[0]  # type: ignore
            if "T" in message.get("timestamp", "")  # type: ignore
            else ""
        )
        hour_str = (
            message.get("timestamp", "").split("T")[1]  # type: ignore
            if "T" in message.get("timestamp", "")  # type: ignore
            else ""
        )
        if date_str == datetime.today().isoformat().split("T")[0]:
            date_str = "Aujourd'hui"

        if self.last_date == "" or self.last_date != date_str:
            self.last_date = date_str
            date_label = ttk.Label(
                self.messages_list_frame,
                text=self.last_date,
                takefocus=False,
                style="Conversation.TLabel",
                anchor=tk.CENTER,
                justify=tk.CENTER,
            )
            date_label.grid(
                row=row_index,
                column=0,
                columnspan=3,
                sticky="ew",
                pady=self.S(10),
            )
            row_index += 1

        main_message_frame = self.app.Frame(
            self.messages_list_frame, texture_path=texture, bg="black", bd=1
        )
        main_message_frame.grid(
            row=row_index,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=self.S(10),
        )
        message_frame = self.app.Frame(main_message_frame, texture_path=texture)
        message_frame.pack(
            pady=self.S(3),
            padx=self.S(3),
            fill=tk.BOTH,
            expand=True,
        )

        up_frame = self.app.Frame(message_frame, texture_path=texture, bd=0)
        up_frame.pack(
            pady=self.S(3),
            padx=self.S(3),
            fill=tk.X,
            expand=True,
        )
        profile_photo_label = self.app.Label(
            up_frame,
            image=profile_photo,
            takefocus=False,
        )
        profile_photo_label.pack(side=tk.LEFT, padx=self.S((0, 3)))

        hour_label = self.app.Label(
            up_frame,
            text=hour_str.split(".")[0][:5] if hour_str else "",
            text_color=foreground,
            takefocus=False,
        )
        hour_label.pack(side=tk.RIGHT, padx=self.S((0, 3)))

        content_label = self.app.Label(
            message_frame,
            text=message.get("content", ""),  # type: ignore
            text_color=foreground,
            takefocus=False,
            wraplength=self.S(400),
        )
        content_label.pack(anchor=tk.NW, padx=self.S(3), pady=self.S(3))

    def new_conversation(self) -> None:
        """
        Open a dialog to start a new conversation with another user already in friend list.
        """

        pass

        # dialog = TopLevelWindow(self.app, width=835, height=560)
        # frame = NewConversationFrame(
        #     dialog.body_frame,
        #     self.app,
        #     on_complete=self._on_new_conversation_created,
        # )
        # frame.pack(fill=tk.BOTH, expand=True)
        # dialog.show(wait=False)

    def send_message(self) -> None:
        """
        Send a message to the currently open conversation.
        """

        if not self.current_conversation_username:
            return

        message = self.message_text_entry.get("1.0", tk.END).strip()
        if not message or message == "":
            return

        response = requests.post(
            f"{BASE_URL}/messages/{self.app.username}",
            json={
                "recipient_username": self.current_conversation_username,
                "timestamp": "string",
                "content": message,
                "type": "message",
            },
        )

        if response.status_code == 200:
            response_data = response.json()
            print(f"Message sent successfully: {response_data}")
            message = response_data.get("message", {})
            self.message_text_entry.delete("1.0", tk.END)
            self._refresh_conversation_canvas_layout()

            self.sent_message(
                message,
                self.profile_photo,
            )

            self._refresh_messages_canvas_layout()

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

    def destroy(self) -> None:
        self.app.unregister_conversation_cache_callback(self._on_conversations_updated)
        super().destroy()

    def _on_return(self) -> None:
        """
        Handle return action to go back to the previous frame.
        """

        # Close dialog
        dialog = self.winfo_toplevel()
        if isinstance(dialog, TopLevelWindow):
            dialog.close()
