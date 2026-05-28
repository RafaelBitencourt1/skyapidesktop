# Skymail API Studio

Interface gráfica desktop para automação dos endpoints da **API Skymail**.  
Execute chamadas individuais e em lote (via CSV) para todos os recursos da plataforma: caixas postais, domínios, grupos, clientes, hospedagem, DNS, SMTP e backup.

---

## Passo a Passo — Usar com Python (código-fonte)

### Pré-requisito

- **Python 3.9 ou superior** — [python.org/downloads](https://www.python.org/downloads/)
  > Marque a opção **"Add Python to PATH"** durante a instalação no Windows

---

### Passo 1 — Clonar o repositório

```bash
git clone https://github.com/SEU_USUARIO/skymail-api-studio.git
cd skymail-api-studio
```

Ou baixe o ZIP pelo GitHub e extraia em uma pasta.

---

### Passo 2 — Instalar dependências

**Opção A — Automática (recomendada no Windows):**

Dê duplo clique em `run_skymail_gui.bat`.  
Ele verifica o Python, instala as dependências automaticamente e já abre a interface.

**Opção B — Manual via terminal:**

```bash
pip install -r requirements.txt
```

Ou com ambiente virtual isolado:

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # PowerShell
pip install -r requirements.txt
```

---

### Passo 3 — Executar o app

```bash
python skymail_gui.py
```

Ou dê duplo clique em `run_skymail_gui.bat`.

---

### Passo 4 — Autenticação

Ao abrir, a tela de login aparece obrigatoriamente:

| Aba | O que fazer |
|---|---|
| **Criar Token** | Informe usuário, senha e Secret Key para gerar um novo JWT |
| **Token Existente** | Cole um JWT gerado anteriormente |

> O acesso à interface só é liberado com um token JWT estruturalmente válido.  
> Fechar a janela de login sem autenticar encerra o aplicativo.

O token é salvo localmente no arquivo `.token` para não precisar informar novamente.

---

### Passo 5 — Usar a interface

Após autenticar, a interface principal abre com duas abas:

**Endpoint Individual**
1. Selecione a **categoria** (ex: Caixa Postal, Domínio, DNS...)
2. Selecione o **endpoint** desejado no menu
3. Preencha os **campos obrigatórios**
4. Clique em **Executar**
5. A resposta JSON aparece no painel da direita

**Execução em Lote (CSV)**
1. Selecione o **endpoint** de lote
2. Clique em **Importar CSV** e escolha o arquivo
3. Confira o **preview** dos dados na tabela
4. Clique em **Executar Lote**
5. Acompanhe o progresso na barra e no console
6. Logs de alterações (`POST`, `PUT`, `DELETE`) são salvos automaticamente em `logs/`

---

## Passo a Passo — Usar o Executável (.exe)

Se não quiser instalar Python, use o executável compilado.

### Passo 1 — Obter o executável

Compile localmente (veja seção abaixo) ou receba a pasta `SkymailAPIStudio/` já pronta.

### Passo 2 — Executar

Abra a pasta `SkymailAPIStudio/` e dê duplo clique em **`SkymailAPIStudio.exe`**.

> A pasta `_internal/` deve ficar **junto** com o `.exe` — não mova o exe sozinho.

### Passo 3 — Autenticar e usar

Siga os **Passos 4 e 5** da seção acima. O funcionamento é idêntico.

---

## Gerar o Executável (.exe)

Para compilar do zero na sua máquina:

```bash
# Windows — execute o script incluído:
build_exe.bat
```

Ou manualmente:

```bash
pip install pyinstaller
pyinstaller --onedir --windowed --name "SkymailAPIStudio" --collect-data ttkbootstrap skymail_gui.py
```

O resultado fica em `dist\SkymailAPIStudio\`. Funciona em qualquer Windows sem precisar do Python instalado.

---

## Estrutura do Projeto

```
skymail-api-studio/
├── skymail_gui.py          # Entry point — inicia o app
├── run_skymail_gui.bat     # Lançador Windows (instala deps automaticamente)
├── build_exe.bat           # Script de build PyInstaller
├── requirements.txt        # Dependências Python
└── skymail/                # Pacote principal
    ├── constants.py        # BASE_URL, caminhos, lock de log
    ├── endpoints.py        # Dicionários de endpoints (140 + 8 DNS)
    ├── field_config.py     # Labels e valores de exemplo dos campos
    ├── api_client.py       # Cliente HTTP, funções de log JSON
    ├── request_builder.py  # Construtores de requisição por endpoint
    ├── login_dialog.py     # Janela de autenticação JWT
    └── app.py              # Janela principal (toda a interface)
```

---

## Dependências

| Pacote | Uso |
|---|---|
| `requests` | Chamadas HTTP à API Skymail |
| `ttkbootstrap` | Tema e widgets visuais (`darkly`) |

`tkinter` já vem incluído na instalação padrão do Python no Windows.

---

## Segurança

- O arquivo `.token` é salvo **localmente** e está no `.gitignore` — nunca suba seu token para o repositório
- Os logs em `logs/` também estão no `.gitignore`

---

## Licença

Uso interno — Skymail / Sky Networks.
