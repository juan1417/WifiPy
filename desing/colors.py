from dataclasses import dataclass


@dataclass(frozen=True)
class Colors:
    bg_primary: str = "#1a1b26"
    bg_secondary: str = "#24283b"
    bg_card: str = "#2f3347"
    bg_hover: str = "#3b4261"

    text_primary: str = "#c0caf5"
    text_secondary: str = "#a9b1d6"
    text_dim: str = "#565f89"

    accent_green: str = "#9ece6a"
    accent_yellow: str = "#e0af68"
    accent_red: str = "#f7768e"
    accent_blue: str = "#7aa2f7"
    accent_cyan: str = "#7dcfff"

    signal_strong: str = "#9ece6a"
    signal_medium: str = "#e0af68"
    signal_weak: str = "#f7768e"

    border: str = "#3b4261"
    border_active: str = "#7aa2f7"


COLORS = Colors()
