import sys
import threading
from pathlib import Path

BASE_URL = "https://api.skymail.net.br/v1"

# Quando empacotado pelo PyInstaller (--onefile ou --onedir),
# sys.frozen é True e APP_DIR deve apontar para a pasta do .exe.
if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
else:
    APP_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = APP_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
CHANGE_LOG_FILE = LOG_DIR / "alteracoes.json"
DNS_LOG_FILE = LOG_DIR / "dns_consultas.json"
TOKEN_FILE = APP_DIR / ".token"
THEME_FILE = APP_DIR / ".theme"
_log_lock = threading.Lock()
