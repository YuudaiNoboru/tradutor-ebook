; Script de configuracao do Inno Setup para o LiberLingua
; Gera o instalador oficial para Windows (tradutor-ebook-setup.exe)

#ifndef MyAppVersion
#define MyAppVersion "0.6.0"
#endif

#define MyAppName "LiberLingua"
#define MyAppPublisher "YuudaiNoboru"
#define MyAppURL "https://github.com/YuudaiNoboru/tradutor-ebook"
#define MyAppExeName "tradutor.exe"

[Setup]
AppId={{8B4A2C0D-9E1F-4B7A-8A1C-9E5F2D3A4B5C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=tradutor-ebook-setup
SetupIconFile=..\assets\app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "envpath"; Description: "Adicionar a pasta do programa ao PATH do usuario"; GroupDescription: "Configuracoes do Sistema:"; Flags: unchecked

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\assets\app.ico"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\app.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\app.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Registry]
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{reg:HKCU\Environment,Path|};{app}"; Tasks: envpath; Check: NeedsAddPath(ExpandConstant('{app}'))

[Code]
function NeedsAddPath(Param: string): boolean;
var
  OrigPath: string;
begin
  if not RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', OrigPath) then
  begin
    Result := True;
    exit;
  end;
  { Verifica se o caminho ja existe no PATH do usuario }
  Result := Pos(';' + Param + ';', ';' + OrigPath + ';') = 0;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  AppDir, OrigPath, NewPath: string;
  P: Integer;
begin
  if CurUninstallStep = usUninstall then
  begin
    AppDir := ExpandConstant('{app}');
    if RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', OrigPath) then
    begin
      P := Pos(';' + AppDir + ';', ';' + OrigPath + ';');
      if P > 0 then
      begin
        NewPath := ';' + OrigPath + ';';
        StringChangeEx(NewPath, ';' + AppDir + ';', ';', True);
        if Length(NewPath) > 1 then
        begin
          if NewPath[1] = ';' then Delete(NewPath, 1, 1);
          if (Length(NewPath) > 0) and (NewPath[Length(NewPath)] = ';') then Delete(NewPath, Length(NewPath), 1);
        end
        else
          NewPath := '';
        RegWriteStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', NewPath);
      end;
    end;
  end;
end;
