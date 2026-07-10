import re
import shutil
import subprocess
from dataclasses import dataclass
from enum import Enum

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


class BackendType(Enum):
    IWD = "iwd"
    NMCLI = "nmcli"
    NONE = "none"


class SecurityType(Enum):
    OPEN = "open"
    WPA2 = "wpa2"
    WPA3 = "wpa3"
    UNKNOWN = "unknown"


@dataclass
class Network:
    ssid: str
    signal: int
    security: SecurityType
    connected: bool = False


@dataclass
class ConnectionStatus:
    connected: bool
    ssid: str | None
    ip: str | None
    interface: str | None


def _parse_signal_iwd(bars: str) -> int:
    mapping = {"": 0, "*": 25, "**": 50, "***": 75, "****": 100}
    return mapping.get(bars.strip(), 0)


def _parse_security_iwd(sec: str) -> SecurityType:
    sec_lower = sec.strip().lower()
    if "open" in sec_lower:
        return SecurityType.OPEN
    if "sae" in sec_lower:
        return SecurityType.WPA3
    if "psk" in sec_lower or "wpa" in sec_lower:
        return SecurityType.WPA2
    return SecurityType.UNKNOWN


def _parse_security_nmcli(sec: str) -> SecurityType:
    sec_upper = sec.strip().upper()
    if not sec_upper or sec_upper == "--":
        return SecurityType.OPEN
    if "SAE" in sec_upper:
        return SecurityType.WPA3
    if "WPA" in sec_upper:
        return SecurityType.WPA2
    return SecurityType.UNKNOWN


