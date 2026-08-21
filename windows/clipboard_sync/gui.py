"""Tkinter desktop interface for manual Clipboard Sync on Windows."""

from __future__ import annotations

import platform
import tkinter as tk
from concurrent.futures import Future, ThreadPoolExecutor
from tkinter import ttk
from typing import Callable

from clipboard_sync.clipboard import read_text, write_text
from clipboard_sync.config import AppConfig, load_config
from clipboard_sync.state import AppState, StateStore
from clipboard_sync.supabase_client import (
    AuthenticationRequiredError,
    ClipboardItem,
    SupabaseSync,
)


class DesktopController:
    """Share the working CLI services with the desktop interface."""

    def __init__(
        self,
        *,
        store: StateStore | None = None,
        config_loader: Callable[[], AppConfig] = load_config,
        sync_factory: Callable[[AppConfig], SupabaseSync] = SupabaseSync,
        clipboard_reader: Callable[[], str] = read_text,
        clipboard_writer: Callable[[str], None] = write_text,
    ) -> None:
        self.store = store or StateStore()
        self.config_loader = config_loader
        self.sync_factory = sync_factory
        self.clipboard_reader = clipboard_reader
        self.clipboard_writer = clipboard_writer
        self.state = self.store.load()
        self.sync: SupabaseSync | None = None

    @property
    def is_logged_in(self) -> bool:
        return self.state.is_logged_in

    def login(self, email: str, password: str, device_name: str) -> AppState:
        previous_state = self.store.load()
        sync = self.sync_factory(self.config_loader())
        state = sync.sign_in(email.strip(), password)
        state.client_device_key = previous_state.client_device_key
        sync.use_session(state)
        sync.ensure_windows_device(state, device_name)
        self.store.save(state)
        self.sync = sync
        self.state = state
        return state

    def restore(self, device_name: str) -> AppState:
        sync = self.sync_factory(self.config_loader())
        self.sync = sync
        self._use_saved_session()
        sync.ensure_windows_device(self.state, device_name)
        self.store.save(self.state)
        return self.state

    def push(self, device_name: str) -> int:
        sync = self._require_sync()
        self._use_saved_session()
        sync.ensure_windows_device(self.state, device_name)
        self.store.save(self.state)
        content = self.clipboard_reader()
        sync.push_clipboard_text(self.state, content)
        return len(content)

    def pull(self) -> ClipboardItem | None:
        sync = self._require_sync()
        self._use_saved_session()
        item = sync.pull_latest_clipboard_text()
        if item is not None:
            self.clipboard_writer(item.content)
        return item

    def logout(self) -> None:
        self.state = self.store.clear_session()
        self.sync = None

    def _require_sync(self) -> SupabaseSync:
        if self.sync is None:
            raise AuthenticationRequiredError("You are not logged in. Sign in first.")
        return self.sync

    def _use_saved_session(self) -> None:
        sync = self._require_sync()
        try:
            sync.use_session(self.state)
        except AuthenticationRequiredError:
            self.state = self.store.clear_session()
            self.sync = None
            raise
        self.store.save(self.state)


