# Guia de Implementação de Novos Provedores de Tradução

Este guia orienta desenvolvedores e agentes de IA sobre como implementar, testar e registrar novos provedores de tradução no `tradutor-ebook`, respeitando a Arquitetura Hexagonal, as convenções de segurança e o sistema modular de descoberta dinâmica (sem registro central rígido).

---

## 1. Visão Geral e Arquitetura

No `tradutor-ebook`, os provedores funcionam como **Adaptadores de Saída (Output Adapters)** que conectam a aplicação a APIs remotas de Inteligência Artificial (LLMs) ou serviços de Tradução Automática (Machine Translation).

### Princípios Inegociáveis

1. **Isolamento do Domínio:** Os módulos em `src/tradutor/domain/` definem apenas contratos puros (`Protocol`, `dataclass`, `enum`). O domínio **nunca** importa bibliotecas de rede (`httpx`), SDKs proprietários ou módulos periféricos.
2. **Segurança de Credenciais (BYOK):** Chaves de API nunca são manipuladas como strings soltas no domínio nem gravadas em logs. Elas são recuperadas sob demanda através da porta `SecretStore` (`src/tradutor/domain/secrets.py`).
3. **Descoberta Dinâmica de Módulos:** Novos provedores não requerem edição de um dicionário central. O mecanismo `tradutor.providers.discovery` descobre automaticamente submódulos em `src/tradutor/providers/llm/` e `src/tradutor/providers/machine_translation/` via `pkgutil`.

---

## 2. Famílias de Provedores e Contratos

O sistema divide os provedores em duas famílias principais (`ProviderFamily` em `src/tradutor/domain/providers.py`):

### A. Provedores LLM (`ProviderFamily.LLM`)

Usados para tradução baseada em contexto literário, suporte a glossário e priming estilístico.

- **Protocolo:** `LLMTranslator`
- **Contexto:** `LLMContext` (contém `source_language`, `target_language`, `policy`, `glossary`, `priming`, `task`)
- **Retorno:** `TranslationBatch` (contém `texts: tuple[str, ...]`, `usage: Usage`)

```python
class LLMTranslator(Protocol):
    identity: ProviderIdentity
    capabilities: ProviderCapabilities

    def translate(self, batch: Sequence[Block], context: LLMContext) -> TranslationBatch: ...

    def test_connection(self) -> ConnectionResult: ...  # Recomendado
```

### B. Provedores de Tradução Automática (`ProviderFamily.MACHINE_TRANSLATION`)

Usados para tradução direta sem dependência de credenciais ou para fallbacks rápidos.

- **Protocolo:** `MachineTranslationProvider`
- **Contexto:** `MachineTranslationContext` (contém `source_language`, `target_language`)
- **Retorno:** `TranslationBatch`

```python
class MachineTranslationProvider(Protocol):
    identity: ProviderIdentity
    capabilities: ProviderCapabilities

    def translate(
        self, batch: Sequence[Block], context: MachineTranslationContext
    ) -> TranslationBatch: ...

    def test_connection(self) -> ConnectionResult: ...
```

---

## 3. Metadados e Capacidades do Provedor

Todo módulo de provedor deve exportar uma constante `DESCRIPTION` do tipo `ProviderDescription`:

```python
from tradutor.domain import (
    ProviderCapabilities,
    ProviderDescription,
    ProviderFamily,
    ProviderIdentity,
    ProviderStability,
)

DESCRIPTION = ProviderDescription(
    identity=ProviderIdentity(
        family=ProviderFamily.LLM,
        provider_id="meu-provedor",
        version="1",
        transport_variant="default",
    ),
    capabilities=ProviderCapabilities(
        family=ProviderFamily.LLM,
        supports_glossary=True,
        supports_priming=True,
        supports_term_policy=True,
        supports_html=True,
        requires_credentials=True,
        stability=ProviderStability.STABLE,
        max_batch_items=32,
        max_concurrency=10,
        latency_seconds=60.0,
        max_output_tokens=8192,
        reports_token_usage=True,
        supports_model_listing=True,
        supports_connection_test=True,
        has_pricing=True,
    ),
    display_name="Meu Provedor IA",
    description="Provedor de tradução de alta fidelidade usando Meu Provedor.",
)
```

---

## 4. Tratamento de Erros e Rate Limiting

O pipeline de tradução depende da categorização correta das exceções para decidir entre tentar novamente com backoff ou abortar a operação:

