# wifiPy

Gestor de redes WiFi con interfaz TUI para Linux, inspirado en vim.

<img src="https://img.shields.io/badge/python-3.14-blue" alt="Python 3.14">
<img src="https://img.shields.io/badge/build-hatchling-green" alt="hatchling">
<img src="https://img.shields.io/badge/license-MIT-yellow" alt="MIT">

## Caracteristicas

- Escaneo de redes WiFi en tiempo real con **LoadingIndicator**
- Soporte dual: **iwctl** (iwd) y **nmcli** (NetworkManager) — auto-detecta
- Contraseñas cifradas con Fernet + Argon2id (key derivation memory-hard)
- Almacenamiento seguro en SQLite (WAL + secure_delete)
- Keybindings estilo **vim** para navegacion rapida
- Auto-refresh cada 10 segundos
- UI en espanol

## Instalacion

### Requisitos

- **Linux** (tested on KDE/Plasma)
- **Python 3.14+**
- [uv](https://docs.astral.sh/uv/) como package manager
- **iwctl** (iwd) o **nmcli** (NetworkManager) — auto-detecta cual esta disponible

### Instalar como herramienta CLI

```bash
git clone git@github.com:juan1417/WifiPy.git
cd WifiPy
uv sync
uv tool install .
```

Una vez instalado, ejecuta desde cualquier directorio:

```bash
wifipy
```

### Ejecutar en modo desarrollo

```bash
uv run main.py
```

### Desinstalar

```bash
uv tool uninstall wifipy
```

## Uso

### Keybindings (vim-style)

| Tecla | Accion |
|-------|--------|
| `j` | Mover cursor hacia abajo |
| `k` | Mover cursor hacia arriba |
| `g` | Ir a la primera red |
| `G` | Ir a la ultima red |
| `Enter` | Conectar a la red seleccionada |
| `d` | Olvidar red guardada |
| `r` | Refrescar lista de redes |
| `?` | Mostrar ayuda (keybinds) |
| `q` / `Escape` | Salir |

### Flujo

1. Al abrir, muestra un **spinner** mientras escanea redes en background
2. Usa `j`/`k` para navegar la lista
3. Presiona `Enter` para conectar — si es red abierta conecta directo, si tiene password pide la clave
4. Las contraseñas se guardan cifradas y se reusan automaticamente
5. `d` olvida una red guardada (pide confirmacion)
6. `r` refresca la lista manualmente

## Arquitectura

```
wifiPy/
├── core/
│   ├── backend.py    — deteccion automatica iwctl/nmcli, scan, connect, status
│   ├── crypto.py     — Fernet encryption + Argon2id KDF
│   └── db.py         — SQLite encrypted (WAL + secure_delete)
├── ui/
│   ├── app.py        — app Textual principal + keybindings vim
│   ├── screens.py    — modales de password y confirmacion
│   └── styles.css    — estilos (Tokyo Night theme)
├── desing/
│   ├── colors.py     — paleta de colores (frozen dataclass)
│   └── layouts.py    — dimensiones y intervalos (frozen dataclass)
├── main.py           — entry point: WifiApp().run()
└── pyproject.toml    — hatchling build, deps: textual, cryptography, platformdirs
```

### Optimizaciones de rendimiento

- **Async scan**: El escaneo de redes corre en un hilo background (`run_worker` + `call_from_thread`), la UI aparece en ~300ms
- **Lazy DB init**: La base de datos y el KDF Argon2id (3.6s) solo se inicializan cuando se necesitan (conectar/olvidar red)
- **ANSI stripping**: `iwctl` emite codigos de color ANSI — `_strip_ansi()` los limpia antes de parsear

## Seguridad

- Contraseñas cifradas con AES-128-CBC (Fernet)
- Key derivation con Argon2id (memory-hard, 2MB, 3 iteraciones, 4 lanes)
- SQLite con `PRAGMA secure_delete = ON` y `journal_mode = WAL`
- Master password hardcodeada para sesion local

## Licencia

MIT
