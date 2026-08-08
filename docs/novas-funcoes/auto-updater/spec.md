# Especificação da Funcionalidade: Auto-atualização de Executável (.exe) no Windows

---

## 1. Entrada do Desenvolvedor: Mapeamento de Atores & Ações

### Contexto / Objetivo Resumido
Proporcionar a geração e publicação de um executável único (`.exe`) para Windows nas releases do GitHub, permitindo que a aplicação faça a checagem automática (ou sob demanda) de novas versões, realize o download em segundo plano e se auto-atualize de forma segura contornando as travas de arquivo em uso do Windows.

### Papéis de Usuário Envolvidos
- **Leitor** (Único perfil de usuário final do tradutor de e-books).

### Ator: Leitor
- **US-01:** Como Leitor no Windows, eu quero ir até a página de Releases do GitHub e baixar o executável único `.exe` do projeto para rodar a aplicação diretamente.
- **US-02:** Como Leitor, quero que o app verifique de forma automática e assíncrona na inicialização se existe uma versão nova disponível e, caso exista, me avise por meio de um popup/modal na TUI.
- **US-03:** Como Leitor, quero poder aceitar a atualização imediatamente, fazendo com que o app faça o download, se encerre, instale a atualização e reinicie sozinho.
- **US-04:** Como Leitor, se eu optar por não fechar o app imediatamente após o download da atualização, eu quero que ela seja salva localmente e que na próxima inicialização o app se atualize de forma automática (sem perguntar novamente, já que a atualização já foi autorizada e baixada).
- **US-05:** Como Leitor, quero ver sempre a versão atual em execução de forma clara e visível no rodapé da TUI.
- **US-06:** Como Leitor, quero ter a opção de desativar a verificação automática de novas versões na tela de configurações do aplicativo e também ter um botão nessa mesma tela para checar atualizações manualmente sob demanda.

### Ator: Desenvolvedor
- **DEV-01:** Como desenvolvedor, quero que o executável para Windows seja gerado automaticamente no pipeline de CI/CD do GitHub Actions sempre que uma nova tag de release `v*` for empurrada ao repositório.
- **DEV-02:** Como desenvolvedor, quero garantir que a versão mostrada no rodapé da TUI e na comparação do auto-update seja sempre sincronizada de forma dinâmica com o número de versão controlado pelo Commitizen (`__version__`), sem necessidade de edição manual.
- **DEV-03:** Como desenvolvedor, quero que as dependências e backends dinâmicos (como keyring para senhas e tiktoken para contagem de tokens) funcionem perfeitamente dentro do ambiente compilado (frozen) do PyInstaller.

### Ator: Sistema (Automações / Background)
- **SYS-01:** O sistema deve executar a compilação do executável usando PyInstaller na plataforma `windows-latest` no pipeline de GitHub Actions e anexá-lo como artefato da release.
- **SYS-02:** O sistema deve consultar a API do GitHub (`/repos/YuudaiNoboru/tradutor-ebook/releases/latest`) para buscar a última versão disponível em formato JSON e compará-la com o `__version__` local.
- **SYS-03:** O sistema deve forçar a ativação do backend nativo do Windows Credential Manager (`WinVaultKeyring`) no `keyring` caso o app esteja executando empacotado (frozen).
- **SYS-04:** O sistema deve gerenciar o processo de substituição de binários no Windows gerando um script batch `.bat` temporário que monitora o processo original até que ele seja encerrado, realiza a cópia, exclui a si mesmo e reinicia a nova versão do aplicativo.

---

## 2. Análise Arquitetônica & Trade-offs

### Características Arquitetônicas Críticas (-ilities)
- **Coesão de Componentes:** Isolamento total das operações de sistema operacional (download, gravação no cache, geração e execução de scripts batch) em um componente dedicado de infraestrutura (`infra/updater.py`), mantendo o domínio do tradutor limpo e a interface TUI focada estritamente em renderização e interação.
- **Portabilidade:** Embora o recurso de auto-atualização seja desenhado exclusivamente para o ambiente Windows compilado, todas as chamadas e inicializações são encapsuladas por guardas de plataforma (`sys.platform == "win32"` e `sys.frozen`) para que o aplicativo continue rodando e compilando perfeitamente em macOS/Linux e em ambiente de desenvolvimento local.
- **Robustez & Confiabilidade:** Garantir que o processo de download seja atômico (arquivos incompletos não disparam atualizações) e resiliente a falhas de rede (timeouts e perda de conexão falham de forma silenciosa e amigável).

