# wifiPy

Gestor de redes WiFi con interfaz TUI para Linux.

## Caracteristicas

- Escaneo de redes WiFi en tiempo real
- Soporte dual: **iwctl** (iwd) y **nmcli** (NetworkManager)
- Contraseñas cifradas con Fernet + Argon2id
- Interfaz modal tipo panel rapido
- Auto-refresh cada 10 segundos
- Almacenamiento seguro en SQLite

## Instalacion

### Requisitos

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) como package manager
- **iwctl** (iwd) o **nmcli** (NetworkManager)

### Instalar

```bash
git clone https://github.com/<user>/wifiPy.git
cd wifiPy
uv sync
uv tool install .
```

### Ejecutar

```bash
wifipy
```

O en modo desarrollo:

```bash
uv run main.py
```

## Uso

| Tecla | Accion |
|-------|--------|
| `Enter` | Conectar a la red seleccionada |
| `r` | Refrescar lista de redes |
| `Delete` | Olvidar red guardada |
| `q` / `Escape` | Cerrar |

## Estructura

```
wifiPy/
├── core/
│   ├── backend.py    — abstraccion iwctl/nmcli
│   ├── crypto.py     — cifrado Fernet + Argon2id
│   └── db.py         — SQLite encrypted
├── ui/
│   ├── app.py        — app Textual principal
│   ├── screens.py    — modales
│   └── styles.css    — estilos
├── desing/
│   ├── colors.py     — paleta de colores
│   └── layouts.py    — dimensiones
└── main.py           — entry point
```

## Seguridad

- Contraseñas cifradas con AES-128-CBC (Fernet)
- Key derivation con Argon2id (memory-hard)
- SQLite con `PRAGMA secure_delete = ON`
- Permisos de archivo restrictivos

## Licencia

MIT
