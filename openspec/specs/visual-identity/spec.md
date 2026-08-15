# visual-identity Specification

## Purpose

Define e provê a identidade visual oficial do aplicativo, incluindo logotipo de alta resolução, ícone Windows multi-resolução e padronização visual na documentação do projeto.

## Requirements

### Requirement: Ativos de identidade visual e ícone do aplicativo
O repositório MUST conter o logotipo oficial (`assets/logo.png`) e o arquivo de ícone multi-resolução para Windows (`assets/app.ico`) derivados do design Conceito 6B (Papel Minimalista).

#### Scenario: Presença dos arquivos de imagem e ícone
- **WHEN** os assets do projeto são verificados
- **THEN** `assets/logo.png` existe em alta resolução e `assets/app.ico` contém as resoluções padrão Windows (16x16, 24x24, 32x32, 48x48, 64x64, 128x128, 256x256)

### Requirement: Embutimento do ícone no executável e instalador
O processo de build do PyInstaller e do Inno Setup MUST embutir o ícone oficial `assets/app.ico` nos binários gerados.

#### Scenario: Compilação com ícone oficial
- **WHEN** `tradutor.exe` e `tradutor-ebook-setup.exe` são compilados
- **THEN** ambos os executáveis exibem o ícone oficial no Windows Explorer, na barra de tarefas e nos atalhos gerados

### Requirement: Exibição da marca no README do projeto
O arquivo `README.md` MUST apresentar o logotipo oficial centralizado na seção inicial de apresentação do projeto.

#### Scenario: Renderização do README
- **WHEN** o usuário visualiza o `README.md` no repositório ou documentação
- **THEN** a imagem do logotipo oficial `assets/logo.png` é exibida no topo do documento com descrição do aplicativo