### Trade-offs Aceitos
> **Decisão de Trade-off:** Optou-se por usar um script Batch temporário executado nativamente pelo Windows para realizar a substituição física do arquivo executável. 
> * **Sacrifício:** Uma janela rápida e vazia do prompt de comando do Windows pode piscar na tela do usuário enquanto a cópia do binário é efetuada em segundo plano.
> * **Ganho:** Portabilidade e Robustez absoluta. Scripts `.bat` clássicos funcionam em todas as versões do Windows sem sofrer restrições de permissões ou de políticas de execução (ExecutionPolicy) que comumente bloqueiam execuções automáticas de scripts do PowerShell na máquina do usuário final.

---

## 3. Estrutura Física & Módulos

### Mapeamento no Projeto Existente
```text
C:\Users\vasco\Software\tradutor-ebook/
├── src/
│   └── tradutor/
│       ├── __init__.py                      <-- [MODIFICADO] (exporta a variável __version__ global)
│       ├── cli.py                           <-- [MODIFICADO] (configura keyring explícito em ambientes frozen)
│       ├── infra/
│       │   ├── config.py                    <-- [MODIFICADO] (esquema TOML com suporte ao bloco [update] e auto_check)
│       │   └── updater.py                   <-- [NOVO COMPONENTE COESO] (lógica de consulta API, download e script de patch)
│       └── tui/
│           ├── app.py                       <-- [MODIFICADO] (controle do fluxo de update na inicialização e layout de rodapé)
│           └── screens/
│               └── config.py                <-- [MODIFICADO] (inclusão do controle de update automático e botão de checagem manual)
├── .github/
│   └── workflows/
│       └── release.yml                      <-- [MODIFICADO] (job em windows-latest para compilar via PyInstaller e fazer upload)
```

### Regras de Acoplamento & Limites
- **Pode Importar:** `tradutor.infra.updater` pode importar `httpx`, `platformdirs`, `subprocess`, `sys`, `pathlib`, `json`, `os`, `tradutor.infra.config`.
- **NÃO Pode Importar:** `tradutor.infra.updater` não pode importar nenhum componente de apresentação (`tradutor.tui`).
- **Padrão de Comunicação:** A TUI (`TradutorApp` e `ConfigScreen`) importa diretamente as funções/classes de `tradutor.infra.updater` para iniciar a checagem, baixar a atualização ou disparar a auto-substituição.

---

## 4. Fluxo de Execução & Casos de Borda

### Sequência Lógica
1. **[Inicialização e Verificação de Cache]:** Na montagem da TUI (`on_mount` no `TradutorApp`), se a plataforma for Windows e estiver rodando de executável frozen, o app checa o cache dedicado (`platformdirs.user_cache_dir("tradutor-ebook")`) por atualizações pendentes (`pending_update.exe` e `pending_update.json`).
   - Se houver atualização pendente gravada e sua versão listada for maior que `__version__`:
     - O app exibe mensagem informando que vai reiniciar para aplicar a atualização pendente.
     - Executa o script batch temporário e se encerra (`sys.exit()`). A atualização é aplicada e o app é reiniciado.
2. **[Checagem Assíncrona Online]:** Se não houver atualização pendente em cache e a configuração `update.auto_check` for verdadeira, o app inicia uma thread/tarefa assíncrona para consultar o GitHub (`/releases/latest`).
3. **[Sinalização e Consentimento]:** Se uma versão mais recente for encontrada no GitHub:
   - Exibe-se um modal de notificação avisando ao usuário e perguntando se deseja baixar.
   - Caso o usuário aceite, o app baixa o binário em segundo plano diretamente para a pasta temporária de cache, gravando-o como `pending_update.exe` e gerando o `pending_update.json` de metadados somente após a conclusão completa e bem-sucedida do download (download atômico).
4. **[Reinicialização Imediata ou Delayed Update]:**
   - Com o download concluído, exibe-se um novo aviso perguntando se deseja fechar e atualizar agora.
   - Se o usuário aceitar: grava o arquivo `update_helper.bat` apontando para o executável ativo (`sys.executable`), inicia o subprocesso batch de forma assíncrona e executa `sys.exit()`.
   - Se o usuário recusar: o app continua em execução normal. A atualização fica em cache e será processada no próximo início do app (etapa 1).