def _run(cmd: list[str], timeout: int = 10) -> tuple[bool, str, str]:
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        return (
            result.returncode == 0,
            _strip_ansi(result.stdout.strip()),
            _strip_ansi(result.stderr.strip()),
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False, "", ""


class WiFiBackend:
    def __init__(self):
        self.backend = self._detect_backend()
        self._device: str | None = None
        if self.backend == BackendType.IWD:
            self._device = self._get_iwd_device()

    def _detect_backend(self) -> BackendType:
        has_iwctl = shutil.which("iwctl") is not None
        has_nmcli = shutil.which("nmcli") is not None

        if has_nmcli and self._nmcli_has_wifi():
            return BackendType.NMCLI
        if has_iwctl:
            return BackendType.IWD
        if has_nmcli:
            return BackendType.NMCLI
        return BackendType.NONE

    def _nmcli_has_wifi(self) -> bool:
        ok, output, _ = _run(["nmcli", "-t", "-f", "DEVICE,TYPE", "device", "status"])
        if not ok:
            return False
        for line in output.splitlines():
            parts = line.split(":")
            if len(parts) == 2 and parts[1] == "wifi":
                return True
        return False

    def _get_iwd_device(self) -> str | None:
        ok, output, _ = _run(["iwctl", "device", "list"])
        if not ok:
            return None
        for line in output.splitlines():
            if re.search(r"\bwlan\w*\b", line, re.IGNORECASE):
                parts = line.split()
                if parts:
                    return parts[0]
        return None

    def _get_nmcli_interface(self) -> str | None:
        ok, output, _ = _run(["nmcli", "-t", "-f", "DEVICE,TYPE", "device", "status"])
        if not ok:
            return None
        for line in output.splitlines():
            parts = line.split(":")
            if len(parts) == 2 and parts[1] == "wifi":
                return parts[0]
        return None

    def get_device(self) -> str | None:
        if self.backend == BackendType.IWD:
            return self._device
        if self.backend == BackendType.NMCLI:
            return self._get_nmcli_interface()
        return None

    def is_available(self) -> bool:
        return self.backend != BackendType.NONE

    def scan(self) -> list[Network]:
        if self.backend == BackendType.IWD:
            return self._scan_iwd()
        if self.backend == BackendType.NMCLI:
            return self._scan_nmcli()
        return []

    def _scan_iwd(self) -> list[Network]:
        dev = self._device
        if not dev:
            return []
        _run(["iwctl", "station", dev, "scan"])
        ok, output, _ = _run(["iwctl", "station", dev, "get-networks"])
        if not ok:
            return []

        connected_ssid = self._get_connected_ssid_iwd()
        networks = []
        for line in output.splitlines()[1:]:
            match = re.match(r"\s+(\S+)\s+(\S+)\s+(\*+)", line)
            if match:
                ssid = match.group(1)
                sec = match.group(2)
                bars = match.group(3)
                networks.append(
                    Network(
                        ssid=ssid,
                        signal=_parse_signal_iwd(bars),
                        security=_parse_security_iwd(sec),
                        connected=connected_ssid == ssid,
                    )
                )
        return networks

    def _scan_nmcli(self) -> list[Network]:
        _run(["nmcli", "device", "wifi", "rescan"])
        ok, output, _ = _run([
            "nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY",
            "device", "wifi", "list",
        ])
        if not ok:
            return []

        connected_ssid = self._get_connected_ssid_nmcli()
        networks = []
        seen = set()
        for line in output.splitlines():
            parts = line.split(":")
            if len(parts) >= 3:
                ssid = parts[0]
                if not ssid or ssid in seen:
                    continue
                seen.add(ssid)
                try:
                    signal = int(parts[1])
                except ValueError:
                    signal = 0
                sec = parts[2] if len(parts) > 2 else ""
                networks.append(
                    Network(
                        ssid=ssid,
                        signal=signal,
                        security=_parse_security_nmcli(sec),
                        connected=connected_ssid == ssid,
                    )
                )
        return networks

    def connect(self, ssid: str, password: str | None = None) -> bool:
        if self.backend == BackendType.IWD:
            return self._connect_iwd(ssid, password)
        if self.backend == BackendType.NMCLI:
            return self._connect_nmcli(ssid, password)
        return False

    def _connect_iwd(self, ssid: str, password: str | None) -> bool:
        dev = self._device
        if not dev:
            return False
        if password:
            ok, _, _ = _run([
                "iwctl", "--passphrase", password,
                "station", dev, "connect", ssid,
            ])
        else:
            ok, _, _ = _run(["iwctl", "station", dev, "connect", ssid])
        return ok

    def _connect_nmcli(self, ssid: str, password: str | None) -> bool:
        cmd = ["nmcli", "device", "wifi", "connect", ssid]
        if password:
            cmd.extend(["password", password])
        ok, _, _ = _run(cmd)
        return ok

    def disconnect(self) -> bool:
        if self.backend == BackendType.IWD:
            dev = self._device
            if not dev:
                return False
            ok, _, _ = _run(["iwctl", "station", dev, "disconnect"])
            return ok
        if self.backend == BackendType.NMCLI:
            dev = self._get_nmcli_interface()
            if not dev:
                return False
            ok, _, _ = _run(["nmcli", "device", "disconnect", dev])
            return ok
        return False

    def status(self) -> ConnectionStatus:
        if self.backend == BackendType.IWD:
            return self._status_iwd()
        if self.backend == BackendType.NMCLI:
            return self._status_nmcli()
        return ConnectionStatus(connected=False, ssid=None, ip=None, interface=None)

    def _get_connected_ssid_iwd(self) -> str | None:
        dev = self._device
        if not dev:
            return None
        ok, output, _ = _run(["iwctl", "station", dev, "show"])
        if not ok:
            return None
        for line in output.splitlines():
            if "SSID" in line:
                parts = line.split(":", 1)
                if len(parts) == 2 and parts[1].strip():
                    return parts[1].strip()
        return None

    def _get_connected_ssid_nmcli(self) -> str | None:
        ok, output, _ = _run(["nmcli", "-t", "-f", "STATE,CONNECTION", "device", "status"])
        if not ok:
            return None
        for line in output.splitlines():
            parts = line.split(":")
            if len(parts) == 2 and parts[0] == "connected":
                return parts[1]
        return None

    def _status_iwd(self) -> ConnectionStatus:
        dev = self._device
        if not dev:
            return ConnectionStatus(False, None, None, None)
        ok, output, _ = _run(["iwctl", "station", dev, "show"])
        if not ok:
            return ConnectionStatus(False, None, None, dev)

        connected = False
        ssid = None
        for line in output.splitlines():
            if "Connected" in line and "yes" in line.lower():
                connected = True
            if "SSID" in line:
                parts = line.split(":", 1)
                if len(parts) == 2 and parts[1].strip():
                    ssid = parts[1].strip()

        ip = None
        if connected:
            ok_ip, ip_out, _ = _run(["ip", "-4", "addr", "show", dev])
            if ok_ip:
                match = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", ip_out)
                if match:
                    ip = match.group(1)

        return ConnectionStatus(connected, ssid, ip, dev)

    def _status_nmcli(self) -> ConnectionStatus:
        dev = self._get_nmcli_interface()
        if not dev:
            return ConnectionStatus(False, None, None, None)
        ok, output, _ = _run(["nmcli", "-t", "-f", "STATE,CONNECTION", "device", "status"])
        if not ok:
            return ConnectionStatus(False, None, None, dev)

        connected = False
        ssid = None
        for line in output.splitlines():
            parts = line.split(":")
            if len(parts) == 2 and parts[0] == "connected":
                connected = True
                ssid = parts[1]
                break

        ip = None
        if connected and ssid:
            ok_ip, ip_out, _ = _run(["nmcli", "-t", "-f", "IP4.ADDRESS", "connection", "show", ssid])
            if ok_ip and ip_out:
                match = re.search(r"(\d+\.\d+\.\d+\.\d+/\d+)", ip_out)
                if match:
                    ip = match.group(1).split("/")[0]

        return ConnectionStatus(connected, ssid, ip, dev)

    def forget_network(self, ssid: str) -> bool:
        if self.backend == BackendType.IWD:
            ok, _, _ = _run(["iwctl", "known-networks", ssid, "forget"])
            return ok
        if self.backend == BackendType.NMCLI:
            ok, _, _ = _run(["nmcli", "connection", "delete", ssid])
            return ok
        return False
