"""Command-line interface for the Windows manual sync MVP."""

from __future__ import annotations

import argparse
import getpass
import platform
import sys

from clipboard_sync.clipboard import ClipboardError, read_text, write_text
from clipboard_sync.config import ConfigError, load_config
from clipboard_sync.state import StateStore
from clipboard_sync.supabase_client import SupabaseSync, SyncError


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not hasattr(args, "handler"):
        parser.print_help()
        return

    try:
        args.handler(args)
    except (ClipboardError, ConfigError, SyncError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="clipboard-sync-windows",
        description="Manual Windows clipboard sync through Supabase.",
    )
    subparsers = parser.add_subparsers(dest="command")

    login_parser = subparsers.add_parser("login", help="Sign in and register this Windows device.")
    login_parser.add_argument("--email", help="Supabase account email.")
    login_parser.add_argument("--device-name", help="Friendly device name.")
    login_parser.set_defaults(handler=handle_login)

    status_parser = subparsers.add_parser("status", help="Show local login and device state.")
    status_parser.set_defaults(handler=handle_status)

    push_parser = subparsers.add_parser("push", help="Push current Windows clipboard text.")
    push_parser.set_defaults(handler=handle_push)

    pull_parser = subparsers.add_parser("pull", help="Pull latest text and copy it to clipboard.")
    pull_parser.set_defaults(handler=handle_pull)

    logout_parser = subparsers.add_parser("logout", help="Remove local session tokens.")
    logout_parser.set_defaults(handler=handle_logout)

    return parser


def handle_login(args: argparse.Namespace) -> None:
    email = args.email or input("Supabase email: ").strip()
    password = getpass.getpass("Supabase password: ")
    device_name = args.device_name or default_device_name()

    store = StateStore()
    previous_state = store.load()

    sync = SupabaseSync(load_config())
    state = sync.sign_in(email, password)
    state.client_device_key = previous_state.client_device_key
    sync.use_session(state)
    device_id = sync.ensure_windows_device(state, device_name)

    store.save(state)

    print(f"Logged in as {state.user_email}.")
    print(f"Registered Windows device: {device_name} ({device_id}).")


def handle_status(_: argparse.Namespace) -> None:
    store = StateStore()
    state = store.load()

    print(f"State file: {store.path}")
    print(f"Logged in: {'yes' if state.is_logged_in else 'no'}")
    print(f"User: {state.user_email or '-'}")
    print(f"Device name: {state.device_name or '-'}")
    print(f"Device ID: {state.device_id or '-'}")
    print(f"Client device key: {'set' if state.client_device_key else '-'}")


def handle_push(_: argparse.Namespace) -> None:
    store = StateStore()
    state = store.load()

    sync = SupabaseSync(load_config())
    sync.use_session(state)
    if not state.device_id:
        sync.ensure_windows_device(state, default_device_name())
        store.save(state)

    content = read_text()
    item = sync.push_clipboard_text(state, content)

    print(f"Pushed clipboard text ({len(content)} characters).")
    print(f"Clipboard item: {item.id}")


def handle_pull(_: argparse.Namespace) -> None:
    store = StateStore()
    state = store.load()

    sync = SupabaseSync(load_config())
    sync.use_session(state)
    item = sync.pull_latest_clipboard_text()
    write_text(item.content)

    print(f"Pulled clipboard item: {item.id}")
    print(f"Copied {len(item.content)} characters to the Windows clipboard.")


def handle_logout(_: argparse.Namespace) -> None:
    store = StateStore()
    store.clear_session()
    print("Logged out locally. Device key was kept so this install can reuse its device row later.")


def default_device_name() -> str:
    node = platform.node().strip()
    if node:
        return f"{node} Windows"
    return "Windows Device"


if __name__ == "__main__":
    main()