### Casos de Borda e Erros
- **Falhas de Conectividade / Rede:** No caso de erros na chamada de rede do GitHub (timeout, DNS, quedas de internet), a checagem deve falhar silenciosamente no boot e, em caso de checagem manual nas configurações, deve apresentar uma mensagem amigável sem interromper a execução da aplicação.
- **Download Incompleto / Corrupção:** O download é feito primeiro em arquivo temporário (ex: `pending_update.exe.tmp`). O arquivo temporário só substitui o `pending_update.exe` de cache e gera o arquivo de metadados JSON após a validação completa de tamanho e encerramento correto do fluxo HTTP.
- **Executável Original Trancado no Windows:** O script batch `update_helper.bat` implementa um loop ativo usando comandos `tasklist` e `findstr` consultando o PID do aplicativo atual. A substituição (`copy /y`) só é executada quando o processo pai tiver desaparecido da listagem de processos ativos do sistema operacional.
- **Falha de Escrita no Diretório de Destino:** Caso o executável original esteja em uma pasta sem direitos de gravação, o batch registrará falha. Para mitigar isso, o processo de cópia no batch pode verificar se o arquivo original foi substituído; caso contrário, relança o app original e limpa a pasta de cache.

---

## 5. Proposta de ADR — Registro de Decisão Arquitetônica

- **Título:** ADR-05: Auto-atualização de Executável no Windows via Script Batch e Cache de Inicialização
- **Contexto:** Distribuir a aplicação no formato de executável único de Windows (`.exe`) exige um mecanismo de atualização autônoma e fluida. O Windows proíbe um executável em execução de ser apagado ou substituído por si mesmo diretamente.
- **Decisão:** Decidiu-se implementar um updater baseado em dois pilares:
  1. **Delayed Update via cache local:** Novas versões baixadas são armazenadas em formato dormente no diretório de cache do usuário (`platformdirs.user_cache_dir("tradutor-ebook")`) acompanhadas de um manifesto JSON. A substituição é disparada imediatamente caso o usuário confirme o reinício, ou é aplicada de forma totalmente automatizada no boot seguinte se o usuário tiver optado por adiar a instalação.
  2. **Substituição nativa com Batch (.bat):** O processo de substituição em tempo de desligamento é delegado a um arquivo `.bat` temporário criado sob demanda que aguarda o encerramento do PID do executável principal antes de executar a cópia, relançar o aplicativo atualizado e deletar a si mesmo.
- **Consequências:**
  - *Impacto Positivo:* Compatibilidade garantida em qualquer instalação padrão de Windows, sem dependência de configurações de segurança ou ExecutionPolicy do PowerShell. Transparência operacional completa.
  - *Impacto Negativo:* Abertura efêmera e visível da janela do prompt de comando durante a troca do binário no desligamento do sistema.

---

## 6. Funções de Aptidão (Fitness Functions) & Critérios de Aceite

- [ ] **Coesão & Isolamento:** Testes unitários do módulo `infra/updater.py` cobrem a lógica de detecção de versão pendente e comparação sem instanciar a TUI ou interagir de fato com o GitHub (usando `respx` para simular as APIs).
- [ ] **Acoplamento Limpo:** O arquivo `src/tradutor/infra/updater.py` não contém importações de componentes de tela ou widgets da TUI (`tradutor.tui`).
- [ ] **Tratamento de Exceções:** Nenhuma falha de rede ou de sistema de arquivos decorrente da verificação ou download interrompe ou fecha o aplicativo inesperadamente.
- [ ] **Sem Hardcode:** A versão local comparada é obtida estritamente de `tradutor.__version__`, que por sua vez é atualizada automaticamente pelo fluxo de tags do Git/Commitizen.
- [ ] **Windows-Specific Safety:** Lógica de keyring específica do Windows e de substituição batch do updater são protegidas por condições de plataforma (`sys.platform == "win32"` e `sys.frozen`).
- [ ] **Comutabilidade:** A configuração `update.auto_check` inserida no TOML desativa com sucesso a consulta assíncrona automática no início da aplicação.
