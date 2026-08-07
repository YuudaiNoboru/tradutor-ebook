## Why

O aplicativo suporta hoje apenas providers orientados a LLM, embora o fluxo de EPUB também se beneficie de tradutores automáticos gratuitos que não exigem credenciais do usuário. A integração do Google Web como primeiro provider comum, acompanhada de uma arquitetura modular para futuros providers, amplia o acesso sem sacrificar a preservação estrutural do EPUB.

## What Changes

- Introduzir duas famílias de providers: LLMs e APIs de tradução automática.
- Separar as portas de domínio para preservar os contextos distintos: LLMs suportam glossário/priming; tradutores comuns recebem apenas idiomas e conteúdo.
- Organizar adapters em módulos descobertos automaticamente nas pastas `providers/llm/` e `providers/machine_translation/`, permitindo adicionar um provider por novo arquivo.
- Implementar o Google Web gratuito como provider experimental, sem exigir chave do usuário, com endpoint HTML, fallback controlado, limites conservadores, retry e retomada por cache.
- Preparar o contrato para o Microsoft Edge gratuito, sem implementá-lo nesta mudança.
- Adaptar o pipeline para ignorar glossário, priming, política de termos e apêndice quando o provider comum não oferecer esses recursos.
- Manter XHTML, tags inline, placeholders e blocos protegidos intactos; falhas de preservação devem impedir a gravação de uma tradução inválida.
- Atualizar cache, estimativa/relatório de custo, configuração, tela de configuração e ajuda para refletirem família, capacidades, credenciais, limitações e estabilidade do provider.

## Capabilities

### New Capabilities

- `machine-translation-provider`: porta, capacidades, descoberta modular e adapter experimental do Google Web gratuito, com contrato de preservação de conteúdo.

### Modified Capabilities

- `llm-provider`: manter a porta de LLM separada e organizar adapters por provider sem misturar contratos de tradução automática.
- `translation-engine`: selecionar o fluxo de enriquecimento conforme as capacidades; tradutores comuns não executam glossário, priming ou apêndice.
- `translation-cache`: incluir identidade da família/provider/variante na chave e suportar retomada sem versão de glossário para providers comuns.
- `cost-control`: representar providers sem uso de tokens/custo mensurável sem afirmar que nenhum conteúdo foi processado.
- `configuration`: configurar família/provider e parâmetros específicos sem guardar credenciais públicas ou de usuário em texto puro.
- `ui-app`: permitir selecionar primeiro a família, exibir somente controles compatíveis e explicar as limitações do provider gratuito.

## Impact

- Afeta `src/tradutor/domain`, `src/tradutor/providers`, `src/tradutor/translate`, `src/tradutor/infra` e `src/tradutor/tui`.
- Exige novos contratos de resultado/capacidade, descoberta de módulos, políticas de lote e limitação de requisições.
- Usa `httpx` já presente; não adiciona dependência de browser ou SDK oficial.
- Exige testes falsos HTTP, testes dourados de XHTML e validação de retomada/cache.
- O Google Web gratuito depende de endpoints não oficiais da interface web e deve ser apresentado como experimental, sujeito a bloqueio ou mudança sem aviso.
