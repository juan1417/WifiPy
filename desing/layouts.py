from dataclasses import dataclass


@dataclass(frozen=True)
class Layouts:
    modal_width: int = 60
    modal_height: int = 25
    max_networks_visible: int = 15
    padding_horizontal: int = 2
    padding_vertical: int = 1
    signal_bar_width: int = 8
    refresh_interval: int = 10


LAYOUTS = Layouts()
