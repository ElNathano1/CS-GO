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
from gui.widgets import TopLevelWindow

# API base URL
BASE_URL = "https://cs-go-production.up.railway.app"


class LoginFrame(ttk.Frame):
    """
    Dialog toplevel for login and register actions.

    Allows users to log in or create a new account.
    """

    def __init__(self, parent: tk.Widget, app: "App"):
        """
        Initializes the login dialog.

        Args:
            parent: The container in which this frame is placed (e.g., dialog body)
            app (App): The main application instance.
        """

        super().__init__(parent)
        self.app = app

        # Title
        title = ttk.Label(self, text="Connexion", style="Title.TLabel")
        title.pack(pady=(40, 20))

        # Login frame
        main_login_frame = self.app.Frame(self, bg="black", bd=1)
        main_login_frame.pack(pady=20, fill=tk.X, padx=20)
        login_frame = self.app.Frame(main_login_frame)
        login_frame.pack(pady=3, padx=3, fill=tk.X)

        # Username entry
        self.username_var = tk.StringVar()
        self.app.Label(
            login_frame,
            text="Nom d'utilisateur",
        ).pack(pady=(20, 5), padx=20)
        self.username_entry = ttk.Entry(
            login_frame,
            textvariable=self.username_var,
            takefocus=True,
            font=("Skranji", 14),
        )
        self.username_entry.pack(pady=(0, 10), padx=20, fill=tk.X)

        # Password entry
        self.password_var = tk.StringVar()
        self.app.Label(
            login_frame,
            text="Mot de passe",
        ).pack(pady=(10, 5), padx=20)
        self.password_entry = ttk.Entry(
            login_frame,
            textvariable=self.password_var,
            takefocus=True,
            font=("Skranji", 14),
            show="*",
        )
        self.password_entry.pack(pady=(0, 10), padx=20, fill=tk.X)

        # Login button
        self.login_button = self.app.Button(
            login_frame,
            text="Se connecter",
            command=self._login,
            takefocus=False,
        )
        self.login_button.pack(pady=(10, 20), padx=20)

        # Error label
        self.error_label = ttk.Label(
            self,
            text="",
            foreground="red",
        )
        self.error_label.pack(pady=(0, 10), padx=20, fill=tk.X)

        # Register button
        self.register_button = ttk.Button(
            self,
            text="Pas de compte ? S'inscrire",
            command=self._on_register,
            takefocus=False,
            cursor="hand2",
            padding=0,
        )
        self.register_button.pack(pady=10)

        # Return button
        self.return_button = self.app.Button(
            self,
            text="Retour",
            overlay_path=self.app.return_icon_path,
            hover_overlay_path=self.app.hovered_return_icon_path,
            command=self._on_return,
            takefocus=False,
        )
        self.return_button.pack(pady=10, padx=20, anchor=tk.S)

        # Bind Enter key to login
        self.bind("<Return>", lambda event: self._login())
        self.username_entry.bind("<Return>", lambda event: self._login())
        self.password_entry.bind("<Return>", lambda event: self._login())

        # Bind Tab key to navigate between entries
        self.username_entry.bind(
            "<Tab>", lambda e: (self.password_entry.focus_set(), "break")[1]
        )
        self.password_entry.bind(
            "<Tab>", lambda e: (self.username_entry.focus_set(), "break")[1]
        )

    def _login(self) -> None:
        """
        Handle user login action.
        """

        username = self.username_var.get()
        password = self.password_var.get()

        self.login_button.set_disabled(True)

        thread = threading.Thread(
            target=lambda: asyncio.run(self._do_login(username, password))
        )
        thread.start()

    async def _do_login(self, username: str, password: str) -> None:
        """
        Authenticate a user with the backend API using async httpx.

        Args:
            username (str): The username of the user.
            password (str): The password of the user.
        """

        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.post(
                    f"{BASE_URL}/auth/login",
                    params={"username": username, "password": password},
                )

                if response.status_code == 200:
                    data = response.json()
                    self.app.after(0, self._on_login_success, data)
                else:
                    self.app.after(0, self._on_login_error, "Identifiants incorrects")

        except Exception as e:
            self.app.after(0, self._on_login_error, str(e))

    def _on_login_success(self, data: dict) -> None:
        """Appelé dans le thread principal après succès."""
        self.app.token = data["token"]
        self.app.username = data["username"]

        # Fetch full user data to get the name
        self.app._fetch_user_data()

        # Mark user as connected in database
        self.app._mark_user_connected()

        # Notify that username and profile photo have been updated
        self.app.notify_username_updated()
        self.app.notify_profile_photo_updated()

        # Import here to avoid circular dependency at module load time
        from gui.frames import LobbyFrame

        # Close dialog and show lobby
        dialog = self.winfo_toplevel()
        if isinstance(dialog, TopLevelWindow):
            dialog.close()

        self.app.preferences["auth_token"] = self.app.token
        self.app.show_frame(LobbyFrame)

    def _on_login_error(self, error: str) -> None:
        """Appelé dans le thread principal après erreur."""
        self.login_button.set_disabled(False)
        self._show_error(error)

        # Re-raise dialog above parent after messagebox closes
        dialog = self.winfo_toplevel()
        if isinstance(dialog, tk.Toplevel):
            dialog.lift()
            dialog.focus_set()

        # Reset entries and button for retry
        self.password_var.set("")
        self.username_var.set("")
        self.login_button.set_disabled(False)

    def _show_error(self, message: str) -> None:
        """
        Display an error message to the user.

        Args:
            message (str): The error message to display.
        """

        self.error_label.config(text=message)

    def _on_register(self) -> None:
        """
        Handle user registration action.
        """

        # Implementation of registration logic goes here
        pass

    def _on_return(self) -> None:
        """
        Handle return action to go back to the previous frame.
        """

        # Close dialog
        dialog = self.winfo_toplevel()
        if isinstance(dialog, TopLevelWindow):
            dialog.close()
