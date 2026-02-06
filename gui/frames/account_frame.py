"""
Login / register dialog for user authentication.

This module provides the dialog interface for users to log in or register.
"""

from pathlib import Path
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
        if not new_profile_picture:
            return

        try:
            picture = Image.open(new_profile_picture).convert("RGBA")
        except Exception:
            return

        dialog = TopLevelWindow(self.app, width=420, height=640)
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

    def __init__(
        self,
        parent: tk.Widget,
        app: "App",
        picture: Image.Image,
        on_complete: Callable[[Path], None] | None = None,
    ):
        """
        Initializes the upload profile picture frame.

        Args:
            parent: The container in which this frame is placed (e.g., dialog body)
            app (App): The main application instance.
        """

        super().__init__(parent)
        self.app = app
        self.original_image = picture.convert("RGBA")
        self.on_complete = on_complete

        self.crop_size = 316
        self.canvas_size = 320
        self._drag_start: tuple[int, int] | None = None

        self.canvas = tk.Canvas(
            self,
            width=self.canvas_size,
            height=self.canvas_size,
            bg="#1e1e1e",
            highlightthickness=0,
        )
        self.canvas.pack(pady=20)

        self.error_label = ttk.Label(self, text="", style="Error.TLabel")
        self.error_label.pack(pady=(0, 10))

        button_row = ttk.Frame(self)
        button_row.pack(pady=(0, 20))

        self.cancel_button = self.app.Button(
            button_row,
            text="Annuler",
            width=160,
            height=45,
            command=self._on_cancel,
            takefocus=False,
        )
        self.cancel_button.pack(side=tk.LEFT, padx=10)

        self.upload_button = self.app.Button(
            button_row,
            text="Importer",
            width=160,
            height=45,
            command=self._on_upload,
            takefocus=False,
        )
        self.upload_button.pack(side=tk.LEFT, padx=10)

        self._init_canvas_image()

        self.canvas.bind("<ButtonPress-1>", self._start_drag)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._end_drag)
        self.canvas.bind("<MouseWheel>", self._on_zoom)

    def _init_canvas_image(self) -> None:
        """
        Prepare the canvas image and crop overlay.
        """

        min_scale = max(
            self.crop_size / self.original_image.width,
            self.crop_size / self.original_image.height,
        )
        self._min_scale = min_scale
        self._max_scale = min_scale * 4
        self._scale = min_scale

        self.crop_left = (self.canvas_size - self.crop_size) / 2
        self.crop_top = (self.canvas_size - self.crop_size) / 2
        self.crop_right = self.crop_left + self.crop_size
        self.crop_bottom = self.crop_top + self.crop_size

        self._display_size = (0, 0)
        self._image_id: int | None = None
        self._render_image(center=(self.canvas_size / 2, self.canvas_size / 2))

        self.crop_rect = self.canvas.create_rectangle(
            self.crop_left,
            self.crop_top,
            self.crop_right,
            self.crop_bottom,
            outline="white",
            width=2,
        )

    def _render_image(self, center: tuple[float, float] | None = None) -> None:
        """
        Render the scaled image in the canvas.
        """

        display_width = max(1, int(self.original_image.width * self._scale))
        display_height = max(1, int(self.original_image.height * self._scale))
        self._display_size = (display_width, display_height)
        resized = self.original_image.resize(
            (display_width, display_height), Image.Resampling.LANCZOS
        )
        self._photo = ImageTk.PhotoImage(resized)

        if center is None and self._image_id is not None:
            coords = self.canvas.coords(self._image_id)
            center = (coords[0], coords[1])
        elif center is None:
            center = (self.canvas_size / 2, self.canvas_size / 2)

        center = self._clamp_center(center[0], center[1])

        if self._image_id is None:
            self._image_id = self.canvas.create_image(
                center[0], center[1], image=self._photo
            )
        else:
            self.canvas.itemconfig(self._image_id, image=self._photo)
            self.canvas.coords(self._image_id, center[0], center[1])

        self.canvas.image = self._photo
        if hasattr(self, "crop_rect"):
            self.canvas.tag_raise(self.crop_rect)

    def _clamp_center(self, cx: float, cy: float) -> tuple[float, float]:
        """
        Keep the image covering the crop square.
        """

        half_w = self._display_size[0] / 2
        half_h = self._display_size[1] / 2

        min_cx = self.crop_right - half_w
        max_cx = self.crop_left + half_w
        if min_cx > max_cx:
            min_cx = max_cx = (min_cx + max_cx) / 2

        min_cy = self.crop_bottom - half_h
        max_cy = self.crop_top + half_h
        if min_cy > max_cy:
            min_cy = max_cy = (min_cy + max_cy) / 2

        cx = min(max(cx, min_cx), max_cx)
        cy = min(max(cy, min_cy), max_cy)
        return cx, cy

    def _start_drag(self, event) -> None:
        self._drag_start = (event.x, event.y)

    def _on_drag(self, event) -> None:
        if not self._drag_start or self._image_id is None:
            return

        dx = event.x - self._drag_start[0]
        dy = event.y - self._drag_start[1]
        cx, cy = self.canvas.coords(self._image_id)
        cx, cy = self._clamp_center(cx + dx, cy + dy)
        self.canvas.coords(self._image_id, cx, cy)
        self._drag_start = (event.x, event.y)

    def _end_drag(self, event) -> None:
        self._drag_start = None

    def _on_zoom(self, event) -> None:
        if self._image_id is None:
            return

        direction = 1 if event.delta > 0 else -1
        factor = 1.08 if direction > 0 else 0.92
        new_scale = min(max(self._scale * factor, self._min_scale), self._max_scale)
        if new_scale == self._scale:
            return
        self._scale = new_scale
        self._render_image()

    def _on_cancel(self) -> None:
        dialog = self.winfo_toplevel()
        if isinstance(dialog, TopLevelWindow):
            dialog.close()

    def _on_upload(self) -> None:
        if getattr(self, "_uploading", False):
            return
        self._set_upload_state(True)
        thread = threading.Thread(target=self._upload_worker, daemon=True)
        thread.start()

    def _set_upload_state(self, uploading: bool) -> None:
        self._uploading = uploading
        state = tk.DISABLED if uploading else tk.NORMAL
        self.upload_button.config(state=state)
        self.cancel_button.config(state=state)
        if uploading:
            self.error_label.config(text="Envoi en cours...")

    def _upload_worker(self) -> None:
        try:
            if not self.app.username:
                raise ValueError("Utilisateur non connecté.")

            cropped = self._get_cropped_image()
            buffer = BytesIO()
            cropped.save(buffer, format="WEBP")
            buffer.seek(0)

            response = requests.post(
                f"{BASE_URL}/users/{self.app.username}/profile-picture",
                files={
                    "file": (
                        "profile_picture.webp",
                        buffer.getvalue(),
                        "image/webp",
                    )
                },
                timeout=10,
            )

            if response.status_code not in (200, 201):
                raise ValueError("Erreur lors de l'envoi de l'image.")

            output_path = (
                Path(BASE_FOLDER_PATH)
                / "gui"
                / "images"
                / "profiles"
                / "current_profile_picture.webp"
            )
            output_path.parent.mkdir(parents=True, exist_ok=True)
            cropped.save(output_path, format="WEBP")

            self.app.after(0, lambda: self._on_upload_success(output_path))

        except Exception as exc:
            self.app.after(0, lambda: self._on_upload_error(str(exc)))

    def _on_upload_success(self, output_path: Path) -> None:
        self._set_upload_state(False)
        if self.on_complete:
            self.on_complete(output_path)
        dialog = self.winfo_toplevel()
        if isinstance(dialog, TopLevelWindow):
            dialog.close()

    def _on_upload_error(self, message: str) -> None:
        self._set_upload_state(False)
        self.error_label.config(text=message)

    def _get_cropped_image(self) -> Image.Image:
        if self._image_id is None:
            return self.original_image

        cx, cy = self.canvas.coords(self._image_id)
        display_w, display_h = self._display_size
        display_left = cx - display_w / 2
        display_top = cy - display_h / 2

        crop_left = (self.crop_left - display_left) / self._scale
        crop_top = (self.crop_top - display_top) / self._scale
        crop_right = (self.crop_right - display_left) / self._scale
        crop_bottom = (self.crop_bottom - display_top) / self._scale

        crop_left = max(0, min(self.original_image.width, crop_left))
        crop_top = max(0, min(self.original_image.height, crop_top))
        crop_right = max(0, min(self.original_image.width, crop_right))
        crop_bottom = max(0, min(self.original_image.height, crop_bottom))

        cropped = self.original_image.crop(
            (
                int(round(crop_left)),
                int(round(crop_top)),
                int(round(crop_right)),
                int(round(crop_bottom)),
            )
        )
        return cropped.resize(
            (self.crop_size, self.crop_size), Image.Resampling.LANCZOS
        )
