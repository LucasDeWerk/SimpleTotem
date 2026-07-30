#!/usr/bin/env python3
"""SimpleTotem — Instalador com interface rich."""
import os
import sys
import shutil
import sqlite3
import stat
import threading
import queue
from pathlib import Path


def garantir_terminal():
    """Se não estiver num terminal, reabre o próprio executável dentro de um."""
    if sys.stdin.isatty():
        return
    exe = sys.argv[0]
    terminais = [
        ("gnome-terminal", ["gnome-terminal", "--wait", "--", exe, "--keep-open"]),
        ("xterm",          ["xterm", "-e", f"{exe} --keep-open"]),
        ("konsole",        ["konsole", "-e", exe, "--keep-open"]),
        ("xfce4-terminal", ["xfce4-terminal", "--command", f"{exe} --keep-open"]),
        ("lxterminal",     ["lxterminal", "-e", f"{exe} --keep-open"]),
    ]
    for nome, cmd in terminais:
        if shutil.which(nome):
            os.execvp(cmd[0], cmd)
    # Nenhum terminal encontrado — continua no modo sem terminal


garantir_terminal()

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import (
        Progress, SpinnerColumn, BarColumn,
        TextColumn, TaskProgressColumn, TimeElapsedColumn,
    )
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from rich.text import Text
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


# ── Localização dos arquivos empacotados ──────────────────────────────────────

def bundle_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)        # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent


