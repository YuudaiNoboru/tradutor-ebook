## Context

O projeto possui uma porta `Translator` orientada a LLM, um adapter OpenAI-compatível e um orquestrador que sempre executa glossário, priming, lotes por tokens e relatório de tokens. A segmentação XHTML já extrai placeholders para conteúdo protegido e reconstrói apenas o interior dos blocos, o que deve continuar sendo a fronteira de segurança da formatação.

O Google Web gratuito usa endpoints da interface web e não é a API oficial autenticada. O adapter precisa, portanto, tratar endpoint, formato de resposta, limites e estabilidade como dados versionáveis. A proposta e os deltas de especificação definem o comportamento esperado.

## Goals / Non-Goals

**Goals:**

- Separar contratos de LLM e tradução automática sem duplicar a orquestração de EPUB.
- Permitir descoberta de providers por módulos nas famílias `llm` e `machine_translation`.
- Entregar Google Web experimental com transporte HTML, fallback controlado, limites conservadores e retomada.
- Fazer a preservação de tags inline, placeholders, blocos protegidos e estrutura do EPUB prevalecer sobre sucesso da tradução.
- Adaptar configuração, UI, cache e relatório às capacidades declaradas por cada provider.
- Manter compatibilidade de configuração com o provider DeepSeek existente.

**Non-Goals:**

- Implementar Microsoft Edge nesta mudança; apenas deixar a porta e a descoberta prontas.
- Criar integração com browser, WebView ou a API JavaScript local do Microsoft Edge.
- Adicionar glossário, priming, política de termos ou apêndice ao fluxo de tradução automática.
- Prometer disponibilidade, limites ou gratuidade permanentes para endpoints não oficiais.
- Alterar o formato de saída para bilíngue ou ampliar o suporte além de EPUB 2/3.

## Decisions

### 1. Duas portas e um resultado comum

O domínio terá uma porta de LLM com contexto rico e uma porta de tradução automática com idiomas e blocos. Ambas produzirão um resultado alinhado, mas o relatório de uso será generalizado para suportar tokens opcionais e contagem de caracteres/blocos.

Alternativa rejeitada: adaptar o provider comum à porta LLM e retornar `Usage(0, 0)`. Isso esconderia a diferença semântica e faria o relatório afirmar zero tokens, em vez de “uso não reportado”.

### 2. Capacidades como contrato de integração

Cada módulo exporá uma descrição de provider com família, nome estável, capacidades de contexto, formato, autenticação, estabilidade, limites de lote, telemetria e suporte a teste/listagem. O pipeline e a UI consumirão essa descrição para decidir quais etapas e controles são válidos.

Alternativa rejeitada: verificar nomes como `google` ou `deepseek` espalhados pelo código. Isso tornaria a adição de providers dependente de alterações em vários pontos.

### 3. Descoberta por módulos

`providers/llm/` e `providers/machine_translation/` serão pacotes de módulos. Um descobridor carregará módulos permitidos, coletará suas descrições e fábricas e rejeitará IDs duplicados ou metadados inválidos. Um novo provider deverá ser adicionável como novo módulo, sem editar um registro central.

O adapter OpenAI-compatível permanecerá como componente compartilhado da família LLM; módulos como DeepSeek e OpenAI fornecerão a configuração e o nome apresentados na UI.

### 4. Formatação como invariável do pipeline

O provider receberá o conteúdo interno serializado do bloco, incluindo markup inline não protegido, enquanto a segmentação continuará protegendo `code`, `pre`, SVG, MathML, scripts, styles e placeholders. Após a resposta, o pipeline validará alinhamento, tags relevantes, placeholders, conteúdo não vazio e capacidade de reconstrução antes de persistir no cache.

O fallback de texto do Google será usado somente quando o conteúdo puder ser transportado sem perder markup; ele não poderá ser aplicado silenciosamente a um bloco XHTML cuja formatação não possa ser verificada.

Alternativa rejeitada: extrair somente texto puro e reconstruir a formatação por heurística. Isso viola a prioridade de preservação estrutural do aplicativo.

### 5. Google Web com perfis de transporte