### Hierarquia de Exceções (`tradutor.providers.errors`)

1. **`TransientProviderError`:**
   - Erros temporários de rede, timeouts, status HTTP 429 (Rate Limit), erros 5xx de servidor.
   - O orquestrador aplica retry exponencial com jitter e respeita o cabeçalho `Retry-After` quando disponível.
2. **`AuthenticationError`:**
   - Chave de API inválida, ausente ou expirada (HTTP 401/403).
   - Interrompe o fluxo imediatamente orientando o usuário a reconfigurar sua chave.
3. **`DefinitiveProviderError`:**
   - Payload rejeitado, modelo inexistente, requisições malformadas ou incompatíveis.
   - Não dispara retry.

### Exemplo de Tratamento de Rate Limit com HTTPX

```python
import httpx
from tradutor.providers.errors import (
    AuthenticationError,
    DefinitiveProviderError,
    TransientProviderError,
)


def _handle_http_error(response: httpx.Response) -> None:
    if response.status_code in (401, 403):
        raise AuthenticationError(f"Chave de API inválida (HTTP {response.status_code})")
    if response.status_code == 429 or 500 <= response.status_code < 600:
        raise TransientProviderError(
            f"Instabilidade temporária no provedor (HTTP {response.status_code})"
        )
    if response.is_error:
        raise DefinitiveProviderError(f"Erro definitivo da API: {response.text}")
```

---

## 5. Função Fábrica (`create_provider`)

Todo módulo de provedor deve exportar uma função `create_provider` compatível com a assinatura requerida pelo `discovery.py`:

```python
from typing import Any
from tradutor.domain import SecretStore


def create_provider(secret_store: SecretStore, **kwargs: Any) -> MeuProvedor:
    """Instancia o provedor injetando o cofre de credenciais e parâmetros de configuração."""
    return MeuProvedor(secret_store=secret_store, **kwargs)
```

---

## 6. Passo a Passo para Criar um Novo Provedor

### Passo 1: Escolher a pasta correta
- Se for LLM: `src/tradutor/providers/llm/<nome_do_provedor>.py`
- Se for Machine Translation: `src/tradutor/providers/machine_translation/<nome_do_provedor>.py`

### Passo 2: Implementar a classe do provedor
- Herdar/implementar os métodos de `LLMTranslator` ou `MachineTranslationProvider`.
- Implementar `test_connection()` retornando `ConnectionResult(ok=True/False, message="...", models=(...))`.
- Validar a fidelidade estrutural dos blocos traduzidos usando as funções puras de `tradutor.domain` (ex: `mask_markup`, `unmask_markup`, `is_faithful`).

### Passo 3: Declarar `DESCRIPTION` e `create_provider`
- Exportar `DESCRIPTION = ProviderDescription(...)`
- Exportar `create_provider(...)`

### Passo 4: Criar testes com Mock de Rede
- Adicionar testes unitários e de integração em `tests/providers/test_<nome_do_provedor>.py`.
- Utilizar `respx` para mockar endpoints HTTP sem fazer chamadas externas reais.

### Passo 5: Executar o Sensor de Qualidade
- Rodar checagem de tipos: `hatch run typecheck`
- Rodar checagem de arquitetura: `hatch run arch-check`
- Rodar linter e formatador: `hatch run lint` && `hatch run fmt-check`
- Rodar a suíte com gate de cobertura: `hatch run cov` (deve manter `>= 95%`)

---

## 7. Checklist de Conformidade

- [ ] O módulo está localizado sob `src/tradutor/providers/llm/` ou `src/tradutor/providers/machine_translation/`.
- [ ] Exporta `DESCRIPTION` com `identity` e `capabilities` preenchidas de forma consistente.
- [ ] Exporta a função `create_provider(secret_store, **kwargs)`.
- [ ] Implementa o método `translate(...)` devolvendo um `TranslationBatch`.
- [ ] Implementa `test_connection()` com retorno `ConnectionResult`.
- [ ] Trata erros mapeando para `TransientProviderError`, `AuthenticationError` ou `DefinitiveProviderError`.
- [ ] Nunca loga tokens, segredos ou senhas em texto puro.
- [ ] `hatch run typecheck` passa sem erros.
- [ ] `hatch run arch-check` confirma ausência de dependências ilegais.
- [ ] A cobertura de testes do novo módulo é de 100% de branches.
