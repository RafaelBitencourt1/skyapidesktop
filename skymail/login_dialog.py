import base64
import hashlib
import hmac
import json
import threading
import tkinter as tk
import requests
import ttkbootstrap as ttk

from .constants import BASE_URL

class LoginDialog(tk.Toplevel):
    """Janela de autenticacao: gera token JWT ou aceita um token existente."""

    AUTH_URL = f"{BASE_URL}/auth/login"

    def __init__(self, master):
        super().__init__(master)
        self.title("Skymail — Autenticacao")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.grab_set()
        self.focus_set()

        # ── Cabecalho ──────────────────────────────────────────
        header = ttk.Frame(self, padding=(24, 18, 24, 8))
        header.pack(fill="x")
        ttk.Label(header, text="Skymail API Studio",
                  font=("Segoe UI", 20, "bold"), bootstyle="light").pack(anchor="w")
        ttk.Label(header, text="Autentique-se para acessar os endpoints.",
                  font=("Segoe UI", 10), bootstyle="secondary").pack(anchor="w", pady=(4, 0))

        sep = ttk.Separator(self)
        sep.pack(fill="x", padx=20, pady=(0, 6))

        # ── Notebook ──────────────────────────────────────────
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=20, pady=(0, 4))

        tab_criar = ttk.Frame(nb, padding=(18, 14))
        nb.add(tab_criar, text="  Criar Token  ")
        self._build_criar_tab(tab_criar)

        tab_existente = ttk.Frame(nb, padding=(18, 14))
        nb.add(tab_existente, text="  Token Existente  ")
        self._build_existente_tab(tab_existente)

        # ── Barra de status ───────────────────────────────────
        self._status_var = tk.StringVar()
        self._status_lbl = ttk.Label(
            self, textvariable=self._status_var,
            font=("Segoe UI", 9), bootstyle="secondary",
            wraplength=400, justify="left",
        )
        self._status_lbl.pack(fill="x", padx=22, pady=(2, 14))

        self._center()

    # ── Aba: Criar Token ──────────────────────────────────────
    def _build_criar_tab(self, frame):
        form = ttk.Frame(frame)
        form.pack(fill="x")

        fields = [
            ("Usuario:", "_user_var", False),
            ("Senha:", "_pass_var", True),
            ("Secret Key:", "_secret_var", True),
        ]
        self._secret_entry = None
        for row, (label, attr, masked) in enumerate(fields):
            ttk.Label(form, text=label, font=("Segoe UI", 9, "bold")).grid(
                row=row, column=0, sticky="w", pady=(0, 10), padx=(0, 14)
            )
            var = tk.StringVar()
            setattr(self, attr, var)
            ent = ttk.Entry(form, textvariable=var, show="*" if masked else "", width=38)
            ent.grid(row=row, column=1, sticky="ew", pady=(0, 10), ipady=5)
            if attr == "_secret_var":
                self._secret_entry = ent
        form.grid_columnconfigure(1, weight=1)

        # Mostrar/ocultar secret key
        self._show_secret_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame, text="Mostrar Secret Key",
            variable=self._show_secret_var,
            command=self._toggle_secret,
            bootstyle="secondary",
        ).pack(anchor="w", pady=(0, 12))

        self._criar_btn = ttk.Button(
            frame, text="Gerar e Usar Token",
            command=self._generate_token,
            bootstyle="success", padding=(16, 8),
        )
        self._criar_btn.pack(fill="x")

        # ── Area de resultado (escondida ate gerar) ───────────
        self._result_frame = ttk.LabelFrame(frame, text="Token Gerado")
        # Nao empacota ainda — mostrado em _on_token_ready

        token_box_row = ttk.Frame(self._result_frame)
        token_box_row.pack(fill="x", padx=10, pady=(8, 4))
        self._token_result_var = tk.StringVar()
        self._token_result_entry = ttk.Entry(
            token_box_row, textvariable=self._token_result_var,
            state="readonly", font=("Consolas", 9),
        )
        self._token_result_entry.pack(side="left", fill="x", expand=True, ipady=4)
        ttk.Button(
            token_box_row, text="Copiar",
            command=self._copy_token,
            bootstyle="info-outline", padding=(10, 4),
        ).pack(side="left", padx=(6, 0))

        ttk.Button(
            self._result_frame, text="Continuar para o Studio",
            command=self.destroy,
            bootstyle="success", padding=(14, 7),
        ).pack(fill="x", padx=10, pady=(4, 10))

    # ── Aba: Token Existente ──────────────────────────────────
    def _build_existente_tab(self, frame):
        ttk.Label(frame, text="Cole seu token JWT abaixo:",
                  font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 6))
        self._existing_var = tk.StringVar()
        ent = ttk.Entry(frame, textvariable=self._existing_var, width=52)
        ent.pack(fill="x", ipady=5, pady=(0, 12))
        ent.focus_set()
        self._existente_btn = ttk.Button(
            frame, text="Entrar com Token",
            command=self._use_existing,
            bootstyle="primary", padding=(16, 8),
        )
        self._existente_btn.pack(fill="x")

    # ── Logica de geracao de token ────────────────────────────
    def _toggle_secret(self):
        show = "" if self._show_secret_var.get() else "*"
        if self._secret_entry:
            self._secret_entry.configure(show=show)

    def _generate_token(self):
        user = self._user_var.get().strip()
        passwd = self._pass_var.get()
        secret = self._secret_var.get().strip()

        if not user or not passwd or not secret:
            self._set_status("Preencha usuario, senha e secret key.", "danger")
            return

        self._criar_btn.configure(state="disabled", text="Aguardando...")
        self._set_status("Autenticando na API...", "info")

        def _worker():
            try:
                resp = requests.post(
                    self.AUTH_URL,
                    data={"username": user, "password": passwd},
                    timeout=15,
                )
                if not resp.ok:
                    msg = f"Erro HTTP {resp.status_code}: {resp.text[:160]}"
                    self.after(0, lambda m=msg: self._set_status(m, "danger"))
                    return

                data = resp.json()
                jti = (data.get("data") or {}).get("jti") or data.get("jti")
                if not jti:
                    msg = f"JTI nao encontrado na resposta: {resp.text[:200]}"
                    self.after(0, lambda m=msg: self._set_status(m, "danger"))
                    return

                jwt_token = self._build_jwt(jti, secret)
                self.after(0, lambda t=jwt_token: self._on_token_ready(t))

            except requests.exceptions.RequestException as exc:
                msg = f"Erro de conexao: {exc}"
                self.after(0, lambda m=msg: self._set_status(m, "danger"))
            finally:
                self.after(0, lambda: self._criar_btn.configure(
                    state="normal", text="Gerar e Usar Token"))

        threading.Thread(target=_worker, daemon=True).start()

    @staticmethod
    def _build_jwt(jti: str, secret_b64: str) -> str:
        """Replica a logica do PS1: header.payload assinado com HMAC-SHA256."""
        def b64url(data: bytes) -> str:
            return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

        header = b64url(b'{"alg":"HS256","typ":"JWT"}')
        payload = b64url(json.dumps({"jti": jti}, separators=(",", ":")).encode())
        signing_input = f"{header}.{payload}"

        # Decodifica a secret key (base64 padrao, igual ao PS1)
        try:
            # Adiciona padding se necessario
            missing = len(secret_b64) % 4
            if missing:
                secret_b64 += "=" * (4 - missing)
            key = base64.b64decode(secret_b64)
        except Exception:
            key = secret_b64.encode("utf-8")  # fallback: usa como texto

        sig = hmac.new(key, signing_input.encode("utf-8"), hashlib.sha256).digest()
        return f"{signing_input}.{b64url(sig)}"

    def _on_token_ready(self, token: str):
        self._set_status("Token gerado com sucesso!", "success")
        self.master.token_var.set(token)
        self.master._save_token(token)
        self.master.deiconify()
        # Mostra o token na area de resultado
        self._token_result_var.set(token)
        self._result_frame.pack(fill="x", pady=(12, 0))
        self._center()

    def _copy_token(self):
        token = self._token_result_var.get()
        if token:
            self.clipboard_clear()
            self.clipboard_append(token)
            self._set_status("Token copiado para a area de transferencia!", "success")

    def _use_existing(self):
        token = self._existing_var.get().strip()
        if not token:
            self._set_status("Cole um token JWT valido.", "danger")
            return

        # Validacao estrutural do JWT: 3 segmentos + header/payload decodificaveis
        parts = token.split(".")
        if len(parts) != 3:
            self._set_status("Formato invalido. Um JWT deve ter 3 segmentos separados por '.'.", "danger")
            return
        try:
            for part in parts[:2]:  # valida header e payload
                pad = (4 - len(part) % 4) % 4
                base64.urlsafe_b64decode(part + "=" * pad)
        except Exception:
            self._set_status("Token invalido: nao foi possivel decodificar os segmentos do JWT.", "danger")
            return

        # JWT estruturalmente valido — usa direto
        self._on_existing_valid(token)

    def _on_existing_valid(self, token: str):
        self.master.token_var.set(token)
        self.master._save_token(token)
        self.master.deiconify()
        self.destroy()

    def _set_status(self, msg: str, style: str = "secondary"):
        self._status_var.set(msg)
        self._status_lbl.configure(bootstyle=style)

    def _on_close(self):
        # Captura master antes de destruir o dialog
        master = self.master
        token = getattr(master, "token_var", None)
        has_token = bool(token and token.get().strip())
        self.destroy()
        if not has_token:
            master.after(0, master.destroy)

    def _center(self):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")