O provider terá um perfil HTML primário para `translate-pa.googleapis.com/v1/translateHtml` e um perfil textual de fallback para `translate.googleapis.com/translate_a/t` (resposta alinhada por bloco, preservando markup inline e placeholders). O perfil HTML usa o corpo posicional `[[[textos], origem, destino], "wt_lib"]` em `application/json+protobuf` e a chave pública da interface web no cabeçalho `X-Goog-Api-Key` (sem ela o endpoint recusa chamadas não registradas); a chave é operacional, tem override no adapter, não é segredo do usuário nem é gravada no config. URLs, variante do corpo e versão do perfil ficarão encapsuladas no adapter e participarão da identidade de cache. Sem essa chave, o endpoint HTML recusa chamadas não registradas e o perfil textual assume o transporte, com a preservação de XHTML validada após a resposta antes de aceitar cada bloco. No perfil textual, as tags inline são mascaradas como tokens `@@N@@` antes do envio e restauradas após a resposta (o endpoint preserva esse formato, ao contrário de `{{N}}`, que o serviço às vezes corrompe), garantindo preservação byte a byte mesmo para tags com atributos; o verificador de fidelidade permanece como guarda final.

O adapter usará `httpx`, cliente injetável nos testes, timeout explícito, User-Agent compatível, limites conservadores de caracteres/itens e concorrência efetiva inicialmente igual a um. 429, 5xx, timeout, falha de transporte e respostas transitórias serão classificadas para backoff; respostas incompatíveis ou bloqueios persistentes produzirão erro acionável.

### 6. Pipeline condicional por família

O serviço de execução consultará capacidades antes das passadas. LLMs mantêm glossário, priming, política, estimativa de tokens e apêndice. Providers comuns pulam essas etapas, usam lote por caracteres/itens, não criam glossário e reportam telemetria não mensurável quando aplicável.

### 7. Cache compatível e migração conservadora

O identificador de cache incluirá família, provider e variante de transporte além dos parâmetros já existentes. Configurações antigas sem família serão interpretadas como LLM/DeepSeek quando o provider salvo for `deepseek`; estados cuja chave não puder ser provada compatível serão ignorados e reprocessados.

### 8. UI orientada por capacidades

A tela selecionará primeiro a família e depois o provider. Modelo/chave/glossário/priming aparecerão somente quando suportados. Providers comuns terão teste de conexão sem listagem de modelos, aviso experimental e parâmetros de limite/atraso. A estimativa e a ajuda usarão a mesma descrição de capacidades para evitar mensagens divergentes.

## Risks / Trade-offs

- **[Endpoint não oficial mudar ou desaparecer]** → encapsular perfis e variantes, manter fallback, identificar a variante no cache e mostrar erro de provider experimental; testes reais ficam fora do CI.
- **[Bloqueio por excesso de requisições]** → paralelismo conservador, atraso mínimo entre chamadas, backoff com jitter, limites pequenos, cache e retomada; não usar rotação de IP/proxy para contornar limites.
- **[Tradução alterar XHTML]** → validar markup/placeholders antes do cache e manter testes dourados byte-diff; uma tradução rejeitada nunca deve chegar ao writer.
- **[Resposta HTML variar entre endpoints]** → perfis de parsing estritos, fixtures por variante e fallback somente quando a preservação for verificável.
- **[Dados do livro enviados a serviços externos]** → aviso explícito na UI e ajuda, sem logs do conteúdo; providers locais/browser ficam fora deste escopo.
- **[Configuração/cache antigos quebrarem]** → defaults compatíveis para DeepSeek e invalidação segura de estados ambíguos.
- **[Complexidade excessiva para adicionar providers]** → manter capacidades e fábrica no módulo do provider, com testes de descoberta que garantam o fluxo “novo arquivo, novo provider”.

## Migration Plan

1. Introduzir tipos de família, capacidades, resultado de uso e portas sem remover imediatamente o adapter DeepSeek.
2. Mover/encapsular a implementação OpenAI-compatível sob a família LLM e preservar aliases de configuração existentes.
3. Adaptar o pipeline, cache, custo e UI para capabilities mantendo o fluxo LLM verde.
4. Adicionar descoberta e o adapter Google com cliente HTTP falso, fixtures de respostas e testes de preservação XHTML.
5. Fazer smoke test manual contra os endpoints reais, sem incluí-lo no CI, e documentar a variante validada.
6. Em caso de falha do Google, desabilitar o provider ou trocar seu perfil/fallback sem afetar LLMs nem os EPUBs já traduzidos.