class ClipboardSyncWindow(tk.Tk):
    def __init__(self, controller: DesktopController | None = None) -> None:
        super().__init__()
        self.controller = controller or DesktopController()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="clipboard-sync")
        self.device_name = default_device_name()
        self.email = tk.StringVar(value=self.controller.state.user_email or "")
        self.password = tk.StringVar()
        self.account = tk.StringVar(value="Not signed in")
        self.feedback = tk.StringVar(value="Ready")
        self.busy = False

        self.title("Clipboard Sync")
        self.geometry("520x430")
        self.minsize(480, 390)
        self.configure(background="#eef4ff")
        self.protocol("WM_DELETE_WINDOW", self._close)

        self._configure_style()
        self._build_ui()

        if self.controller.is_logged_in:
            self._show_session(self.controller.state.user_email or "Saved account")
            self._run(
                "Restoring session…",
                lambda: self.controller.restore(self.device_name),
                lambda state: self._session_ready(state, "Device ready."),
            )
        else:
            self._show_login()

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("vista" if "vista" in style.theme_names() else "clam")
        style.configure("App.TFrame", background="#eef4ff")
        style.configure("Card.TFrame", background="#ffffff")
        style.configure("Title.TLabel", background="#eef4ff", foreground="#172554", font=("Segoe UI", 22, "bold"))
        style.configure("Subtitle.TLabel", background="#eef4ff", foreground="#53627c", font=("Segoe UI", 10))
        style.configure("Card.TLabel", background="#ffffff", foreground="#1f2937", font=("Segoe UI", 10))
        style.configure("Account.TLabel", background="#ffffff", foreground="#172554", font=("Segoe UI", 12, "bold"))
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), padding=(14, 9))
        style.configure("Action.TButton", font=("Segoe UI", 10), padding=(12, 9))

    def _build_ui(self) -> None:
        root = ttk.Frame(self, style="App.TFrame", padding=28)
        root.pack(fill="both", expand=True)

        ttk.Label(root, text="Clipboard Sync", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            root,
            text="Manual text transfer through your Supabase account",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(2, 18))

        self.login_card = ttk.Frame(root, style="Card.TFrame", padding=22)
        ttk.Label(self.login_card, text="Email", style="Card.TLabel").pack(anchor="w")
        self.email_entry = ttk.Entry(self.login_card, textvariable=self.email)
        self.email_entry.pack(fill="x", pady=(4, 12))
        ttk.Label(self.login_card, text="Password", style="Card.TLabel").pack(anchor="w")
        self.password_entry = ttk.Entry(self.login_card, textvariable=self.password, show="•")
        self.password_entry.pack(fill="x", pady=(4, 16))
        self.sign_in_button = ttk.Button(
            self.login_card,
            text="Sign In",
            style="Primary.TButton",
            command=self._sign_in,
        )
        self.sign_in_button.pack(fill="x")

        self.session_card = ttk.Frame(root, style="Card.TFrame", padding=22)
        ttk.Label(self.session_card, textvariable=self.account, style="Account.TLabel").pack(anchor="w")
        ttk.Label(self.session_card, text=self.device_name, style="Card.TLabel").pack(anchor="w", pady=(2, 18))
        self.push_button = ttk.Button(
            self.session_card,
            text="Push Current Clipboard",
            style="Primary.TButton",
            command=self._push,
        )
        self.push_button.pack(fill="x", pady=(0, 9))
        self.pull_button = ttk.Button(
            self.session_card,
            text="Pull Latest Text",
            style="Action.TButton",
            command=self._pull,
        )
        self.pull_button.pack(fill="x", pady=(0, 9))
        self.logout_button = ttk.Button(
            self.session_card,
            text="Log Out",
            style="Action.TButton",
            command=self._logout,
        )
        self.logout_button.pack(fill="x")

        self.progress = ttk.Progressbar(root, mode="indeterminate")
        self.progress.pack(fill="x", pady=(18, 8))
        self.progress.pack_forget()
        self.feedback_label = ttk.Label(root, textvariable=self.feedback, style="Subtitle.TLabel", wraplength=450)
        self.feedback_label.pack(anchor="w")

    def _sign_in(self) -> None:
        email = self.email.get().strip()
        password = self.password.get()
        if not email or not password:
            self._set_feedback("Enter your email and password.", error=True)
            return

        self._run(
            "Signing in…",
            lambda: self.controller.login(email, password, self.device_name),
            lambda state: self._session_ready(state, "Signed in. Device ready."),
        )

    def _push(self) -> None:
        self._run(
            "Pushing clipboard text…",
            lambda: self.controller.push(self.device_name),
            lambda length: self._set_feedback(f"Pushed {length} characters."),
        )

    def _pull(self) -> None:
        self._run(
            "Pulling latest text…",
            self.controller.pull,
            lambda item: self._set_feedback(
                "No synced text yet. Windows clipboard was not changed."
                if item is None
                else f"Pulled {len(item.content)} characters to the Windows clipboard."
            ),
        )

    def _logout(self) -> None:
        self.controller.logout()
        self.password.set("")
        self._show_login()
        self._set_feedback("Logged out. This installation's device key was kept.")

    def _run(self, message: str, work: Callable[[], object], success: Callable[[object], None]) -> None:
        if self.busy:
            return
        self._set_busy(True)
        self._set_feedback(message)
        future = self.executor.submit(work)
        self.after(50, self._poll_future, future, success)

    def _poll_future(self, future: Future[object], success: Callable[[object], None]) -> None:
        if not future.done():
            self.after(50, self._poll_future, future, success)
            return
        self._finish(future, success)

    def _finish(self, future: Future[object], success: Callable[[object], None]) -> None:
        self._set_busy(False)
        try:
            result = future.result()
        except Exception as error:
            if isinstance(error, AuthenticationRequiredError):
                self._show_login()
            self._set_feedback(str(error) or "Something went wrong. Please try again.", error=True)
            return
        success(result)

    def _session_ready(self, state: AppState, message: str) -> None:
        self.password.set("")
        self._show_session(state.user_email or "Signed-in user")
        self._set_feedback(message)

    def _show_login(self) -> None:
        self.session_card.pack_forget()
        self.login_card.pack(fill="x")
        self.account.set("Not signed in")
        self.email_entry.focus_set()
        self._update_buttons()

    def _show_session(self, email: str) -> None:
        self.login_card.pack_forget()
        self.session_card.pack(fill="x")
        self.account.set(email)
        self._update_buttons()

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        if busy:
            self.progress.pack(fill="x", pady=(18, 8), before=self.feedback_label)
            self.progress.start(12)
        else:
            self.progress.stop()
            self.progress.pack_forget()
        self._update_buttons()

    def _update_buttons(self) -> None:
        state = "disabled" if self.busy else "normal"
        self.sign_in_button.configure(state=state)
        self.push_button.configure(state=state)
        self.pull_button.configure(state=state)
        self.logout_button.configure(state=state)

    def _set_feedback(self, message: str, *, error: bool = False) -> None:
        self.feedback.set(message)
        self.feedback_label.configure(foreground="#b42318" if error else "#2563a6")

    def _close(self) -> None:
        self.executor.shutdown(wait=False, cancel_futures=True)
        self.destroy()


def default_device_name() -> str:
    node = platform.node().strip()
    return f"{node} Windows" if node else "Windows Device"


def main() -> None:
    ClipboardSyncWindow().mainloop()


if __name__ == "__main__":
    main()
