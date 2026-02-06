"""
Login / register dialog for user authentication.

This module provides the dialog interface for users to log in or register.
"""

from pathlib import Path
from typing import TYPE_CHECKING
from io import BytesIO
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.filedialog as filedialog

import requests
import asyncio
import httpx
import threading
from PIL import Image

if TYPE_CHECKING:
    from gui.app import App
from gui.widgets import TopLevelWindow, TexturedButton

# API base URL
from config import BASE_URL, BASE_FOLDER_PATH


class AccountFrame(ttk.Frame):
    """
    Dialog toplevel for managing account.

    Allows users to:
    - Change account details (e.g., name, password, profile_photo).
    - Log out.
    """

    def __init__(self, parent: tk.Widget, app: "App"):
        """
        Initializes the account management dialog.

        Args:
            parent: The container in which this frame is placed (e.g., dialog body)
            app (App): The main application instance.
        """

        super().__init__(parent)
        self.app = app
        loading = self.app.show_loading("Chargement...")

        # Create canvas and scrollbar for scrollable content
        canvas_frame = ttk.Frame(self)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(80, 20))

        canvas = tk.Canvas(canvas_frame, bg="#1e1e1e", highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Enable mouse wheel scrolling
        def _on_mousewheel(event):
            try:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except tk.TclError:
                # Canvas has been destroyed, binding will be cleaned up
                pass

        self._mousewheel_binding = self.bind_all("<MouseWheel>", _on_mousewheel)

        # Account information
        title = ttk.Label(
            scrollable_frame, text="Informations du compte", style="SubTitle.TLabel"
        )
        title.pack(pady=0)

        # Account management frame
        main_account_frame = self.app.Frame(scrollable_frame, bg="black", bd=1)
        main_account_frame.pack(pady=20, fill=tk.X, padx=20)
        account_frame = self.app.Frame(main_account_frame)
        account_frame.pack(pady=3, padx=3, fill=tk.X)

        self.download_profile_picture()

        # Change profile picture button
        self.change_profile_picture_button = TexturedButton(
            account_frame,
            texture_path=self.profile_picture_path,
            hover_overlay_path=self.app.edit_picture_banner_path,
            overlay_padding=0,
            command=self._on_change_profile_picture,
            width=240,
            height=240,
            bd=2,
            relief=tk.FLAT,
            bg="black",
            takefocus=False,
        )
        self.change_profile_picture_button.pack(pady=(20, 10), padx=10)

        # Change name entry
        self.name_var = tk.StringVar(value=self.app.name)
        self.app.Label(
            account_frame,
            text="Changer le nom d'affichage",
        ).pack(pady=(10, 5), padx=20)
        self.name_entry = ttk.Entry(
            account_frame,
            textvariable=self.name_var,
            font=("Skranji", 14),
            takefocus=True,
            state=tk.NORMAL if self.app.password else tk.DISABLED,
        )
        self.name_entry.pack(pady=(0, 10), padx=20, fill=tk.X)

        # Change password entry
        self.password_var = tk.StringVar(
            value=self.app.password if self.app.password else ""
        )
        self.app.Label(
            account_frame,
            text="Changer le mot de passe",
        ).pack(pady=(10, 5), padx=20)
        self.password_entry = ttk.Entry(
            account_frame,
            textvariable=self.password_var,
            takefocus=True,
            font=("Skranji", 14),
            show="*",
            state=tk.NORMAL if self.app.password else tk.DISABLED,
        )
        self.password_entry.pack(pady=(0, 10), padx=20, fill=tk.X)

        # Edit account button
        self.edit_account_button = self.app.Button(
            account_frame,
            text="Sauvegarder" if self.app.password else "Éditer le compte",
            overlay_path=(
                self.app.save_icon_path
                if self.app.password
                else self.app.edit_icon_path
            ),
            hover_overlay_path=(
                self.app.hovered_save_icon_path
                if self.app.password
                else self.app.hovered_edit_icon_path
            ),
            command=self._on_edit_account,
            takefocus=False,
            state=(
                tk.DISABLED
                if (
                    self.app.password
                    and self.app.name == self.name_var.get()
                    and self.app.password == self.password_var.get()
                )
                else tk.NORMAL
            ),
        )
        self.edit_account_button.pack(pady=(10, 20), padx=20)

        # Return button
        self.return_button = self.app.Button(
            self,
            text="Retour",
            overlay_path=self.app.return_icon_path,
            hover_overlay_path=self.app.hovered_return_icon_path,
            command=self._on_return,
            takefocus=False,
        )
        self.return_button.pack(pady=(0, 20), padx=20, anchor=tk.S)

        # Bind Enter key to login
        self.bind("<Return>", lambda event: self._login())
        self.name_entry.bind("<Return>", lambda event: self._login())
        self.password_entry.bind("<Return>", lambda event: self._login())

        # Bind Tab key to navigate between entries
        self.name_entry.bind(
            "<Tab>", lambda e: (self.password_entry.focus_set(), "break")[1]
        )
        self.password_entry.bind(
            "<Tab>", lambda e: (self.name_entry.focus_set(), "break")[1]
        )

        self.app.hide_loading(loading)

        self.name_entry.bind("<KeyRelease>", self._update_button)
        self.password_entry.bind("<KeyRelease>", self._update_button)

    def _update_button(self, e):
        """
        Update state of self.edit_account_button when we change the name or the password of the user.
        """

        if (
            self.name_var.get() != self.app.name
            or self.password_var.get() != self.app.password
        ):
            self.edit_account_button.config(state=tk.NORMAL)
        else:
            self.edit_account_button.config(state=tk.DISABLED)

    def _on_edit_account(self):
        """
        Give permission to modify the information of the account.
        Check if the user logged in manually or automatically. If automatically,
        open login dialog to login manually.
        """

        if self.app.password:
            self.name_entry.config(state=tk.NORMAL)
            self.password_entry.config(state=tk.NORMAL)
            self.edit_account_button.configure(
                state=tk.DISABLED,
                text="Sauvegarder",
                overlay_path=self.app.save_icon_path,
                hover_overlay_path=self.app.hovered_save_icon_path,
            )

        else:
            self.app._show_login_dialog()

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

    def _login(self) -> None:
        """
        Handle user login action.
        """

        username = self.username_var.get()
        password = self.password_var.get()

        # Check if all fields are filled
        if username == "" or password == "":
            if username == "":
                self.username_entry.configure(highlightbackground="red")
            if password == "":
                self.password_entry.configure(highlightbackground="red")
            self._show_error("Veuillez remplir tous les champs.")
            return
        self.username_entry.configure(highlightcolor="black")
        self.password_entry.configure(highlightcolor="black")

        self.login_button.config(state=tk.DISABLED)

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

        self.app.show_loading("Connexion en cours...")

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
        self.app.hide_loading()
        dialog = self.winfo_toplevel()
        if isinstance(dialog, TopLevelWindow):
            dialog.close()

        self.app.preferences["auth_token"] = self.app.token
        self.app.show_frame_with_loading(LobbyFrame, "Chargement du lobby...")

    def _on_login_error(self, error: str) -> None:
        """
        Appelé dans le thread principal après erreur.
        """
        self.app.hide_loading()
        self.login_button.config(state=tk.NORMAL)
        self.username_entry.configure(highlightbackground="red")
        self.password_entry.configure(highlightbackground="red")
        self._show_error(error)

        # Re-raise dialog above parent after messagebox closes
        dialog = self.winfo_toplevel()
        if isinstance(dialog, tk.Toplevel):
            dialog.lift()
            dialog.focus_set()

        # Reset entries and button for retry
        self.password_var.set("")
        self.username_var.set("")
        self.login_button.config(state=tk.NORMAL)

    def _show_error(self, message: str) -> None:
        """
        Display an error message to the user.

        Args:
            message (str): The error message to display.
        """

        self.error_label.config(text=message)

    def _on_register(self) -> None:
        """
        Switch to registration frame.
        """
        # Get the parent container (dialog body_frame)
        parent = self.master

        # Destroy current frame
        self.destroy()

        # Create and pack the RegisterFrame
        register_frame = RegisterFrame(parent, self.app)  # type: ignore
        register_frame.pack(fill=tk.BOTH, expand=True)

    def _on_return(self) -> None:
        """
        Handle return action to go back to the previous frame.
        """

        # Close dialog
        dialog = self.winfo_toplevel()
        if isinstance(dialog, TopLevelWindow):
            dialog.close()


class UploadProfilePictureFrame(ttk.Frame):
    """
    Frame to upload a new profile picture for the user.
    Allows users to select an image file from their computer and upload it as their new profile picture.

    Allows users to:
    - Select an image file from their computer.
    - Crop and preview the selected image.
    - Upload the new profile picture to the backend API.
    """

    def __init__(self, parent: tk.Widget, app: "App"):
        """
        Initializes the upload profile picture frame.

        Args:
            parent: The container in which this frame is placed (e.g., dialog body)
            app (App): The main application instance.
        """

        super().__init__(parent)
        self.app = app

        # Create UI elements for selecting and uploading profile picture
