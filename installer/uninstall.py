#!/usr/bin/env python3
"""SimpleTotem — Desinstalador com interface rich."""
import os
import sys
import shutil
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


LARANJA = "#f57c00"

ITENS_BINARIOS = ["SimpleTotem", "SimpleTotem-backend"]
ITENS_DIRS    = ["SimpleTotem-ui", "script"]
ITENS_DADOS   = ["dados", ".env"]

PASSOS_NOMES = [
    "Removendo binários",
    "Removendo diretórios do sistema",
    "Removendo dados (banco + .env)",
    "Removendo atalho .desktop",
    "Removendo sudoers",
]


# ── Lógica de desinstalação ───────────────────────────────────────────────────

class Uninstaller:
    def __init__(self, alvo: Path, manter_dados: bool, log_fn):
        self.alvo = alvo
        self.manter_dados = manter_dados
        self.log = log_fn

    def remover_binarios(self):
        for nome in ITENS_BINARIOS:
            caminho = self.alvo / nome
            if caminho.exists():
                caminho.unlink()
                self.log(f"Removido: {nome}")
            else:
                self.log(f"Não encontrado: {nome}")

    def remover_dirs(self):
        for nome in ITENS_DIRS:
            caminho = self.alvo / nome
            if caminho.exists():
                shutil.rmtree(caminho)
                self.log(f"Removido: {nome}/")
            else:
                self.log(f"Não encontrado: {nome}/")

    def remover_dados(self):
        if self.manter_dados:
            self.log("Dados preservados (banco + .env)")
            return
        for nome in ITENS_DADOS:
            caminho = self.alvo / nome
            if caminho.is_dir():
                shutil.rmtree(caminho)
                self.log(f"Removido: {nome}/")
            elif caminho.exists():
                caminho.unlink()
                self.log(f"Removido: {nome}")

    def remover_desktop(self):
        desktop = Path.home() / ".local" / "share" / "applications" / "simpletotem.desktop"
        if desktop.exists():
            desktop.unlink()
            self.log(f"Removido: {desktop.name}")
        else:
            self.log("Atalho .desktop não encontrado")

    def remover_sudoers(self):
        sudoers = Path("/etc/sudoers.d/simpletotem")
        if sudoers.exists():
            if os.geteuid() == 0:
                sudoers.unlink()
                self.log("Removido: /etc/sudoers.d/simpletotem")
            else:
                self.log(f"AVISO: remova manualmente: sudo rm {sudoers}")
        else:
            self.log("sudoers não encontrado")


# ── Interface Rich ────────────────────────────────────────────────────────────

def run_rich(alvo: Path, manter_dados: bool):
    console = Console()
    estados = ["wait"] * len(PASSOS_NOMES)
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
            u = Uninstaller(alvo, manter_dados, log_fn)
            fns = [
                u.remover_binarios,
                u.remover_dirs,
                u.remover_dados,
                u.remover_desktop,
                u.remover_sudoers,
            ]
            for i, fn in enumerate(fns):
                step_fn(i, "run")
                fn()
                step_fn(i, "ok")

            # Remove diretório raiz se ficou vazio
            try:
                alvo.rmdir()
                log_fn(f"Diretório removido: {alvo}")
            except OSError:
                log_fn(f"Mantido (ainda tem conteúdo): {alvo}")

            sucesso = True
        except Exception as exc:
            import traceback
            erro_msg = str(exc)
            log_fn(traceback.format_exc())
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
        for i, nome in enumerate(PASSOS_NOMES):
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
        task = progress.add_task("Desinstalando...", total=len(PASSOS_NOMES))

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
                    progress.update(task, description=PASSOS_NOMES[idx])
            elif kind == "log":
                progress.console.print(f"   [dim]{item[1]}[/dim]")
            elif kind == "done":
                break

    console.print()
    console.print(render_passos())
    console.print()

    if sucesso:
        aviso_dados = "\n  Os dados foram [bold]preservados[/bold] em: " + str(alvo / "dados") if manter_dados else ""
        console.print(Panel(
            f"[bold green]  SimpleTotem desinstalado com sucesso![/bold green]{aviso_dados}",
            border_style="green",
            padding=(1, 4),
        ))
    else:
        console.print(Panel(
            f"[bold red]  Falha na desinstalação![/bold red]\n\n  {erro_msg}",
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

    if not HAS_RICH:
        alvo = Path(input("Diretório instalado [/opt/simpletotem]: ").strip() or "/opt/simpletotem")
        manter = input("Manter dados? [S/n]: ").strip().lower() not in ("n", "nao", "não", "no")
        u = Uninstaller(alvo, manter, lambda m: print(f"  {m}"))
        u.remover_binarios(); u.remover_dirs(); u.remover_dados()
        u.remover_desktop(); u.remover_sudoers()
        print("Desinstalado!")
        return

    console = Console()
    console.print()
    console.print(Panel(
        Text("SimpleTotem — Desinstalador", style=f"bold {LARANJA}", justify="center"),
        border_style=LARANJA,
        padding=(1, 4),
    ))
    console.print()

    padrao = "/opt/simpletotem"
    resposta = Prompt.ask("  [bold]Diretório instalado[/bold]", default=padrao)
    alvo = Path(resposta)

    if not alvo.exists():
        console.print(f"\n  [red]Diretório não encontrado: {alvo}[/red]\n")
        if keep_open:
            aguardar_enter(console)
        sys.exit(1)

    console.print()
    console.print(f"  [yellow]Isso removerá o SimpleTotem de:[/yellow] [bold]{alvo}[/bold]")
    if not Confirm.ask("  Tem certeza?", default=False):
        console.print("  Cancelado.\n")
        if keep_open:
            aguardar_enter(console)
        sys.exit(0)

    console.print()
    manter_dados = Confirm.ask("  Manter dados (banco SQLite + .env)?", default=True)

    console.print()
    sucesso = run_rich(alvo, manter_dados)

    if keep_open:
        aguardar_enter(console)

    if not sucesso:
        sys.exit(1)


if __name__ == "__main__":
    main()
