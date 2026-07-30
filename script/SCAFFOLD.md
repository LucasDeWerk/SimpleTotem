# Scaffold — script/

Integração **CliSiTef** (TEF/pinpad). Consumido pelo backend via `sitef_service.py` / `sitef_worker.py`.

Contexto geral: [.cursor/cursor.md](../.cursor/cursor.md)

## Arquivos

| Arquivo | Papel |
|---------|-------|
| `CliSiTef.ini` | Config SiTef (IP, `TransacoesAdicionaisHabilitadas=7` para PIX, pinpad) |
| `pinpad_config.py` | Detecta Gertec PPC930 e atualiza `Porta` no ini |
| `instalar_permissoes_totem.sh` | **Instalação única** — udev + sudo sem senha + pinpad |
| `configurar_pinpad.sh` | udev + dialout + atualiza ini (chamado pelo instalador) |
| `run_sitef_worker.sh` | Wrapper SiTef executado como root (sudo NOPASSWD) |
| `simpletotem.sudoers` | Template sudoers para totem kiosk |
| `99-pinpad-gertec.rules` | Regra udev para `/dev/pinpad-gertec` |
| `test_clisitef.py` | Script de teste manual da lib CliSiTef |
| `fix_hosts.py` | Utilitário de correção de hosts para rede SiTef |
| `Cheque.txt` | Config de campos para modalidade cheque |
| `RELEASE.TXT` | Notas de versão da lib CliSiTef |
| `Leiame.txt` | Documentação da distribuição CliSiTef |
| `libclisitef.so` | Lib principal CliSiTef (binário, versionado) |
| `libcurl64.so` | Dependência HTTP da CliSiTef |
| `libemv64.so` | Lib EMV (chip) |
| `libqrencode64.so` | Lib QR Code (PIX) |
| `*_LICENSE.txt` | Licenças das libs |

## Pastas (runtime, não versionadas)

| Pasta | Papel |
|-------|-------|
| `transacoes/` | JSONs de transações de teste/produção |

## Agente

Tarefas aqui → **backend-agent**
