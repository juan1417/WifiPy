from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Label, LoadingIndicator, Static

from core.backend import ConnectionStatus, Network, WiFiBackend
from core.db import DatabaseManager
from desing.colors import COLORS
from desing.layouts import LAYOUTS
from platformdirs import user_config_dir, user_data_dir
from ui.screens import ConfirmModal, PasswordModal

_UI_DIR = Path(__file__).parent


class StatusBar(Static):
    def __init__(self, backend: WiFiBackend, **kwargs) -> None:
        super().__init__(**kwargs)
        self.backend = backend
        self._last_status: ConnectionStatus | None = None

    def compose(self) -> ComposeResult:
        yield Label(self._get_status_text(), id="status-text")

    def _get_status_text(self, status: ConnectionStatus | None = None) -> str:
        s = status or self._last_status or self.backend.status()
        ip = s.ip or "Sin IP"
        connected_to = s.ssid or "Desconectado"
        return f"Red: {connected_to} | IP: {ip}"

    def update_status(self, status: ConnectionStatus | None = None) -> None:
        if status:
            self._last_status = status
        label = self.query_one("#status-text", Label)
        label.update(self._get_status_text(status))


class WifiApp(App):
    CSS_PATH = str(_UI_DIR / "styles.css")

    BINDINGS = [
        Binding("j", "cursor_down", "↓", show=False),
        Binding("k", "cursor_up", "↑", show=False),
        Binding("g", "cursor_top", "Inicio", show=False),
        Binding("shift+g", "cursor_bottom", "Fin", show=False),
        Binding("enter", "connect", "Conectar"),
        Binding("d", "forget", "Olvidar red"),
        Binding("r", "refresh", "Refrescar"),
        Binding("q", "quit", "Salir"),
        Binding("escape", "quit", "Salir"),
        Binding("question", "help", "Ayuda", show=False),
    ]

    TITLE = "wifiPy"

    def __init__(self) -> None:
        super().__init__()
        self.config_dir = Path(user_config_dir("wifipy"))
        self.data_dir = Path(user_data_dir("wifipy"))
        self.wifi = WiFiBackend()
        self.db: DatabaseManager | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="wifi-modal"):
            yield Static(" wifiPy ", id="header")
            yield DataTable(id="wifi-list")
            with Vertical(id="loading-container"):
                yield LoadingIndicator(id="loading-spinner")
                yield Label("Escaneando redes...", classes="loading-text")
            with Horizontal(id="footer"):
                yield Button("Refrescar", id="refresh-btn", variant="default")
                yield Button("Salir", id="close-btn", variant="error")
            yield StatusBar(self.wifi, id="status-bar")

    def on_mount(self) -> None:
        if not self.wifi.is_available():
            self.notify(
                "No se encontro iwctl ni nmcli",
                severity="error",
                timeout=5,
            )
            return

        table = self.query_one("#wifi-list", DataTable)
        table.add_columns(" ", "SSID", "Senal", "Seguridad")
        table.cursor_type = "row"
        table.add_class("hidden")
        self._load_networks_async()
        self.set_interval(LAYOUTS.refresh_interval, self._auto_refresh)

    def _init_db(self):
        if self.db is None:
            self.db = DatabaseManager(self.data_dir, "default-session-key")

    def _load_networks_async(self) -> None:
        self.run_worker(self._do_scan, thread=True)

    def _do_scan(self) -> None:
        networks = self.wifi.scan()
        status = self.wifi.status()
        self.call_from_thread(self._on_scan_done, networks, status)

    def _on_scan_done(self, networks: list[Network], status: ConnectionStatus) -> None:
        self._populate_table(networks)
        loading = self.query_one("#loading-container")
        loading.add_class("hidden")
        table = self.query_one("#wifi-list", DataTable)
        table.remove_class("hidden")
        status_bar = self.query_one("#status-bar", StatusBar)
        status_bar.update_status(status)

    def _populate_table(self, networks: list[Network]) -> None:
        table = self.query_one("#wifi-list", DataTable)
        table.clear()
        self._init_db()
        db_networks = {n["ssid"]: n for n in (self.db.list_networks() if self.db else [])}

        for net in networks:
            signal_icon = self._signal_icon(net.signal)
            connected = " *" if net.connected else ""
            sec = net.security.value.upper()
            ssid_display = f"{net.ssid}{connected}"
            saved = " [guardada]" if net.ssid in db_networks else ""
            table.add_row(
                signal_icon,
                ssid_display,
                f"{net.signal}%",
                f"{sec}{saved}",
                key=net.ssid,
            )

    def _refresh_networks(self):
        self._load_networks_async()

    def _signal_icon(self, signal: int) -> str:
        if signal >= 75:
            return "****"
        if signal >= 50:
            return "***"
        if signal >= 25:
            return "**"
        return "*"

    def _auto_refresh(self):
        self._load_networks_async()

    def action_refresh(self):
        self._load_networks_async()
        self.notify("Redes actualizadas", timeout=2)

    def action_cursor_down(self) -> None:
        table = self.query_one("#wifi-list", DataTable)
        if table.row_count:
            table.move_cursor(down=1)

    def action_cursor_up(self) -> None:
        table = self.query_one("#wifi-list", DataTable)
        if table.row_count:
            table.move_cursor(up=1)

    def action_cursor_top(self) -> None:
        table = self.query_one("#wifi-list", DataTable)
        if table.row_count:
            table.move_cursor(row=0)

    def action_cursor_bottom(self) -> None:
        table = self.query_one("#wifi-list", DataTable)
        if table.row_count:
            table.move_cursor(row=table.row_count - 1)

    def action_connect(self) -> None:
        table = self.query_one("#wifi-list", DataTable)
        if table.cursor_row is None:
            return
        ssid = table.get_row_at(table.cursor_row)
        if not ssid or not ssid[1]:
            return
        ssid_value = ssid[1].replace(" *", "").replace(" [guardada]", "")
        self._connect_to_ssid(ssid_value)

    def action_help(self) -> None:
        self.notify(
            "j/k: mover | Enter: conectar | d: olvidar | g/G: inicio/fin | r: refrescar | q: salir",
            timeout=8,
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "refresh-btn":
            self.action_refresh()
        elif event.button.id == "close-btn":
            self.exit()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        ssid = event.row_key.value
        if not ssid:
            return
        self._connect_to_ssid(ssid)

    def _connect_to_ssid(self, ssid: str) -> None:
        self._init_db()
        db_net = self.db.get_network(ssid) if self.db else None
        if db_net and db_net.get("security") == "open":
            self._do_connect(ssid, None)
            return

        if db_net and self.db:
            saved_password = self.db.get_password(ssid)
            if saved_password:
                self._do_connect(ssid, saved_password)
                return

        def on_password(password: str | None) -> None:
            if password is not None:
                self._do_connect(ssid, password)

        self.push_screen(PasswordModal(ssid), on_password)

    def _do_connect(self, ssid: str, password: str | None):
        self.notify(f"Conectando a {ssid}...", timeout=3)
        success = self.wifi.connect(ssid, password)

        if success:
            if password and self.db:
                self.db.save_network(ssid, password)
            self.notify(f"Conectado a {ssid}", severity="success", timeout=3)
            self._load_networks_async()
        else:
            self.notify(
                f"Error al conectar a {ssid}",
                severity="error",
                timeout=5,
            )

    def action_forget(self):
        table = self.query_one("#wifi-list", DataTable)
        if table.cursor_row is None:
            return
        ssid = table.get_row_at(table.cursor_row)
        if not ssid or not ssid[1]:
            return

        ssid_value = ssid[1].replace(" *", "").replace(" [guardada]", "")

        def on_confirm(result: bool) -> None:
            if result:
                if self.db:
                    self.db.delete_network(ssid_value)
                self.wifi.forget_network(ssid_value)
                self.notify(f"Red {ssid_value} olvidada", timeout=3)
                self._load_networks_async()

        self.push_screen(
            ConfirmModal(f"Olvidar red '{ssid_value}'?"), on_confirm
        )
