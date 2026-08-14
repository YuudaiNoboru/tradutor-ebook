# Modificação Rápida: Correção do Auto-Updater no Windows (PowerShell helper e flags de subprocess)

*(preenchido em conjunto por desenvolvedor e IA — sem debate de trade-offs, sem ADR)*

## O que muda
1. **`src/tradutor/infra/updater.py`**:
   - Correção do disparo de subprocesso no Windows: remoção da combinação inválida `CREATE_NO_WINDOW | DETACHED_PROCESS` que causava `WinError 87: The parameter is incorrect`. Utilização de `CREATE_NO_WINDOW` isolado para o launcher do processo.
   - Substituição do script `.bat` por um script PowerShell (`update_helper.ps1`) executado via `powershell.exe -NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File ...`.
   - Script PowerShell realiza: espera pelo encerramento do PID pai (`WaitForExit`), renomeação atômica (`Move-Item` com fallback para `.old`), movimentação do executável novo, limpeza dos arquivos temporários e relançamento do executável atualizado via `Start-Process`.
   - Em caso de falha de substituição, restaura o executável original, descarta arquivos temporários do cache para não travar o usuário e relança a aplicação original.
   - Encerramento do processo Python através de `os._exit(0)` após disparar o helper para garantir a liberação imediata dos file locks no Windows.
   - Adição da função `clear_pending_update()` para descartar atualizações pendentes.
2. **`src/tradutor/tui/app.py` & `src/tradutor/tui/screens/update.py`**:
   - Ajuste em `on_mount()`: ao detectar atualização pendente em cache (`check_delayed_update`), abre o `UpdateModal` no estado `downloaded` permitindo ao usuário decidir se reinicia, adia ou descarta a atualização, eliminando o timer forçado de 2 segundos que causava loop infinito de reinicializações quando havia falha.
   - Suporte a `initial_state` e botão de descarte no `UpdateModal`.

## Por que
No Windows compilado, ao tentar aplicar uma atualização baixada, `subprocess.Popen` falhava silenciosamente devido a flags inválidas no Win32 `CreateProcessW`. O executável antigo fechava mas o script nunca era executado, mantendo `pending_update.exe` no cache. Ao reabrir o app, `on_mount()` entrava em loop forçando novo fechamento a cada 2 segundos.

## Arquivos afetados
- `src/tradutor/infra/updater.py`
- `src/tradutor/tui/app.py`
- `src/tradutor/tui/screens/update.py`
- `tests/infra/test_updater.py`
- `tests/tui/test_updater_tui.py`

## Risco de Regressão
Baixo — afeta exclusivamente o fluxo de auto-atualização do executável empacotado no Windows, mantendo as interfaces públicas de `infra/updater.py` e isolamento arquitetural.

## Precisa de teste novo?
Sim: testes unitários em `tests/infra/test_updater.py` validando geração do script PowerShell, argumentos do `Popen`, função `clear_pending_update`, e testes de TUI em `tests/tui/test_updater_tui.py` cobrindo o modal no estado `downloaded` ao iniciar.

---

## ⚠️ Trava de Escalonamento

- Introduz um Ator/papel de usuário novo? não
- Cria ou muda uma regra de acoplamento entre componentes já registrada no `arquitetura.html`? não
- Contraria ou exige revisar um ADR aprovado? não
- Muda comportamento observável de forma que mereça uma decisão arquitetural registrada? não
