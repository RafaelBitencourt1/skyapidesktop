# Skymail API Studio

Interface gráfica desktop para automação dos endpoints da **API Skymail**.  
Permite executar chamadas individuais e em lote (via CSV) para todos os recursos da plataforma: caixas postais, domínios, grupos, clientes, hospedagem, DNS, SMTP, backup e muito mais.

---

## Funcionalidades

- **140+ endpoints** organizados por categoria em abas
- **Execução individual** com formulário de campos dinâmico
- **Execução em lote via CSV** com preview de dados e progresso
- **Autenticação JWT** — geração automática de token ou uso de token existente
- **Logs automáticos** de alterações (`POST`, `PUT`, `DELETE`) em JSON
- **Tema claro/escuro** com ttkbootstrap (`darkly`)

---

## Instalação

### Opção 1 — Um clique (recomendada para Windows)

> Não é necessário ter Python instalado previamente.

1. Baixe ou clone o repositório:
   ```
   git clone https://github.com/SEU_USUARIO/skymail-api-studio.git
   cd skymail-api-studio
   ```

2. Dê duplo clique em **`instalar.bat`**

O script faz automaticamente:
- Detecta se o Python já está instalado (3.9+)
- Se não encontrar, **baixa e instala o Python 3.12 silenciosamente**
- Cria um ambiente virtual isolado (`.venv`)
- Instala `requests` e `ttkbootstrap`
- Abre o Skymail API Studio

> Nas próximas vezes, basta clicar em `instalar.bat` novamente — ele detecta que tudo já está instalado e abre direto o app.

---

### Opção 2 — Manual (venv isolado)

```bash
# 1. Clone o repositório
git clone https://github.com/SEU_USUARIO/skymail-api-studio.git
cd skymail-api-studio

# 2. Crie e ative um ambiente virtual
python -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# Windows (CMD)
.venv\Scripts\activate.bat

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Execute o app
python skymail_gui.py
```

---

### Opção 3 — Sem ambiente virtual (instalação global)

```bash
pip install requests ttkbootstrap
python skymail_gui.py
```

---

## Uso

> **Importante:** A tela com as chamadas de API **só é exibida após autenticação com um token JWT válido**. Sem um token válido, o acesso à interface principal é bloqueado.

1. Ao abrir, a tela de **autenticação** aparece obrigatoriamente:
   - **Criar Token** — informe usuário, senha e Secret Key para gerar e salvar um novo JWT
   - **Token Existente** — cole um JWT já gerado previamente

   Somente após inserir ou criar um token válido a interface principal será carregada.

2. Após autenticar, a interface principal abre com as abas:
   - **Endpoint Individual** — selecione a categoria, o endpoint e preencha os campos
   - **Execução em Lote** — selecione um CSV e execute em massa

3. Logs de alterações são salvos automaticamente em `logs/alteracoes.json`

---

## Estrutura do Projeto

```
skymail-api-studio/
├── skymail_gui.py          # Entry point — inicia o app
├── instalar.bat            # Instalador com um clique (baixa Python se necessário)
├── run_skymail_gui.bat     # Lançador rápido (requer ambiente já configurado)
├── requirements.txt        # Dependências Python
├── .gitignore
├── README.md
└── skymail/                # Pacote principal
    ├── __init__.py
    ├── constants.py        # BASE_URL, caminhos, lock de log
    ├── endpoints.py        # Dicionários de endpoints (140 + 8 DNS)
    ├── field_config.py     # Labels e valores de exemplo dos campos
    ├── api_client.py       # Cliente HTTP, funções de log JSON
    ├── request_builder.py  # Construtores de requisição por endpoint
    ├── login_dialog.py     # Janela de autenticação JWT
    └── app.py              # Janela principal (toda a interface)
```

---

## Gerar executável Windows (.exe)

Para distribuir sem precisar do Python instalado, use o PyInstaller:

```bash
# Execute o script de build incluído:
build_exe.bat
```

Ou manualmente:
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "SkymailAPIStudio" --collect-data ttkbootstrap skymail_gui.py
```

O arquivo `dist\SkymailAPIStudio.exe` gerado é **autossuficiente** — pode ser copiado para qualquer máquina Windows e executado com duplo clique, sem instalar Python.

> **Nota:** O primeiro build leva 1-3 minutos. O `.exe` terá ~60-90 MB (inclui Python + todas as dependências).

---

## Dependências

| Pacote | Versão mínima | Uso |
|---|---|---|
| `requests` | 2.28.0 | Chamadas HTTP à API Skymail |
| `ttkbootstrap` | 1.10.0 | Tema e widgets visuais (`darkly`) |

`tkinter` já está incluído na instalação padrão do Python no Windows.

---

## Observações de segurança

- O arquivo `.token` é salvo **localmente** e está no `.gitignore` — nunca suba seu token para o repositório
- Os logs em `logs/` também estão no `.gitignore`

---

## Licença

Uso interno — Skymail / Sky Networks.
