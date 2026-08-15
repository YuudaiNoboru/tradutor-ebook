# Modificação Rápida: Retry com backoff em escrita atômica de estado no Windows

*(preenchido em conjunto por desenvolvedor e IA — sem debate de trade-offs, sem ADR)*

## O que muda

1. **`src/tradutor/translate/estado.py`**:
   - Criação da função `safe_replace(src, dst, max_attempts=5, initial_delay=0.05)` para encapsular `os.replace` com política de repetição com backoff exponencial caso ocorra erro transitório de lock no Windows (`PermissionError`, `WinError 5: Acesso negado` ou `WinError 32: Violação de compartilhamento`).
   - Atualização de `save_estado` para utilizar `safe_replace(tmp, dest)` em vez de `os.replace(tmp, dest)` diretamente.
2. **`src/tradutor/translate/glossary_store.py`**:
   - Atualização de `save_glossary` para utilizar `safe_replace(tmp, dest)`.
3. **`src/tradutor/infra/secrets.py`**:
   - Atualização de `EncryptedFileSecretStore._save` com retry equivalente para proteger gravação do cofre no Windows.
4. **`tests/translate/test_estado.py`**:
   - Testes unitários para `safe_replace` cobrindo sucesso após falha transitória, tratamento de falhas permanentes (reraise com limpeza de `.tmp`) e repasse imediato de erros não relacionados a lock (ex: disco cheio).

## Por que

No Windows, especialmente durante traduções com provedores rápidos como Google Web Translation, arquivos de estado (`estado.json`) sofrem gravações atômicas sucessivas em intervalos de milissegundos. Quando o antivírus (como o Windows Defender), o indexador do Windows ou o próprio sistema de arquivos NTFS mantêm um lock temporário de leitura sobre o arquivo recém-gravado, chamadas imediatas a `os.replace` falham com `PermissionError: [WinError 5] Acesso negado`, abortando todo o processo de tradução mesmo com o conteúdo íntegro e a API funcionando. O retry com backoff de frações de segundo absorve esses bloqueios transitórios.

## Arquivos afetados

- `src/tradutor/translate/estado.py`
- `src/tradutor/translate/glossary_store.py`
- `src/tradutor/infra/secrets.py`
- `tests/translate/test_estado.py`

## Risco de Regressão

Muito baixo — a operação continua sendo atômica via arquivo temporário + substituição, mantendo a compatibilidade de formato e comportamento em sistemas Linux/macOS e adicionando resiliência a locks no Windows.

## Precisa de teste novo?

Sim: testes unitários em `tests/translate/test_estado.py` validando o comportamento de repetição em `PermissionError` / `WinError 5`, falha após esgotamento de tentativas e repasse sem espera para outros `OSError`.

---

## ⚠️ Trava de Escalonamento

- Introduz um Ator/papel de usuário novo? não
- Cria ou muda uma regra de acoplamento entre componentes já registrada no `arquitetura.html`? não
- Contraria ou exige revisar um ADR aprovado? não
- Muda comportamento observável de forma que mereça uma decisão arquitetural registrada? não