# ── Schema SQLite ─────────────────────────────────────────────────────────────

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS vstb_empresa (
    id_saas INTEGER NOT NULL, id_empresa INTEGER NOT NULL,
    razao_social TEXT NOT NULL, nome_fantasia TEXT NOT NULL,
    cpf_cnpj TEXT, whatsapp TEXT, integrado_simplesfique TEXT NOT NULL,
    dhinc TEXT NOT NULL, insc_estadual TEXT, endereco TEXT, numero TEXT,
    cep TEXT, id_ibge TEXT, cidade TEXT, id_uf TEXT, id_bairro INTEGER,
    bairro TEXT, perfil TEXT, crt TEXT, ind_tp_ativ INTEGER, cnae TEXT,
    ret TEXT, token TEXT, email_simples TEXT, senha_simples TEXT,
    usuario_os TEXT, senha_os TEXT,
    PRIMARY KEY (id_saas, id_empresa)
);
CREATE TABLE IF NOT EXISTS test_grupo (
    id_grupo INTEGER PRIMARY KEY, descgrupo TEXT, foto BLOB
);
CREATE TABLE IF NOT EXISTS test_subgrupo (
    id_grupo INTEGER NOT NULL, id_subgrupo INTEGER NOT NULL,
    descsubgrupo TEXT, PRIMARY KEY (id_grupo, id_subgrupo)
);
CREATE TABLE IF NOT EXISTS test_marca (id_marca INTEGER PRIMARY KEY, descmarca TEXT);
CREATE TABLE IF NOT EXISTS test_medida (
    id_medida INTEGER PRIMARY KEY, descmedida TEXT, abreviatura TEXT
);
CREATE TABLE IF NOT EXISTS test_produto (
    id_produto INTEGER PRIMARY KEY, gtin TEXT, cod_referencia TEXT,
    cod_fabricacao TEXT, descproduto TEXT, id_grupo INTEGER,
    id_subgrupo INTEGER, id_marca INTEGER, id_medida INTEGER,
    preco_venda NUMERIC, custo_medio NUMERIC, custo_aquisicao NUMERIC,
    custo_compra NUMERIC, peso NUMERIC, id_ncm TEXT, cest TEXT,
    foto BLOB, estoque NUMERIC, dhinc TEXT, dhalt TEXT
);
CREATE TABLE IF NOT EXISTS tfin_tipopagrec (id TEXT PRIMARY KEY, desctipopagrec TEXT);
CREATE TABLE IF NOT EXISTS tven_saida (
    id INTEGER PRIMARY KEY, dtemissao TEXT, id_cfop TEXT,
    id_clifor INTEGER, id_vendedor INTEGER, situacao TEXT,
    vlr_venda NUMERIC, custo_total_venda NUMERIC, id_terminal INTEGER
);
CREATE TABLE IF NOT EXISTS tven_saidaitens (
    id INTEGER PRIMARY KEY, id_saida INTEGER, id_produto INTEGER,
    vlr_unitario_sugerido NUMERIC, vlr_unitario_praticado NUMERIC,
    desconto_unit_item NUMERIC, acrescimo_unit_item NUMERIC,
    quantidade NUMERIC, vlr_total_item NUMERIC
);
CREATE TABLE IF NOT EXISTS tven_saidapagamento (
    id INTEGER PRIMARY KEY AUTOINCREMENT, id_saida INTEGER NOT NULL,
    id_tipo_pagamento TEXT, vlr_pagamento NUMERIC NOT NULL,
    nsu_sitef TEXT, nsu_host TEXT, autorizacao TEXT, bandeira TEXT,
    modalidade TEXT, pix INTEGER NOT NULL DEFAULT 0,
    cupom_bruto TEXT, dh_pagamento TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tven_terminal (
    id INTEGER PRIMARY KEY, descterminal TEXT NOT NULL,
    nome_dispositivo TEXT, ip_dispositivo TEXT, imp_nfe_nfce TEXT,
    imp_ipc_nfe_nfce TEXT, totem_autoatendimento TEXT NOT NULL,
    imprime_pedido TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tconf_hardware (
    id INTEGER PRIMARY KEY AUTOINCREMENT, tipo_dispositivo TEXT,
    nome TEXT, vendor_id TEXT, product_id TEXT, descricao TEXT,
    driver_id TEXT, ativo INTEGER, dhinc TEXT, dhalt TEXT
);
CREATE TABLE IF NOT EXISTS tconf_api_sessao (
    chave TEXT PRIMARY KEY, token TEXT, id_saas INTEGER,
    id_empresa INTEGER, email TEXT, os_usuario TEXT,
    senha_simples_enc TEXT, senha_os_enc TEXT, expira_em INTEGER,
    dh_login TEXT, terminal_id INTEGER, terminal_token TEXT,
    senha_terminal_enc TEXT
);
CREATE TABLE IF NOT EXISTS tconf_sync_checkpoint (
    etapa TEXT PRIMARY KEY, dhsinc TEXT, ultimo_records INTEGER, dh_sync TEXT
);
"""


# ── Lógica de instalação ──────────────────────────────────────────────────────

def chmod_x(path: Path):
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


class Installer:
    def __init__(self, alvo: Path, bundle: Path, log_fn):
        self.alvo = alvo
        self.bundle = bundle
        self.log = log_fn

    def criar_diretorios(self):
        for d in ("dados", "script"):
            (self.alvo / d).mkdir(parents=True, exist_ok=True)
        self.log("Diretórios criados")

    def implantar_arquivos(self):
        b, a = self.bundle, self.alvo

        for nome in ("SimpleTotem", "SimpleTotem-backend"):
            src = b / nome
            if src.exists():
                dst = a / nome
                shutil.copy2(src, dst)
                chmod_x(dst)
                self.log(f"Copiado: {nome}")
            else:
                self.log(f"AVISO: {nome} não encontrado no pacote")

        ui_src = b / "SimpleTotem-ui"
        if ui_src.exists():
            self.log("Copiando SimpleTotem-ui/ (pode demorar)...")
            dst = a / "SimpleTotem-ui"
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(ui_src, dst)
            electron = dst / "simple-totem"
            if electron.exists():
                chmod_x(electron)
            self.log("Copiado: SimpleTotem-ui/")
        else:
            self.log("AVISO: SimpleTotem-ui não encontrado no pacote")

        script_src = b / "script"
        if script_src.exists():
            for f in script_src.iterdir():
                if f.name == "SCAFFOLD.md":
                    continue
                dst = a / "script" / f.name
                shutil.copy2(f, dst)
                if f.suffix in (".sh", ".so") or f.name == "hardware.py":
                    chmod_x(dst)
            self.log("Copiado: script/")

        env_dst = a / ".env"
        env_src = b / ".env.example"
        if not env_dst.exists() and env_src.exists():
            shutil.copy2(env_src, env_dst)
            self.log("Criado: .env")

    def criar_banco(self):
        db = self.alvo / "dados" / "simplebd"
        conn = sqlite3.connect(db)
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        conn.close()
        self.log("Banco criado: dados/simplebd")

    def criar_desktop(self):
        launcher = self.alvo / "SimpleTotem"
        icon = self.alvo / "SimpleTotem-ui" / "resources" / "app.asar.unpacked" / "icon.png"
        entry = (
            "[Desktop Entry]\n"
            "Name=SimpleTotem\n"
            "Comment=Totem de autoatendimento\n"
            f"Exec={launcher}\n"
            f"Icon={icon}\n"
            "Terminal=false\nType=Application\nCategories=Application;\n"
        )
        d = Path.home() / ".local" / "share" / "applications"
        d.mkdir(parents=True, exist_ok=True)
        f = d / "simpletotem.desktop"
        f.write_text(entry)
        f.chmod(0o644)
        self.log(f"Atalho criado: {f}")

    def configurar_sudoers(self):
        worker_sh = self.alvo / "script" / "run_sitef_worker.sh"
        usuario = os.environ.get("SUDO_USER") or os.environ.get("USER", "totem")
        regra = f"{usuario} ALL=(ALL) NOPASSWD: {worker_sh}\n"
        sudoers = Path("/etc/sudoers.d/simpletotem")
        if os.geteuid() != 0:
            self.log("AVISO: sudoers não configurado (execute com sudo)")
            return
        sudoers.write_text(regra)
        sudoers.chmod(0o440)
        self.log(f"Sudoers configurado para: {usuario}")


# ── Interface Rich ────────────────────────────────────────────────────────────

LARANJA = "#f57c00"
PASSOS = [
    "Criando diretórios",
    "Implantando arquivos",
    "Criando banco de dados",
    "Criando atalho .desktop",
    "Configurando sudoers",
]


def run_rich(alvo: Path, bundle: Path):
    console = Console()
    estados = ["wait"] * len(PASSOS)
    sucesso = False
    erro_msg = ""

    msg_q: "queue.Queue[tuple]" = queue.Queue()

    def log_fn(msg: str):
        msg_q.put(("log", msg))

    def step_fn(idx: int, estado: str):
        msg_q.put(("step", idx, estado))

    def worker():
        nonlocal sucesso, erro_msg
        try:
            inst = Installer(alvo, bundle, log_fn)
            fns = [
                inst.criar_diretorios,
                inst.implantar_arquivos,
                inst.criar_banco,
                inst.criar_desktop,
                inst.configurar_sudoers,
            ]
            for i, fn in enumerate(fns):
                step_fn(i, "run")
                fn()
                step_fn(i, "ok")
            sucesso = True
        except Exception as exc:
            import traceback
            erro_msg = str(exc)
            log_fn(traceback.format_exc())
            # marca o passo que falhou
            for i, e in enumerate(estados):
                if e == "run":
                    step_fn(i, "err")
        msg_q.put(("done",))

    def render_passos() -> Table:
        icons = {
            "wait": "[dim]  ·[/dim]",
            "run":  "[yellow]  ⏳[/yellow]",
            "ok":   "[green]  ✔[/green]",
            "err":  "[red]  ✘[/red]",
        }
        t = Table.grid(padding=(0, 2))
        t.add_column(width=5)
        t.add_column()
        for i, nome in enumerate(PASSOS):
            t.add_row(icons[estados[i]], nome)
        return t

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    with Progress(
        SpinnerColumn(spinner_name="dots", style=LARANJA),
        TextColumn("[bold]{task.description}"),
        BarColumn(bar_width=36, style=LARANJA, complete_style="green"),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
        refresh_per_second=10,
    ) as progress:
        task = progress.add_task("Instalando...", total=len(PASSOS))

        while True:
            try:
                item = msg_q.get(timeout=0.05)
            except queue.Empty:
                if not thread.is_alive():
                    break
                continue

            kind = item[0]
            if kind == "step":
                _, idx, estado = item
                estados[idx] = estado
                if estado == "ok":
                    progress.advance(task)
                    progress.update(task, description=PASSOS[idx])
            elif kind == "log":
                progress.console.print(f"   [dim]{item[1]}[/dim]")
            elif kind == "done":
                break

    console.print()
    console.print(render_passos())
    console.print()

    if sucesso:
        console.print(Panel(
            f"[bold green]  Instalação concluída com sucesso!\n\n"
            f"[/bold green]  Antes de iniciar, edite: [bold]{alvo}/.env[/bold]",
            border_style="green",
            padding=(1, 4),
        ))
    else:
        console.print(Panel(
            f"[bold red]  Falha na instalação![/bold red]\n\n  {erro_msg}",
            border_style="red",
            padding=(1, 2),
        ))

    return sucesso


# ── Main ──────────────────────────────────────────────────────────────────────

def aguardar_enter(console):
    console.print()
    console.print("  Pressione [bold]Enter[/bold] para fechar...", end="")
    input()


def main():
    keep_open = "--keep-open" in sys.argv
    bundle = bundle_dir()

    if not HAS_RICH:
        alvo = Path(input("Diretório de instalação [/opt/simpletotem]: ").strip() or "/opt/simpletotem")
        inst = Installer(alvo, bundle, lambda m: print(f"  {m}"))
        inst.criar_diretorios()
        inst.implantar_arquivos()
        inst.criar_banco()
        inst.criar_desktop()
        inst.configurar_sudoers()
        print("Instalado!")
        return

    console = Console()
    console.print()
    console.print(Panel(
        Text("SimpleTotem — Instalador", style=f"bold {LARANJA}", justify="center"),
        border_style=LARANJA,
        padding=(1, 4),
    ))
    console.print()

    # Avisa se não tem permissão de root para instalar em /opt
    if os.geteuid() != 0:
        console.print(
            "  [yellow]Atenção:[/yellow] não está rodando como root.\n"
            "  Para instalar em [bold]/opt[/bold] use: [bold]sudo ./SimpleTotem-Installer[/bold]\n"
            "  Ou escolha um diretório dentro do seu home, ex: [bold]/home/totem/simpletotem[/bold]\n"
        )

    padrao = "/opt/simpletotem" if os.geteuid() == 0 else str(Path.home() / "simpletotem")
    resposta = Prompt.ask("  [bold]Diretório de instalação[/bold]", default=padrao)
    alvo = Path(resposta)

    if alvo.exists() and any(alvo.iterdir()):
        console.print()
        if not Confirm.ask(f"  [yellow]'{alvo}' já existe. Sobrescrever?[/yellow]", default=False):
            console.print("  Instalação cancelada.\n")
            if keep_open:
                aguardar_enter(console)
            sys.exit(0)

    console.print()
    sucesso = run_rich(alvo, bundle)

    if keep_open:
        aguardar_enter(console)

    if not sucesso:
        sys.exit(1)


if __name__ == "__main__":
    main()
