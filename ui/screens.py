from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Grid, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label


class PasswordModal(ModalScreen[str | None]):
    CSS = """
    PasswordModal {
        align: center middle;
    }
    #dialog {
        grid-size: 2 3;
        grid-gutter: 1 2;
        width: 50;
        height: auto;
        border: solid #3b4261;
        background: #24283b;
        padding: 1 2;
    }
    #title {
        column-span: 2;
        content-align: center middle;
        text-style: bold;
        color: #c0caf5;
        height: 2;
    }
    #pw-label {
        content-align: right middle;
        color: #a9b1d6;
    }
    #password-input {
        width: 100%;
    }
    #connect-btn {
        background: #9ece6a;
        color: #1a1b26;
    }
    #cancel-btn {
        background: #f7768e;
        color: #1a1b26;
    }
    """

    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, ssid: str) -> None:
        super().__init__()
        self.ssid = ssid

    def compose(self) -> ComposeResult:
        yield Grid(
            Label(f"Conectar a {self.ssid}", id="title"),
            Label("Clave:", id="pw-label"),
            Input(
                password=True,
                placeholder="Contraseña WiFi...",
                id="password-input",
            ),
            Button("Conectar", variant="success", id="connect-btn"),
            Button("Cancelar", variant="error", id="cancel-btn"),
            id="dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "connect-btn":
            password = self.query_one("#password-input", Input).value
            self.dismiss(password)
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "password-input":
            self.dismiss(event.value)

    def action_cancel(self) -> None:
        self.dismiss(None)


class ConfirmModal(ModalScreen[bool]):
    CSS = """
    ConfirmModal {
        align: center middle;
    }
    #dialog {
        width: 40;
        height: auto;
        border: solid #3b4261;
        background: #24283b;
        padding: 1 2;
        layout: vertical;
    }
    #msg {
        text-style: bold;
        color: #c0caf5;
        text-align: center;
        margin: 0 0 1 0;
    }
    #btns {
        height: auto;
        align: center middle;
    }
    """

    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(self.message, id="msg")
            with Horizontal(id="btns"):
                yield Button("Si", variant="success", id="yes-btn")
                yield Button("No", variant="error", id="no-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "yes-btn")

    def action_cancel(self) -> None:
        self.dismiss(False)
