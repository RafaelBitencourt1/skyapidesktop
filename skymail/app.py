import base64
import csv
import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from .constants import APP_DIR, LOG_DIR, TOKEN_FILE
from .endpoints import ENDPOINTS, DNS_ENDPOINTS, ENDPOINT_PAGES
from .field_config import FIELD_LABELS, SAMPLE_VALUES
from .api_client import ApiClient, write_change_log, write_dns_log, normalize_row, now_iso
from .request_builder import build_request, build_dns_request
from .login_dialog import LoginDialog

class App(ttk.Window):
    def __init__(self):
        super().__init__(themename="darkly")
        self.title("Skymail API Studio")
        self.geometry("1200x800")
        self.minsize(1050, 720)

        self.running_batch = False
        self._cancel_batch = False
        self._batch_success = 0
        self._batch_errors = 0
        self._current_theme = "darkly"
        self.preview_rows = []
        self.preview_columns = []
        self.endpoint_labels = {v["label"]: k for k, v in ENDPOINTS.items()}
        self.dns_endpoint_labels = {v["label"]: k for k, v in DNS_ENDPOINTS.items()}
        self.endpoint_labels.update(self.dns_endpoint_labels)  # DNS junto
        self.field_vars = {}        # referência dinâmica para aba ativa
        self._tab_state = {}       # estado por categoria
        self.dns_field_vars = {}
        self._dns_cancel_batch = False
        self._dns_batch_success = 0
        self._dns_batch_errors = 0
        self.dns_preview_rows = []
        self.dns_preview_columns = []
        self.single_response_var = tk.StringVar(value="")

        self.withdraw()  # oculta ate login
        self._build_ui()
        self._load_token()
        self.bind_all("<F5>", self._on_f5)
        self.bind_all("<Control-l>", lambda e: self.clear_batch_console())
        self.bind_all("<Control-L>", lambda e: self.clear_batch_console())
        saved_token = self.token_var.get()
        # Verificacao silenciosa: JWT valido tem exatamente 3 segmentos
        if saved_token and len(saved_token.split(".")) == 3:
            self.deiconify()  # token salvo com formato valido: mostra direto
        else:
            # Token ausente ou malformado: limpa e pede login
            self.token_var.set("")
            try:
                TOKEN_FILE.unlink(missing_ok=True)
            except Exception:
                pass
            self.after(100, lambda: LoginDialog(self))

    def _build_ui(self):
        header = ttk.Frame(self, padding=(16, 12, 16, 4))
        header.pack(fill="x")
        ttk.Label(header, text="Skymail API Studio",
                  font=("Segoe UI", 22, "bold"),
                  bootstyle="light").pack(anchor="w")
        ttk.Label(header,
                  text="Todas as funcoes e endpoints da API em execucao individual e lote por CSV.",
                  font=("Segoe UI", 10), bootstyle="secondary").pack(anchor="w", pady=(4, 0))

        token_frame = ttk.LabelFrame(self, text="Token JWT")
        token_frame.pack(fill="x", padx=16, pady=(8, 10))
        token_row = ttk.Frame(token_frame, padding=(10, 6, 10, 0))
        token_row.pack(fill="x")
        self.token_var = tk.StringVar()
        self.token_entry = ttk.Entry(token_row, textvariable=self.token_var, show="*")
        self.token_entry.pack(side="left", fill="x", expand=True, ipady=4)
        ttk.Button(token_row, text="Mostrar/Ocultar", command=self.toggle_token,
                   bootstyle="secondary-outline", padding=(10, 4)).pack(side="left", padx=(8, 0))
        ttk.Button(token_row, text="Login / Novo Token", command=self.open_login,
                   bootstyle="info-outline", padding=(10, 4)).pack(side="left", padx=(6, 0))

        badges = ttk.Frame(token_frame, padding=(10, 6, 10, 8))
        badges.pack(fill="x")
        total_eps = len(ENDPOINTS) + len(DNS_ENDPOINTS)
        ttk.Label(badges, text=f"  {total_eps} endpoints disponiveis  ",
                  bootstyle="info-inverse",
                  font=("Segoe UI", 9, "bold")).pack(side="left")
        ttk.Label(badges, text=f"  Logs: {LOG_DIR}  ",
                  bootstyle="success-inverse",
                  font=("Segoe UI", 9)).pack(side="left", padx=(6, 0))

        ttk.Button(badges, text="Tema Claro/Escuro", command=self.toggle_theme,
                   bootstyle="secondary-outline", padding=(8, 2)).pack(side="right")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=16, pady=(0, 10))

        self.single_tab = ttk.Frame(notebook, padding=6)
        self.batch_tab = ttk.Frame(notebook, padding=6)
        notebook.add(self.single_tab, text="  Endpoint Individual  ")
        notebook.add(self.batch_tab, text="  Execucao em Lote  ")

        self._build_single_tab()
        self._build_batch_tab()

    def _build_single_tab(self):
        self._tab_state = {}
        self._page_names = [k for k in ENDPOINT_PAGES if k != "Todas" and ENDPOINT_PAGES[k]]

        self.single_inner_notebook = ttk.Notebook(self.single_tab)
        self.single_inner_notebook.pack(fill="both", expand=True)

        for cat_name in self._page_names:
            cat_ids = ENDPOINT_PAGES[cat_name]
            tab_frame = ttk.Frame(self.single_inner_notebook, padding=4)
            self.single_inner_notebook.add(tab_frame, text=f" {cat_name} ")
            self._build_inner_category_tab(tab_frame, cat_name, cat_ids)

        self.single_inner_notebook.bind("<<NotebookTabChanged>>", self._on_single_inner_tab_change)
        # Ativa o primeiro tab
        self._activate_category_tab(self._page_names[0])

    def _build_inner_category_tab(self, frame, cat_name, cat_ids):
        cfg = ttk.LabelFrame(frame, text="Configuracao")
        cfg.pack(fill="x", pady=(0, 6))

        ttk.Label(cfg, text="Endpoint", font=("Segoe UI", 9, "bold")).grid(
            row=0, column=0, sticky="w", pady=(6, 2), padx=(10, 0)
        )
        labels = [
            (ENDPOINTS.get(k) or DNS_ENDPOINTS.get(k) or {}).get("label", k)
            for k in cat_ids if k in ENDPOINTS or k in DNS_ENDPOINTS
        ]
        endpoint_var = tk.StringVar(value=labels[0] if labels else "")
        combo_row = ttk.Frame(cfg)
        combo_row.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 6), padx=(10, 10))
        endpoint_combo = ttk.Combobox(
            combo_row, textvariable=endpoint_var, values=labels, state="readonly"
        )
        endpoint_combo.pack(side="left", fill="x", expand=True, ipady=2)
        run_btn = ttk.Button(
            combo_row, text="Executar Endpoint",
            command=self.run_single_endpoint,
            bootstyle="success", padding=(14, 6),
        )
        run_btn.pack(side="left", padx=(8, 0))
        cfg.grid_columnconfigure(0, weight=1)

        fields_card = ttk.LabelFrame(frame, text="Parametros")
        fields_card.pack(fill="x", pady=(0, 6))
        fields_frame = ttk.Frame(fields_card, padding=(10, 6))
        fields_frame.pack(fill="x")

        resp_card = ttk.LabelFrame(frame, text="Resposta")
        resp_card.pack(fill="both", expand=True)
        resp_toolbar = ttk.Frame(resp_card)
        resp_toolbar.pack(fill="x", padx=10, pady=(4, 2))
        ttk.Button(resp_toolbar, text="Salvar resposta (.json)", command=self.save_single_response,
                   bootstyle="info-outline", padding=(9, 3)).pack(side="right")
        response = tk.Text(
            resp_card, wrap="word",
            bg="#0d1117", fg="#c9d1d9",
            insertbackground="#c9d1d9",
            relief="flat", font=("Consolas", 10),
        )
        response.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        response.configure(state="disabled")

        field_vars = {}
        state = {
            "endpoint_var": endpoint_var,
            "endpoint_combo": endpoint_combo,
            "fields_frame": fields_frame,
            "field_vars": field_vars,
            "response": response,
            "run_btn": run_btn,
        }
        self._tab_state[cat_name] = state

        endpoint_combo.bind("<<ComboboxSelected>>",
                            lambda e, s=state: self._on_cat_endpoint_change(s))
        # Popula os campos iniciais
        self._populate_fields(state)

    def _activate_category_tab(self, cat_name):
        if cat_name not in self._tab_state:
            return
        state = self._tab_state[cat_name]
        self.single_endpoint_var = state["endpoint_var"]
        self.single_endpoint_combo = state["endpoint_combo"]
        self.fields_frame = state["fields_frame"]
        self.field_vars = state["field_vars"]
        self.single_response = state["response"]
        self.single_run_btn = state["run_btn"]

    def _on_single_inner_tab_change(self, _event=None):
        try:
            tab_id = self.single_inner_notebook.select()
            tab_text = self.single_inner_notebook.tab(tab_id, "text").strip()
            self._activate_category_tab(tab_text)
        except Exception:
            pass

    def _on_cat_endpoint_change(self, state):
        # Garante que self.* aponta para a aba correta antes de recarregar campos
        self.single_endpoint_var = state["endpoint_var"]
        self.single_endpoint_combo = state["endpoint_combo"]
        self.fields_frame = state["fields_frame"]
        self.field_vars = state["field_vars"]
        self.single_response = state["response"]
        self.single_run_btn = state["run_btn"]
        self._populate_fields(state)

    def _populate_fields(self, state):
        fields_frame = state["fields_frame"]
        field_vars = state["field_vars"]
        endpoint_var = state["endpoint_var"]

        for w in fields_frame.winfo_children():
            w.destroy()
        field_vars.clear()

        label = endpoint_var.get()
        if not label or label not in self.endpoint_labels:
            return
        endpoint_id = self.endpoint_labels[label]
        spec = ENDPOINTS.get(endpoint_id) or DNS_ENDPOINTS.get(endpoint_id)
        if not spec:
            return
        fields = spec["required"] + spec["optional"]
        if not fields:
            ttk.Label(fields_frame, text="Endpoint sem parametros.",
                      bootstyle="secondary").grid(row=0, column=0, sticky="w")
            return

        for idx, field in enumerate(fields):
            ttk.Label(fields_frame, text=FIELD_LABELS.get(field, field)).grid(
                row=idx, column=0, sticky="w", pady=(0, 6), padx=(0, 12)
            )
            if field == "data_kv":
                txt = tk.Text(fields_frame, width=58, height=4,
                              bg="#1e2936", fg="#c9d1d9",
                              insertbackground="#c9d1d9", relief="flat",
                              font=("Consolas", 10))
                txt.grid(row=idx, column=1, sticky="ew", pady=(0, 6))
                field_vars[field] = txt
            else:
                var = tk.StringVar(value=SAMPLE_VALUES.get(field, ""))
                ent = ttk.Entry(fields_frame, textvariable=var)
                ent.grid(row=idx, column=1, sticky="ew", pady=(0, 6), ipady=4)
                field_vars[field] = var
        fields_frame.grid_columnconfigure(1, weight=1)

    def _build_batch_tab(self):
        cfg = ttk.LabelFrame(self.batch_tab, text="Configuracao")
        cfg.pack(fill="x", pady=(0, 8))

        # ── Linha 0/1: Categoria ──────────────────────────────
        ttk.Label(cfg, text="Categoria", font=("Segoe UI", 9, "bold")).grid(
            row=0, column=0, sticky="w", pady=(8, 2), padx=(10, 0)
        )
        self.batch_page_var = tk.StringVar(value=self._page_names[0])
        self.batch_page_combo = ttk.Combobox(
            cfg,
            textvariable=self.batch_page_var,
            values=self._page_names,
            state="readonly",
            width=28,
        )
        self.batch_page_combo.grid(row=1, column=0, sticky="w", pady=(0, 6), ipady=2, padx=(10, 0))
        self.batch_page_combo.bind("<<ComboboxSelected>>", self.on_batch_category_change)

        # ── Linha 2/3: Endpoint ──────────────────────────────
        ttk.Label(cfg, text="Endpoint", font=("Segoe UI", 9, "bold")).grid(
            row=2, column=0, sticky="w", pady=(0, 2), padx=(10, 0)
        )
        self.batch_all_values = list(self.endpoint_labels.keys())
        self.batch_endpoint_var = tk.StringVar(value=self.batch_all_values[0])
        self.batch_endpoint_combo = ttk.Combobox(
            cfg,
            textvariable=self.batch_endpoint_var,
            values=self.batch_all_values,
            state="readonly",
        )
        self.batch_endpoint_combo.grid(row=3, column=0, sticky="ew", pady=(0, 8), ipady=2, padx=(10, 0))
        self.batch_endpoint_combo.bind("<<ComboboxSelected>>", self.on_batch_endpoint_change)

        ttk.Label(cfg, text="Arquivo CSV", font=("Segoe UI", 9, "bold")).grid(
            row=4, column=0, sticky="w", pady=(0, 4), padx=(10, 0)
        )
        self.csv_var = tk.StringVar()
        self.csv_entry = ttk.Entry(cfg, textvariable=self.csv_var)
        self.csv_entry.grid(row=5, column=0, sticky="ew", pady=(0, 8), ipady=4, padx=(10, 0))

        right = ttk.Frame(cfg)
        right.grid(row=1, column=1, rowspan=5, sticky="ns", padx=(12, 10), pady=(0, 8))
        ttk.Button(right, text="Selecionar CSV", command=self.select_csv,
                   bootstyle="info", padding=(10, 5)).pack(fill="x", pady=(0, 6))
        ttk.Button(right, text="Gerar modelo CSV", command=self.save_csv_template,
                   bootstyle="secondary", padding=(10, 5)).pack(fill="x", pady=(0, 6))
        self.run_batch_btn = ttk.Button(right, text="Executar lote", command=self.run_batch,
                                        bootstyle="success", padding=(10, 5))
        self.run_batch_btn.pack(fill="x", pady=(0, 6))
        self.cancel_batch_btn = ttk.Button(right, text="Cancelar", command=self.cancel_batch,
                                           bootstyle="danger-outline", padding=(10, 5))
        self.cancel_batch_btn.pack(fill="x")
        self.cancel_batch_btn.configure(state="disabled")

        ttk.Label(cfg, text="Delay (s)", font=("Segoe UI", 9, "bold")).grid(
            row=6, column=0, sticky="w", pady=(0, 4), padx=(10, 0)
        )
        self.delay_var = tk.StringVar(value="0.5")
        self.delay_entry = ttk.Entry(cfg, textvariable=self.delay_var, width=10)
        self.delay_entry.grid(row=7, column=0, sticky="w", pady=(0, 8), ipady=4, padx=(10, 0))

        self.required_cols_var = tk.StringVar(value="Campos obrigatorios: -")
        ttk.Label(cfg, textvariable=self.required_cols_var,
                  bootstyle="secondary").grid(row=8, column=0, sticky="w", pady=(0, 10), padx=(10, 0))
        cfg.grid_columnconfigure(0, weight=1)

        preview = ttk.LabelFrame(self.batch_tab, text="Previa CSV")
        preview.pack(fill="x", pady=(0, 8))
        tree_wrap = ttk.Frame(preview, padding=(10, 6))
        tree_wrap.pack(fill="x")
        self.preview_tree = ttk.Treeview(tree_wrap, show="headings", height=6, bootstyle="dark")
        self.preview_tree.pack(side="left", fill="x", expand=True)
        ysb = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.preview_tree.yview,
                             bootstyle="secondary-round")
        ysb.pack(side="right", fill="y")
        self.preview_tree.configure(yscrollcommand=ysb.set)

        result = ttk.LabelFrame(self.batch_tab, text="Execucao")
        result.pack(fill="both", expand=True)
        self.progress = ttk.Progressbar(result, mode="determinate", bootstyle="success-striped")
        self.progress.pack(fill="x", pady=(0, 4), padx=10)

        self.progress_var = tk.StringVar(value="0%")
        self.status_var = tk.StringVar(value="Pronto")
        self.batch_counter_var = tk.StringVar(value="")
        status_row = ttk.Frame(result)
        status_row.pack(fill="x", pady=(0, 6), padx=10)
        ttk.Label(status_row, textvariable=self.progress_var,
                  bootstyle="success", font=("Segoe UI", 9, "bold")).pack(side="left")
        ttk.Label(status_row, textvariable=self.status_var,
                  bootstyle="secondary").pack(side="left", padx=(8, 0))
        ttk.Label(status_row, textvariable=self.batch_counter_var,
                  font=("Segoe UI", 9, "bold")).pack(side="left", padx=(12, 0))
        ttk.Button(status_row, text="Abrir logs", command=self.open_logs_folder,
                   bootstyle="info-outline", padding=(9, 3)).pack(side="right")
        ttk.Button(status_row, text="Limpar console", command=self.clear_batch_console,
                   bootstyle="secondary-outline", padding=(9, 3)).pack(side="right", padx=(0, 6))

        self.batch_console = tk.Text(
            result, wrap="word",
            bg="#0d1117", fg="#c9d1d9",
            insertbackground="#c9d1d9",
            relief="flat", font=("Consolas", 10),
        )
        self.batch_console.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.batch_console.configure(state="disabled")

        # Filtra o combo de endpoint para a categoria inicial
        self.on_batch_category_change()

    def toggle_token(self):
        self.token_entry.configure(show="" if self.token_entry.cget("show") == "*" else "*")

    def open_login(self):
        LoginDialog(self)

    # ── Token persistente ──────────────────────────────────────
    def _load_token(self):
        try:
            if TOKEN_FILE.exists():
                self.token_var.set(TOKEN_FILE.read_text(encoding="utf-8").strip())
        except Exception:
            pass

    def _save_token(self, token):
        try:
            TOKEN_FILE.write_text(token, encoding="utf-8")
        except Exception:
            pass

    # ── Validacao JWT ──────────────────────────────────────────
    def _validate_token(self, token):
        parts = token.split(".")
        if len(parts) != 3:
            messagebox.showerror(
                "Token invalido",
                "O token informado nao e um JWT valido.\nFormato esperado: xxxxx.yyyyy.zzzzz"
            )
            return False
        try:
            padding = "=" * (-len(parts[1]) % 4)
            payload = json.loads(base64.urlsafe_b64decode(parts[1] + padding))
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp) < datetime.now():
                exp_str = datetime.fromtimestamp(exp).strftime("%d/%m/%Y %H:%M:%S")
                messagebox.showwarning(
                    "Token expirado",
                    f"O token JWT expirou em {exp_str}.\nAtualize o token antes de continuar.",
                )
                return False
        except Exception:
            messagebox.showerror(
                "Token invalido",
                "Nao foi possivel decodificar o token JWT.\nVerifique se o token esta correto."
            )
            return False
        return True

    # ── Tema ───────────────────────────────────────────────────
    def toggle_theme(self):
        self._current_theme = "cosmo" if self._current_theme == "darkly" else "darkly"
        self.style.theme_use(self._current_theme)

    # ── Salvar resposta ────────────────────────────────────────
    def save_single_response(self):
        content = self.single_response.get("1.0", "end").strip()
        if not content:
            messagebox.showinfo("Vazio", "Nenhuma resposta para salvar.")
            return
        path = filedialog.asksaveasfilename(
            title="Salvar resposta",
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("Texto", "*.txt"), ("Todos", "*.*")],
            initialdir=str(LOG_DIR),
            initialfile=f"resposta_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        messagebox.showinfo("Salvo", f"Resposta salva em:\n{path}")

    # ── Cancelar lote ──────────────────────────────────────────
    def cancel_batch(self):
        self._cancel_batch = True
        self.status_var.set("Cancelando...")
        self.cancel_batch_btn.configure(state="disabled")

    # ── Atalho F5 ──────────────────────────────────────────────
    def _on_f5(self, _event=None):
        self.run_single_endpoint()

    def log_batch(self, text):
        self.batch_console.configure(state="normal")
        self.batch_console.insert("end", text + "\n")
        self.batch_console.see("end")
        self.batch_console.configure(state="disabled")

    def clear_batch_console(self):
        self.batch_console.configure(state="normal")
        self.batch_console.delete("1.0", "end")
        self.batch_console.configure(state="disabled")

    def log_single_response(self, text):
        self.single_response.configure(state="normal")
        self.single_response.delete("1.0", "end")
        self.single_response.insert("end", text)
        self.single_response.configure(state="disabled")

    def open_logs_folder(self):
        os.startfile(str(LOG_DIR))

    def on_batch_category_change(self, _event=None):
        cat = self.batch_page_var.get()
        ids = ENDPOINT_PAGES.get(cat, [])
        labels = [
            (ENDPOINTS.get(k) or DNS_ENDPOINTS.get(k) or {}).get("label", k)
            for k in ids if k in ENDPOINTS or k in DNS_ENDPOINTS
        ]
        if not labels:
            labels = list(self.endpoint_labels.keys())
        self.batch_endpoint_combo.configure(values=labels)
        self.batch_endpoint_var.set(labels[0])
        self.on_batch_endpoint_change()

    def on_single_endpoint_change(self, _event=None):
        # Delega para _populate_fields com o estado da aba ativa
        for cat, state in self._tab_state.items():
            if state["endpoint_var"] is self.single_endpoint_var:
                self._populate_fields(state)
                self.field_vars = state["field_vars"]
                return
        # fallback: reconstrói usando os refs diretos
        for w in self.fields_frame.winfo_children():
            w.destroy()
        self.field_vars.clear()

        label = self.single_endpoint_var.get()
        if not label or label not in self.endpoint_labels:
            return
        endpoint_id = self.endpoint_labels[label]
        spec = ENDPOINTS[endpoint_id]
        fields = spec["required"] + spec["optional"]
        if not fields:
            ttk.Label(self.fields_frame, text="Endpoint sem parametros.",
                      bootstyle="secondary").grid(row=0, column=0, sticky="w")
            return
        for idx, field in enumerate(fields):
            ttk.Label(self.fields_frame, text=FIELD_LABELS.get(field, field)).grid(
                row=idx, column=0, sticky="w", pady=(0, 6), padx=(0, 12)
            )
            if field == "data_kv":
                txt = tk.Text(self.fields_frame, width=58, height=4,
                              bg="#1e2936", fg="#c9d1d9",
                              insertbackground="#c9d1d9", relief="flat",
                              font=("Consolas", 10))
                txt.grid(row=idx, column=1, sticky="ew", pady=(0, 6))
                self.field_vars[field] = txt
            else:
                var = tk.StringVar(value=SAMPLE_VALUES.get(field, ""))
                ent = ttk.Entry(self.fields_frame, textvariable=var)
                ent.grid(row=idx, column=1, sticky="ew", pady=(0, 6), ipady=4)
                self.field_vars[field] = var
        self.fields_frame.grid_columnconfigure(1, weight=1)

    def on_batch_endpoint_change(self, _event=None):
        endpoint_id = self.endpoint_labels[self.batch_endpoint_var.get()]
        spec = ENDPOINTS.get(endpoint_id) or DNS_ENDPOINTS.get(endpoint_id) or {}
        req = ", ".join(spec.get("required", [])) or "(nenhum)"
        opt = ", ".join(spec.get("optional", [])) or "(nenhum)"
        self.required_cols_var.set(f"Obrigatorios: {req} | Opcionais: {opt}")

    def _collect_single_values(self):
        values = {}
        for key, source in self.field_vars.items():
            if isinstance(source, tk.Text):
                values[key] = source.get("1.0", "end").strip()
            else:
                values[key] = source.get().strip()
        return values

    def run_single_endpoint(self):
        token = self.token_var.get().strip()
        if not token:
            messagebox.showwarning("Token", "Informe o token JWT.")
            return
        if not self._validate_token(token):
            return
        self._save_token(token)
        endpoint_id = self.endpoint_labels[self.single_endpoint_var.get()]
        spec = ENDPOINTS.get(endpoint_id) or DNS_ENDPOINTS.get(endpoint_id)
        values = self._collect_single_values()

        missing = [k for k in spec["required"] if not values.get(k)]
        if missing:
            messagebox.showwarning("Campos", f"Preencha: {', '.join(missing)}")
            return

        self.single_run_btn.configure(state="disabled", text="Executando...")
        self.log_single_response("Aguardando resposta da API...")

        def _worker():
            client = ApiClient(token)
            try:
                if endpoint_id in DNS_ENDPOINTS:
                    method, url, params, data = build_dns_request(endpoint_id, values)
                    _json_body = None
                else:
                    method, url, params, data = build_request(endpoint_id, values)
                    _json_body = data.pop("__json__", None) if isinstance(data, dict) else None
                resp = client.request(method, url, params=params, data=data if data else None, json=_json_body)
                write_change_log("single", method, url, data, resp)

                body_text = resp.text or ""
                try:
                    body_pretty = json.dumps(resp.json(), indent=2, ensure_ascii=False)
                except Exception:
                    body_pretty = body_text

                # Detectar falha no corpo mesmo com HTTP 2xx
                _body_ok = True
                _raw_s = body_text.strip()
                try:
                    _body_s = resp.json()
                    if _body_s is False or _body_s == 0:
                        _body_ok = False
                    elif isinstance(_body_s, dict):
                        for _ks in ("success", "ok", "result"):
                            if _body_s.get(_ks) is False:
                                _body_ok = False
                                break
                except Exception:
                    pass
                if _body_ok and _raw_s.lower() in ("false", "0"):
                    _body_ok = False

                if not resp.ok:
                    _status_label = f"✗ ERRO HTTP {resp.status_code}"
                elif not _body_ok:
                    _status_label = f"⚠ AVISO — HTTP {resp.status_code} mas resposta indica falha"
                else:
                    _status_label = f"✓ OK {resp.status_code}"

                output = (
                    f"{_status_label}\n"
                    f"Metodo: {method}\n"
                    f"URL: {url}\n"
                    f"Params: {params}\n"
                    f"Data: {data}\n"
                    f"\nResposta:\n{body_pretty}"
                )
                self.after(0, lambda: self.log_single_response(output))
            except Exception as exc:
                self.after(0, lambda: self.log_single_response(f"Falha ao executar endpoint:\n{exc}"))
            finally:
                self.after(0, lambda: self.single_run_btn.configure(state="normal", text="Executar Endpoint"))

        threading.Thread(target=_worker, daemon=True).start()

    def select_csv(self):
        path = filedialog.askopenfilename(
            title="Selecione CSV",
            filetypes=[("CSV", "*.csv"), ("Todos", "*.*")],
            initialdir=str(APP_DIR),
        )
        if path:
            self.csv_var.set(path)
            self.load_csv_preview(path)

    def save_csv_template(self):
        endpoint_id = self.endpoint_labels[self.batch_endpoint_var.get()]
        spec = ENDPOINTS.get(endpoint_id) or DNS_ENDPOINTS.get(endpoint_id) or {}
        headers = spec.get("required", []) + spec.get("optional", [])
        if not headers:
            headers = ["dummy"]

        path = filedialog.asksaveasfilename(
            title="Salvar modelo CSV",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialdir=str(APP_DIR),
            initialfile=f"modelo_{endpoint_id}.csv",
        )
        if not path:
            return

        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerow({h: SAMPLE_VALUES.get(h, "") for h in headers})

        self.log_batch(f"Modelo CSV salvo: {path}")

    def load_csv_preview(self, csv_path):
        try:
            with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                self.preview_rows = [normalize_row(r) for r in reader]
                if self.preview_rows:
                    self.preview_columns = list(self.preview_rows[0].keys())
                else:
                    self.preview_columns = [c.lstrip("\ufeff").strip() for c in (reader.fieldnames or [])]

            self.refresh_preview_tree()
            self.log_batch(f"Preview carregada: {len(self.preview_rows)} linha(s).")
        except Exception as exc:
            self.preview_rows = []
            self.preview_columns = []
            self.refresh_preview_tree()
            self.log_batch(f"[ERRO] Falha no preview: {exc}")

    def refresh_preview_tree(self):
        for item in self.preview_tree.get_children():
            self.preview_tree.delete(item)

        if not self.preview_columns:
            self.preview_tree["columns"] = []
            return

        self.preview_tree["columns"] = self.preview_columns
        for col in self.preview_columns:
            self.preview_tree.heading(col, text=col)
            self.preview_tree.column(col, width=145, anchor="w")

        for row in self.preview_rows[:10]:
            self.preview_tree.insert("", "end", values=[row.get(c, "") for c in self.preview_columns])

    def set_batch_running(self, running):
        self.running_batch = running
        state = "disabled" if running else "readonly"
        self.batch_endpoint_combo.configure(state=state)
        self.run_batch_btn.configure(state="disabled" if running else "normal")
        self.cancel_batch_btn.configure(state="normal" if running else "disabled")
        if not running:
            self._cancel_batch = False

    def run_batch(self):
        if self.running_batch:
            return

        token = self.token_var.get().strip()
        csv_path = self.csv_var.get().strip()
        endpoint_id = self.endpoint_labels[self.batch_endpoint_var.get()]
        spec = ENDPOINTS.get(endpoint_id) or DNS_ENDPOINTS.get(endpoint_id) or {}

        if not token:
            messagebox.showwarning("Token", "Informe o token JWT.")
            return
        if not self._validate_token(token):
            return
        self._save_token(token)
        if not csv_path or not os.path.isfile(csv_path):
            messagebox.showwarning("CSV", "Selecione um arquivo CSV valido.")
            return

        try:
            delay = float((self.delay_var.get() or "0.5").replace(",", "."))
            if delay < 0.5:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Delay", "O delay minimo e 0.5 segundos.")
            return

        self._batch_success = 0
        self._batch_errors = 0
        self.batch_counter_var.set("")
        self.set_batch_running(True)
        self.status_var.set("Executando...")
        self.progress.configure(value=0)
        self.progress_var.set("0%")
        self.log_batch("=" * 76)
        self.log_batch(f"Inicio: {now_iso()} | Endpoint: {spec['label']}")
        self.log_batch(f"CSV: {csv_path}")

        if not self.preview_rows or self.csv_var.get().strip() != csv_path:
            self.load_csv_preview(csv_path)

        worker = threading.Thread(
            target=self._run_batch_worker,
            args=(token, endpoint_id, csv_path, delay),
            daemon=True,
        )
        worker.start()

    def _run_batch_worker(self, token, endpoint_id, csv_path, delay):
        spec = ENDPOINTS.get(endpoint_id) or DNS_ENDPOINTS.get(endpoint_id) or {}
        required = spec.get("required", [])
        rows = []
        errors = []
        success = 0

        try:
            with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
                rows = [normalize_row(r) for r in csv.DictReader(f)]
        except Exception as exc:
            self.after(0, lambda: self.log_batch(f"[ERRO] Falha ao ler CSV: {exc}"))
            self.after(0, lambda: self.status_var.set("Falha no CSV"))
            self.after(0, lambda: self.set_batch_running(False))
            return

        total = len(rows)
        if total == 0:
            self.after(0, lambda: self.log_batch("[ERRO] CSV sem linhas"))
            self.after(0, lambda: self.status_var.set("Sem dados"))
            self.after(0, lambda: self.set_batch_running(False))
            return

        self.after(0, lambda: self.progress.configure(maximum=total, value=0))
        client = ApiClient(token)

        for idx, row in enumerate(rows, start=1):
            if self._cancel_batch:
                self.after(0, lambda: self.log_batch("[!] Execucao cancelada pelo usuario."))
                break

            missing = [k for k in required if not row.get(k)]
            if missing:
                msg = f"Campos obrigatorios ausentes: {', '.join(missing)}"
                errors.append({"linha": idx, "dados": row, "erro": msg})
                self._batch_errors += 1
                self.after(0, lambda i=idx, t=total, m=msg: self.log_batch(f"[{i}/{t}] [ERRO] {m}"))
                self.after(0, lambda i=idx, t=total: self._update_batch_progress(i, t))
                continue

            try:
                if endpoint_id in DNS_ENDPOINTS:
                    method, url, params, data = build_dns_request(endpoint_id, row)
                    _json_body = None
                else:
                    method, url, params, data = build_request(endpoint_id, row)
                    _json_body = data.pop("__json__", None) if isinstance(data, dict) else None
                self.after(0, lambda i=idx, t=total, m=method, u=url: self.log_batch(f"[{i}/{t}] {m} {u}"))
                resp = client.request(method, url, params=params, data=data if data else None, json=_json_body)
                write_change_log("batch", method, url, data, resp)

                if resp.ok:
                    # Verifica se o corpo da resposta indica falha
                    _body_ok = True
                    _raw_text = (resp.text or "").strip()
                    try:
                        _body = resp.json()
                        if _body is False or _body == 0:
                            _body_ok = False
                        elif isinstance(_body, dict):
                            for _key in ("success", "ok", "result"):
                                if _body.get(_key) is False:
                                    _body_ok = False
                                    break
                    except Exception:
                        pass
                    # Captura respostas text/plain como "false"
                    if _body_ok and _raw_text.lower() in ("false", "0"):
                        _body_ok = False

                    if _body_ok:
                        success += 1
                        self._batch_success += 1
                        self.after(0, lambda c=resp.status_code: self.log_batch(f"  -> OK {c}"))
                    else:
                        self._batch_errors += 1
                        _preview = (resp.text or "")[:200]
                        errors.append({"linha": idx, "dados": row, "status": resp.status_code, "response": (resp.text or "")[:1500]})
                        self.after(0, lambda c=resp.status_code, r=_preview: self.log_batch(f"  -> AVISO: HTTP {c} mas resposta indica falha: {r}"))
                else:
                    self._batch_errors += 1
                    errors.append(
                        {
                            "linha": idx,
                            "dados": row,
                            "status": resp.status_code,
                            "response": (resp.text or "")[:1500],
                        }
                    )
                    self.after(0, lambda c=resp.status_code: self.log_batch(f"  -> ERRO HTTP {c}"))
            except Exception as exc:
                self._batch_errors += 1
                write_change_log("batch", ENDPOINTS[endpoint_id]["method"], "", {}, None, error=str(exc))
                errors.append({"linha": idx, "dados": row, "erro": str(exc)})
                self.after(0, lambda e=str(exc): self.log_batch(f"  -> EXCEPTION {e}"))

            self.after(0, lambda i=idx, t=total: self._update_batch_progress(i, t))
            if delay > 0 and idx < total:
                time.sleep(delay)

        if errors:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            err_file = LOG_DIR / f"erros_lote_{endpoint_id}_{stamp}.json"
            try:
                with open(err_file, "w", encoding="utf-8") as f:
                    json.dump(errors, f, indent=2, ensure_ascii=False)
                self.after(0, lambda p=str(err_file): self.log_batch(f"Log de erros: {p}"))
            except Exception as _ew:
                self.after(0, lambda e=str(_ew): self.log_batch(f"[ERRO] Falha ao salvar log de erros: {e}"))

        self.after(0, lambda: self.log_batch("-" * 76))
        self.after(0, lambda: self.log_batch(f"Concluido. Sucesso: {success} | Erros: {len(errors)}"))
        self.after(0, lambda: self.status_var.set("Concluido"))
        self.after(0, lambda: self.set_batch_running(False))

    def _update_batch_progress(self, current, total):
        self.progress.configure(value=current)
        percent = int((current / max(total, 1)) * 100)
        self.progress_var.set(f"{percent}%")
        self.batch_counter_var.set(f"  ✓ {self._batch_success}   ✗ {self._batch_errors}")


    # ═══════════════════════════════════════════════════════════
    # ─────────────────────  ABA DNS  ───────────────────────────
    # ═══════════════════════════════════════════════════════════

    def _build_dns_tab(self):
        dns_nb = ttk.Notebook(self.dns_tab)
        dns_nb.pack(fill="both", expand=True)

        self.dns_single_tab = ttk.Frame(dns_nb, padding=6)
        self.dns_batch_tab = ttk.Frame(dns_nb, padding=6)
        dns_nb.add(self.dns_single_tab, text="  Individual  ")
        dns_nb.add(self.dns_batch_tab, text="  Lote  ")

        self._build_dns_single_tab()
        self._build_dns_batch_tab()

    def _build_dns_single_tab(self):
        cfg = ttk.LabelFrame(self.dns_single_tab, text="Configuracao")
        cfg.pack(fill="x", pady=(0, 8))

        ttk.Label(cfg, text="Endpoint DNS", font=("Segoe UI", 9, "bold")).grid(
            row=0, column=0, sticky="w", pady=(8, 4), padx=(10, 0)
        )
        dns_labels = list(self.dns_endpoint_labels.keys())
        self.dns_endpoint_var = tk.StringVar(value=dns_labels[0])
        combo_row = ttk.Frame(cfg)
        combo_row.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 4), padx=(10, 10))
        self.dns_endpoint_combo = ttk.Combobox(
            combo_row,
            textvariable=self.dns_endpoint_var,
            values=dns_labels,
            state="readonly",
        )
        self.dns_endpoint_combo.pack(side="left", fill="x", expand=True, ipady=2)
        self.dns_endpoint_combo.bind("<<ComboboxSelected>>", self.on_dns_endpoint_change)
        self.dns_single_run_btn = ttk.Button(
            combo_row,
            text="Executar",
            command=self.run_dns_single,
            bootstyle="success",
            padding=(14, 6),
        )
        self.dns_single_run_btn.pack(side="left", padx=(8, 0))
        cfg.grid_columnconfigure(0, weight=1)

        fields_card = ttk.LabelFrame(self.dns_single_tab, text="Parametros")
        fields_card.pack(fill="x", pady=(0, 8))
        self.dns_fields_frame = ttk.Frame(fields_card, padding=(10, 6))
        self.dns_fields_frame.pack(fill="x")

        resp_card = ttk.LabelFrame(self.dns_single_tab, text="Resposta")
        resp_card.pack(fill="both", expand=True)
        resp_toolbar = ttk.Frame(resp_card)
        resp_toolbar.pack(fill="x", padx=10, pady=(6, 2))
        ttk.Button(resp_toolbar, text="Exportar (.json)", command=self.save_dns_response,
                   bootstyle="info-outline", padding=(9, 3)).pack(side="right")
        ttk.Button(resp_toolbar, text="Abrir pasta logs", command=self.open_dns_logs,
                   bootstyle="secondary-outline", padding=(9, 3)).pack(side="right", padx=(0, 6))
        self.dns_single_response = tk.Text(
            resp_card, wrap="word",
            bg="#0d1117", fg="#c9d1d9",
            insertbackground="#c9d1d9",
            relief="flat", font=("Consolas", 10),
        )
        self.dns_single_response.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.dns_single_response.configure(state="disabled")

        self.on_dns_endpoint_change()

    def _build_dns_batch_tab(self):
        cfg = ttk.LabelFrame(self.dns_batch_tab, text="Configuracao")
        cfg.pack(fill="x", pady=(0, 8))

        ttk.Label(cfg, text="Endpoint DNS", font=("Segoe UI", 9, "bold")).grid(
            row=0, column=0, sticky="w", pady=(8, 4), padx=(10, 0)
        )
        dns_labels = list(self.dns_endpoint_labels.keys())
        self.dns_batch_endpoint_var = tk.StringVar(value=dns_labels[0])
        self.dns_batch_endpoint_combo = ttk.Combobox(
            cfg,
            textvariable=self.dns_batch_endpoint_var,
            values=dns_labels,
            state="readonly",
        )
        self.dns_batch_endpoint_combo.grid(row=1, column=0, sticky="ew", pady=(0, 8), ipady=2, padx=(10, 0))
        self.dns_batch_endpoint_combo.bind("<<ComboboxSelected>>", self.on_dns_batch_endpoint_change)

        ttk.Label(cfg, text="Arquivo CSV", font=("Segoe UI", 9, "bold")).grid(
            row=2, column=0, sticky="w", pady=(0, 4), padx=(10, 0)
        )
        self.dns_csv_var = tk.StringVar()
        ttk.Entry(cfg, textvariable=self.dns_csv_var).grid(
            row=3, column=0, sticky="ew", pady=(0, 8), ipady=4, padx=(10, 0)
        )

        right = ttk.Frame(cfg)
        right.grid(row=1, column=1, rowspan=3, sticky="ns", padx=(12, 10), pady=(0, 8))
        ttk.Button(right, text="Selecionar CSV", command=self.select_dns_csv,
                   bootstyle="info", padding=(10, 5)).pack(fill="x", pady=(0, 6))
        ttk.Button(right, text="Gerar modelo CSV", command=self.save_dns_csv_template,
                   bootstyle="secondary", padding=(10, 5)).pack(fill="x", pady=(0, 6))
        self.dns_run_batch_btn = ttk.Button(right, text="Executar lote", command=self.run_dns_batch,
                                            bootstyle="success", padding=(10, 5))
        self.dns_run_batch_btn.pack(fill="x", pady=(0, 6))
        self.dns_cancel_batch_btn = ttk.Button(right, text="Cancelar", command=self.cancel_dns_batch,
                                               bootstyle="danger-outline", padding=(10, 5))
        self.dns_cancel_batch_btn.pack(fill="x")
        self.dns_cancel_batch_btn.configure(state="disabled")

        ttk.Label(cfg, text="Delay (s)", font=("Segoe UI", 9, "bold")).grid(
            row=4, column=0, sticky="w", pady=(0, 4), padx=(10, 0)
        )
        self.dns_delay_var = tk.StringVar(value="0.5")
        ttk.Entry(cfg, textvariable=self.dns_delay_var, width=10).grid(
            row=5, column=0, sticky="w", pady=(0, 8), ipady=4, padx=(10, 0)
        )
        self.dns_required_cols_var = tk.StringVar(value="Campos obrigatorios: -")
        ttk.Label(cfg, textvariable=self.dns_required_cols_var,
                  bootstyle="secondary").grid(row=6, column=0, sticky="w", pady=(0, 10), padx=(10, 0))
        cfg.grid_columnconfigure(0, weight=1)

        preview = ttk.LabelFrame(self.dns_batch_tab, text="Previa CSV")
        preview.pack(fill="x", pady=(0, 8))
        tree_wrap = ttk.Frame(preview, padding=(10, 6))
        tree_wrap.pack(fill="x")
        self.dns_preview_tree = ttk.Treeview(tree_wrap, show="headings", height=5, bootstyle="dark")
        self.dns_preview_tree.pack(side="left", fill="x", expand=True)
        ysb = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.dns_preview_tree.yview,
                             bootstyle="secondary-round")
        ysb.pack(side="right", fill="y")
        self.dns_preview_tree.configure(yscrollcommand=ysb.set)

        result = ttk.LabelFrame(self.dns_batch_tab, text="Execucao")
        result.pack(fill="both", expand=True)
        self.dns_progress = ttk.Progressbar(result, mode="determinate", bootstyle="info-striped")
        self.dns_progress.pack(fill="x", pady=(0, 4), padx=10)

        self.dns_progress_var = tk.StringVar(value="0%")
        self.dns_status_var = tk.StringVar(value="Pronto")
        self.dns_batch_counter_var = tk.StringVar(value="")
        status_row = ttk.Frame(result)
        status_row.pack(fill="x", pady=(0, 6), padx=10)
        ttk.Label(status_row, textvariable=self.dns_progress_var,
                  bootstyle="info", font=("Segoe UI", 9, "bold")).pack(side="left")
        ttk.Label(status_row, textvariable=self.dns_status_var,
                  bootstyle="secondary").pack(side="left", padx=(8, 0))
        ttk.Label(status_row, textvariable=self.dns_batch_counter_var,
                  font=("Segoe UI", 9, "bold")).pack(side="left", padx=(12, 0))
        ttk.Button(status_row, text="Abrir pasta logs", command=self.open_dns_logs,
                   bootstyle="info-outline", padding=(9, 3)).pack(side="right")
        ttk.Button(status_row, text="Limpar console", command=self.clear_dns_batch_console,
                   bootstyle="secondary-outline", padding=(9, 3)).pack(side="right", padx=(0, 6))

        self.dns_batch_console = tk.Text(
            result, wrap="word",
            bg="#0d1117", fg="#c9d1d9",
            insertbackground="#c9d1d9",
            relief="flat", font=("Consolas", 10),
        )
        self.dns_batch_console.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.dns_batch_console.configure(state="disabled")

        self.on_dns_batch_endpoint_change()

    def on_dns_endpoint_change(self, _event=None):
        for w in self.dns_fields_frame.winfo_children():
            w.destroy()
        self.dns_field_vars.clear()
        endpoint_id = self.dns_endpoint_labels[self.dns_endpoint_var.get()]
        spec = DNS_ENDPOINTS[endpoint_id]
        all_fields = spec["required"] + spec["optional"]
        for idx, field in enumerate(all_fields):
            label = FIELD_LABELS.get(field, field)
            req_mark = " *" if field in spec["required"] else ""
            ttk.Label(self.dns_fields_frame, text=f"{label}{req_mark}",
                      font=("Segoe UI", 9)).grid(row=idx, column=0, sticky="w", padx=(0, 12), pady=(0, 6))
            var = tk.StringVar(value=SAMPLE_VALUES.get(field, ""))
            ent = ttk.Entry(self.dns_fields_frame, textvariable=var)
            ent.grid(row=idx, column=1, sticky="ew", pady=(0, 6), ipady=4)
            self.dns_field_vars[field] = var
        self.dns_fields_frame.grid_columnconfigure(1, weight=1)

    def on_dns_batch_endpoint_change(self, _event=None):
        endpoint_id = self.dns_endpoint_labels[self.dns_batch_endpoint_var.get()]
        spec = DNS_ENDPOINTS[endpoint_id]
        req = ", ".join(spec["required"]) if spec["required"] else "(nenhum)"
        opt = ", ".join(spec["optional"]) if spec["optional"] else "(nenhum)"
        self.dns_required_cols_var.set(f"Obrigatorios: {req} | Opcionais: {opt}")

    def run_dns_single(self):
        token = self.token_var.get().strip()
        if not token:
            messagebox.showwarning("Token", "Informe o token JWT.")
            return
        if not self._validate_token(token):
            return
        self._save_token(token)
        endpoint_id = self.dns_endpoint_labels[self.dns_endpoint_var.get()]
        spec = DNS_ENDPOINTS[endpoint_id]
        values = {k: v.get().strip() for k, v in self.dns_field_vars.items()}
        missing = [k for k in spec["required"] if not values.get(k)]
        if missing:
            messagebox.showwarning("Campos", f"Preencha: {', '.join(missing)}")
            return

        self.dns_single_run_btn.configure(state="disabled", text="Executando...")
        self._log_dns_response("Aguardando resposta da API...")

        def _worker():
            client = ApiClient(token)
            try:
                method, url, params, data = build_dns_request(endpoint_id, values)
                resp = client.request(method, url, params=params, data=data if data else None)
                write_dns_log("single", url, params, resp)
                write_change_log("single", method, url, data, resp)
                body_text = resp.text or ""
                try:
                    body_pretty = json.dumps(resp.json(), indent=2, ensure_ascii=False)
                except Exception:
                    body_pretty = body_text
                _label = f"✓ OK {resp.status_code}" if resp.ok else f"✗ ERRO HTTP {resp.status_code}"
                output = (
                    f"{_label}\n"
                    f"URL: {url}\n"
                    f"Params: {params}\n"
                    f"\nResposta:\n{body_pretty}"
                )
                self.after(0, lambda: self._log_dns_response(output))
            except Exception as exc:
                self.after(0, lambda: self._log_dns_response(f"Falha ao executar:\n{exc}"))
            finally:
                self.after(0, lambda: self.dns_single_run_btn.configure(state="normal", text="Executar"))

        threading.Thread(target=_worker, daemon=True).start()

    def _log_dns_response(self, text):
        self.dns_single_response.configure(state="normal")
        self.dns_single_response.delete("1.0", "end")
        self.dns_single_response.insert("end", text)
        self.dns_single_response.configure(state="disabled")

    def save_dns_response(self):
        content = self.dns_single_response.get("1.0", "end").strip()
        if not content:
            messagebox.showinfo("Vazio", "Nenhuma resposta para exportar.")
            return
        path = filedialog.asksaveasfilename(
            title="Exportar resposta DNS",
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("Texto", "*.txt"), ("Todos", "*.*")],
            initialdir=str(LOG_DIR),
            initialfile=f"dns_resposta_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        messagebox.showinfo("Exportado", f"Resposta salva em:\n{path}")

    def open_dns_logs(self):
        os.startfile(str(LOG_DIR))

    def select_dns_csv(self):
        path = filedialog.askopenfilename(
            title="Selecione CSV",
            filetypes=[("CSV", "*.csv"), ("Todos", "*.*")],
            initialdir=str(APP_DIR),
        )
        if path:
            self.dns_csv_var.set(path)
            self._load_dns_csv_preview(path)

    def save_dns_csv_template(self):
        endpoint_id = self.dns_endpoint_labels[self.dns_batch_endpoint_var.get()]
        spec = DNS_ENDPOINTS[endpoint_id]
        headers = spec["required"] + spec["optional"]
        if not headers:
            headers = ["domain"]
        path = filedialog.asksaveasfilename(
            title="Salvar modelo CSV",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialdir=str(APP_DIR),
            initialfile=f"modelo_dns_{endpoint_id}.csv",
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerow({h: SAMPLE_VALUES.get(h, "") for h in headers})
        self.log_dns_batch(f"Modelo CSV salvo: {path}")

    def _load_dns_csv_preview(self, csv_path):
        try:
            with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                self.dns_preview_rows = [normalize_row(r) for r in reader]
                self.dns_preview_columns = list(self.dns_preview_rows[0].keys()) if self.dns_preview_rows else []
        except Exception:
            self.dns_preview_rows = []
            self.dns_preview_columns = []

        self.dns_preview_tree.configure(columns=self.dns_preview_columns)
        for col in self.dns_preview_columns:
            self.dns_preview_tree.heading(col, text=col)
            self.dns_preview_tree.column(col, width=130, minwidth=60)
        for row in self.dns_preview_tree.get_children():
            self.dns_preview_tree.delete(row)
        for row in self.dns_preview_rows[:20]:
            self.dns_preview_tree.insert("", "end", values=[row.get(c, "") for c in self.dns_preview_columns])

    def cancel_dns_batch(self):
        self._dns_cancel_batch = True
        self.dns_status_var.set("Cancelando...")
        self.dns_cancel_batch_btn.configure(state="disabled")

    def set_dns_batch_running(self, running):
        if running:
            self.dns_run_batch_btn.configure(state="disabled")
            self.dns_cancel_batch_btn.configure(state="normal")
            self._dns_cancel_batch = False
        else:
            self.dns_run_batch_btn.configure(state="normal")
            self.dns_cancel_batch_btn.configure(state="disabled")

    def log_dns_batch(self, text):
        self.dns_batch_console.configure(state="normal")
        self.dns_batch_console.insert("end", text + "\n")
        self.dns_batch_console.see("end")
        self.dns_batch_console.configure(state="disabled")

    def clear_dns_batch_console(self):
        self.dns_batch_console.configure(state="normal")
        self.dns_batch_console.delete("1.0", "end")
        self.dns_batch_console.configure(state="disabled")

    def _update_dns_batch_progress(self, current, total):
        self.dns_progress.configure(value=current)
        percent = int((current / max(total, 1)) * 100)
        self.dns_progress_var.set(f"{percent}%")
        self.dns_batch_counter_var.set(f"  ✓ {self._dns_batch_success}   ✗ {self._dns_batch_errors}")

    def run_dns_batch(self):
        token = self.token_var.get().strip()
        if not token:
            messagebox.showwarning("Token", "Informe o token JWT.")
            return
        if not self._validate_token(token):
            return
        self._save_token(token)
        endpoint_id = self.dns_endpoint_labels[self.dns_batch_endpoint_var.get()]
        spec = DNS_ENDPOINTS[endpoint_id]
        csv_path = self.dns_csv_var.get().strip()
        if not csv_path:
            messagebox.showwarning("CSV", "Selecione um arquivo CSV.")
            return
        try:
            delay = float(self.dns_delay_var.get().strip() or "0")
        except ValueError:
            messagebox.showwarning("Delay", "Delay deve ser um numero.")
            return
        if delay < 0.5:
            delay = 0.5
            self.dns_delay_var.set("0.5")

        self._dns_batch_success = 0
        self._dns_batch_errors = 0
        self.dns_batch_counter_var.set("")
        self.set_dns_batch_running(True)
        self.dns_status_var.set("Executando...")
        self.dns_progress.configure(value=0)
        self.dns_progress_var.set("0%")
        self.log_dns_batch("=" * 76)
        self.log_dns_batch(f"Inicio: {now_iso()} | Endpoint: {spec['label']}")
        self.log_dns_batch(f"CSV: {csv_path}")

        threading.Thread(
            target=self._run_dns_batch_worker,
            args=(token, endpoint_id, csv_path, delay),
            daemon=True,
        ).start()

    def _run_dns_batch_worker(self, token, endpoint_id, csv_path, delay):
        spec = DNS_ENDPOINTS[endpoint_id]
        required = spec["required"]
        rows = []
        errors = []
        success = 0

        try:
            with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
                rows = [normalize_row(r) for r in csv.DictReader(f)]
        except Exception as exc:
            self.after(0, lambda: self.log_dns_batch(f"[ERRO] Falha ao ler CSV: {exc}"))
            self.after(0, lambda: self.dns_status_var.set("Falha no CSV"))
            self.after(0, lambda: self.set_dns_batch_running(False))
            return

        total = len(rows)
        if total == 0:
            self.after(0, lambda: self.log_dns_batch("[ERRO] CSV sem linhas"))
            self.after(0, lambda: self.dns_status_var.set("Sem dados"))
            self.after(0, lambda: self.set_dns_batch_running(False))
            return

        self.after(0, lambda: self.dns_progress.configure(maximum=total, value=0))
        client = ApiClient(token)

        for idx, row in enumerate(rows, start=1):
            if self._dns_cancel_batch:
                self.after(0, lambda: self.log_dns_batch("[!] Execucao cancelada pelo usuario."))
                break

            missing = [k for k in required if not row.get(k)]
            if missing:
                msg = f"Campos obrigatorios ausentes: {', '.join(missing)}"
                errors.append({"linha": idx, "dados": row, "erro": msg})
                self._dns_batch_errors += 1
                self.after(0, lambda i=idx, t=total, m=msg: self.log_dns_batch(f"[{i}/{t}] [ERRO] {m}"))
                self.after(0, lambda i=idx, t=total: self._update_dns_batch_progress(i, t))
                continue

            try:
                method, url, params, data = build_dns_request(endpoint_id, row)
                self.after(0, lambda i=idx, t=total, m=method, u=url: self.log_dns_batch(f"[{i}/{t}] {m} {u}"))
                resp = client.request(method, url, params=params, data=data if data else None)
                write_dns_log("batch", url, params, resp)
                write_change_log("batch", method, url, data, resp)
                if resp.ok:
                    success += 1
                    self._dns_batch_success += 1
                    self.after(0, lambda c=resp.status_code: self.log_dns_batch(f"  -> OK {c}"))
                else:
                    self._dns_batch_errors += 1
                    errors.append({"linha": idx, "dados": row, "status": resp.status_code,
                                   "response": (resp.text or "")[:1500]})
                    self.after(0, lambda c=resp.status_code: self.log_dns_batch(f"  -> ERRO HTTP {c}"))
            except Exception as exc:
                self._dns_batch_errors += 1
                write_dns_log("batch", "", {}, None, error=str(exc))
                errors.append({"linha": idx, "dados": row, "erro": str(exc)})
                self.after(0, lambda e=str(exc): self.log_dns_batch(f"  -> EXCEPTION {e}"))

            self.after(0, lambda i=idx, t=total: self._update_dns_batch_progress(i, t))
            if delay > 0 and idx < total:
                time.sleep(delay)

        if errors:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            err_file = LOG_DIR / f"erros_dns_{endpoint_id}_{stamp}.json"
            try:
                with open(err_file, "w", encoding="utf-8") as f:
                    json.dump(errors, f, indent=2, ensure_ascii=False)
                self.after(0, lambda p=str(err_file): self.log_dns_batch(f"Log de erros: {p}"))
            except Exception as _ew:
                self.after(0, lambda e=str(_ew): self.log_dns_batch(f"[ERRO] Falha ao salvar log: {e}"))

        self.after(0, lambda: self.log_dns_batch("-" * 76))
        self.after(0, lambda: self.log_dns_batch(f"Concluido. Sucesso: {success} | Erros: {len(errors)}"))
        self.after(0, lambda: self.dns_status_var.set("Concluido"))
        self.after(0, lambda: self.set_dns_batch_running(False))


