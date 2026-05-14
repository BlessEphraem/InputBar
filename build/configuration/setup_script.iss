; Dynamic variables received from CMake:
; AppName, AppVersion, AppPublisher, AppExeName, AppId
;
; Paths are relative to this file's location: build/configuration/
; Repo root is therefore: ..\..\

[Setup]
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=admin
UsedUserAreasWarning=no
; OutputDir handled by /O flag in CMake
OutputBaseFilename=InputBar_v{#AppVersion}_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\..\src\Assets\Icons\Logo.ico
UninstallDisplayIcon={app}\{#AppExeName}
CloseApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startupicon"; Description: "Start InputBar at Windows startup"; GroupDescription: "Windows Integration:"; Flags: unchecked

[Dirs]
; Pre-create writable directories so the app can write data without needing admin rights at runtime
Name: "{app}\Path";            Permissions: users-full
Name: "{app}\Data";            Permissions: users-full
Name: "{app}\Data\Themes";     Permissions: users-full
Name: "{app}\Plugins";          Permissions: users-full
Name: "{app}\Plugins\App";         Permissions: users-full
Name: "{app}\Plugins\Shell";       Permissions: users-full
Name: "{app}\Plugins\Everything";  Permissions: users-full

[Files]
Source: "..\..\build_dist\{#AppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs restartreplace uninsrestartdelete
; aliases.data is preserved across updates (user may have customised it)
Source: "..\..\src\Plugins\App\aliases.data"; DestDir: "{app}\Plugins\App"; Flags: onlyifdoesntexist uninsneveruninstall skipifsourcedoesntexist
; favorites.data is preserved across updates (user may have customised it)
Source: "..\..\src\Plugins\Shell\favorites.data"; DestDir: "{app}\Plugins\Shell"; Flags: onlyifdoesntexist uninsneveruninstall skipifsourcedoesntexist
; default_shell.json — only installed if absent so user changes are kept
Source: "..\..\src\Plugins\Shell\default_shell.json"; DestDir: "{app}\Plugins\Shell"; Flags: onlyifdoesntexist skipifsourcedoesntexist
; Everything plugin seed files — preserved across updates (user may have customised them)
Source: "..\..\src\Plugins\Everything\favorites.data"; DestDir: "{app}\Plugins\Everything"; Flags: onlyifdoesntexist uninsneveruninstall skipifsourcedoesntexist
Source: "..\..\src\Plugins\Everything\extensions.data"; DestDir: "{app}\Plugins\Everything"; Flags: onlyifdoesntexist uninsneveruninstall skipifsourcedoesntexist
; Config.json is created by the app on first launch (Path/ has users-full permissions).

[InstallDelete]
; Remove old Run plugin directory on upgrade (replaced by App/ + Shell/)
Type: filesandordirs; Name: "{app}\Plugins\Run"
; Remove bundled winkey_hook.exe from older versions (replaced by WinKeyHook daemon)
Type: files; Name: "{app}\Lib\Core\winkey_hook.exe"

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon
Name: "{userstartup}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: startupicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent shellexec

[Code]
const
  REG_UNINSTALL = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\';

var
  DataDirPage: TInputDirWizardPage;

{ Gracefully kill the application and its global hook before extracting files.
  This frees up file locks and prevents Windows Restart Manager from prompting
  the user to close other GUI applications. }
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM {#AppExeName} /T', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Sleep(2000);
  Result := '';
end;

function InitializeUninstall(): Boolean;
var
  ResultCode: Integer;
begin
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM {#AppExeName} /T', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Sleep(2000);
  Result := True;
end;

{ Tries all registry hives and returns the value, or '' if not found. }
function _RegQuery(const SubKey, ValueName: String; var OutStr: String): Boolean;
begin
  Result := RegQueryStringValue(HKLM,   SubKey, ValueName, OutStr) or
            RegQueryStringValue(HKLM32, SubKey, ValueName, OutStr) or
            RegQueryStringValue(HKLM64, SubKey, ValueName, OutStr) or
            RegQueryStringValue(HKCU,   SubKey, ValueName, OutStr);
end;

function _RegKey(): String;
begin
  Result := REG_UNINSTALL + '{#AppId}' + '_is1';
end;

function GetInstalledVersion(): String;
var s: String;
begin
  Result := '';
  if _RegQuery(_RegKey(), 'DisplayVersion', s) then Result := s;
end;

function GetInstallDir(): String;
var s: String;
begin
  Result := '';
  if _RegQuery(_RegKey(), 'InstallLocation', s) then
  begin
    Result := s;
    if (Length(Result) > 0) and (Result[Length(Result)] <> '\') then
      Result := Result + '\';
  end;
end;

function GetUninstallString(): String;
var s: String;
begin
  Result := '';
  _RegQuery(_RegKey(), 'UninstallString', s);
  Result := s;
end;

procedure InitializeWizard;
var
  _PrevDir: String;
begin
  DataDirPage := nil;
  { Only show the data directory page on a fresh install }
  if GetInstalledVersion() = '' then
  begin
    DataDirPage := CreateInputDirPage(
      wpSelectDir,
      'Data & Settings Location',
      'Where should InputBar store your settings, themes and history?',
      'You can change this later by editing Path\Config.json in the installation folder.' + #13#10 +
      'Leave as the default to store data alongside the application.',
      False, '');
    DataDirPage.Add('');
    DataDirPage.Values[0] := WizardDirValue();
    { Restore previously configured data dir from registry (survives uninstall+reinstall) }
    if RegQueryStringValue(HKCU, 'Software\Ephraem\InputBar', 'ConfigDirectory', _PrevDir) and (_PrevDir <> '') then
      DataDirPage.Values[0] := _PrevDir;
  end;
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
  { Refresh the default value with the install dir the user may have just changed }
  if (DataDirPage <> nil) and (PageID = DataDirPage.ID) then
    DataDirPage.Values[0] := WizardDirValue();
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if (DataDirPage <> nil) and (CurPageID = DataDirPage.ID) then
  begin
    if Trim(DataDirPage.Values[0]) = '' then
    begin
      MsgBox('Please select a valid directory.', mbError, MB_OK);
      Result := False;
    end;
  end;
end;

{ Always remove the startup shortcut — whether the user is doing a full
  uninstall or a "uninstall only" from the same-version dialog. }
procedure _RemoveStartupShortcut();
var
  ShortcutPath: String;
begin
  ShortcutPath := ExpandConstant('{userstartup}\{#AppName}.lnk');
  if FileExists(ShortcutPath) then
    DeleteFile(ShortcutPath);
end;

{ Read ConfigDirectory value from Path\Config.json, or '' if absent/default. }
function GetConfigDirFromFile(AppDir: String): String;
var
  JsonPath, ContentStr, Key, Segment: String;
  RawContent: AnsiString;
  KeyPos, StartPos, EndPos: Integer;
begin
  Result := '';
  JsonPath := AppDir + '\Path\Config.json';
  if not FileExists(JsonPath) then Exit;
  if not LoadStringFromFile(JsonPath, RawContent) then Exit;
  ContentStr := String(RawContent);

  Key    := '"ConfigDirectory"';
  KeyPos := Pos(Key, ContentStr);
  if KeyPos = 0 then Exit;

  Segment  := Copy(ContentStr, KeyPos + Length(Key), Length(ContentStr));
  StartPos := Pos('"', Segment);
  if StartPos = 0 then Exit;

  Segment  := Copy(Segment, StartPos + 1, Length(Segment));
  EndPos   := Pos('"', Segment);
  if EndPos = 0 then Exit;

  Result := Copy(Segment, 1, EndPos - 1);
  StringChange(Result, '\\', '\');
end;

{ Copy RelPath from AppDir to CustomDir (skip if dest exists), then remove from AppDir. }
procedure MoveSeedFile(AppDir, CustomDir, RelPath: String);
var
  SrcPath, DstPath, DstDir: String;
begin
  SrcPath := AppDir + '\' + RelPath;
  if not FileExists(SrcPath) then Exit;
  DstPath := CustomDir + '\' + RelPath;
  DstDir  := ExtractFileDir(DstPath);
  if not DirExists(DstDir) then
    ForceDirectories(DstDir);
  if not FileExists(DstPath) then
    CopyFile(SrcPath, DstPath, False);
  DeleteFile(SrcPath);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  Chosen, AppDir, JsonPath, Escaped, Content, CustomDir, _Effective: String;
begin
  if CurStep = ssPostInstall then
  begin
    AppDir    := ExpandConstant('{app}');
    CustomDir := '';

    if DataDirPage <> nil then
    begin
      { First install: write Config.json if user chose a custom data dir }
      Chosen := Trim(DataDirPage.Values[0]);
      if (Chosen <> '') and (CompareText(Chosen, AppDir) <> 0) then
      begin
        CustomDir := Chosen;
        JsonPath  := AppDir + '\Path\Config.json';
        Escaped   := Chosen;
        StringChange(Escaped, '\', '\\');
        Content := '{' + #13#10 + '    "ConfigDirectory": "' + Escaped + '"' + #13#10 + '}';
        SaveStringToFile(JsonPath, Content, False);
      end;
    end
    else
      { Update/reinstall: read existing Config.json to find custom dir }
      CustomDir := GetConfigDirFromFile(AppDir);

    { Relocate seed files ISS placed in app\Plugins\ to the custom data dir }
    if (CustomDir <> '') and (CompareText(CustomDir, AppDir) <> 0) then
    begin
      MoveSeedFile(AppDir, CustomDir, 'Plugins\App\aliases.data');
      MoveSeedFile(AppDir, CustomDir, 'Plugins\Shell\favorites.data');
      MoveSeedFile(AppDir, CustomDir, 'Plugins\Shell\default_shell.json');
      MoveSeedFile(AppDir, CustomDir, 'Plugins\Everything\favorites.data');
      MoveSeedFile(AppDir, CustomDir, 'Plugins\Everything\extensions.data');
    end;

    { Sync effective data dir to registry so a future reinstall can restore it }
    _Effective := CustomDir;
    if _Effective = '' then _Effective := AppDir;
    RegWriteStringValue(HKCU, 'Software\Ephraem\InputBar', 'ConfigDirectory', _Effective);

    { Remove leftover startup shortcut if task was not selected. }
    if not WizardIsTaskSelected('startupicon') then
      _RemoveStartupShortcut();
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
  begin
    { Seed files have uninsneveruninstall so Inno skips them.
      Delete them now so Inno can remove the empty Plugins sub-dirs. }
    DeleteFile(ExpandConstant('{app}\Plugins\App\aliases.data'));
    DeleteFile(ExpandConstant('{app}\Plugins\Shell\favorites.data'));
    DeleteFile(ExpandConstant('{app}\Plugins\Shell\default_shell.json'));
    DeleteFile(ExpandConstant('{app}\Plugins\Everything\favorites.data'));
    DeleteFile(ExpandConstant('{app}\Plugins\Everything\extensions.data'));
  end;

  if CurUninstallStep = usPostUninstall then
  begin
    _RemoveStartupShortcut();

    if MsgBox('Do you want to delete all user data (settings, themes, history) and the installation folder?', mbConfirmation, MB_YESNO) = IDYES then
      DelTree(ExpandConstant('{app}'), True, True, True);
  end;
end;

function InitializeSetup(): Boolean;
var
  OldVersion: String;
  InstallResult: Integer;
  UninstallerPath: String;
  InstallDir: String;
  ResultCode: Integer;
  Msg: String;
  WipeData: Boolean;
begin
  Result := True;
  OldVersion := GetInstalledVersion();

  if OldVersion <> '' then
  begin
    { Different version: silent update, keep user data }
    if OldVersion <> '{#AppVersion}' then
    begin
      Result := True;
      Exit;
    end;

    { Same version: ask what to do }
    Msg := '{#AppName} v' + OldVersion + ' is already installed.';

    InstallResult := MsgBox(Msg + #13#10#13#10 +
      'YES  — Reinstall (keep settings and data)' + #13#10 +
      'NO   — Uninstall only' + #13#10 +
      'Cancel — Abort', mbConfirmation, MB_YESNOCANCEL);

    if InstallResult = IDYES then
    begin
      { Optional: wipe Data/ + Config.json for a clean reinstall }
      if MsgBox('Wipe all user data (settings, themes, history) before reinstalling?' + #13#10 +
        'YES — Clean reinstall    NO — Keep data', mbConfirmation, MB_YESNO) = IDYES then
      begin
        InstallDir := GetInstallDir();
        if InstallDir <> '' then
        begin
          DelTree(InstallDir + 'Data', True, True, True);
          { Reset the data-dir redirect so InputBar treats next launch as first-run }
          DeleteFile(InstallDir + 'Path\Config.json');
          { Clear registry backup — otherwise _reg_get_config_dir() would restore
            the old custom path, bypassing the intended first-run state. }
          RegDeleteValue(HKCU, 'Software\Ephraem\InputBar', 'ConfigDirectory');
        end;
      end;
      Result := True;
    end
    else if InstallResult = IDNO then
    begin
      { Ask about data deletion BEFORE running silent uninstaller,
        because /SILENT suppresses MsgBox inside CurUninstallStepChanged. }
      WipeData := MsgBox(
        'Do you want to delete all user data (settings, themes, history) and the installation folder?',
        mbConfirmation, MB_YESNO) = IDYES;

      UninstallerPath := GetUninstallString();
      StringChange(UninstallerPath, '"', '');
      if (UninstallerPath <> '') and FileExists(UninstallerPath) then
      begin
        InstallDir := GetInstallDir();
        Exec(UninstallerPath, '/SILENT', '', SW_SHOW, ewWaitUntilTerminated, ResultCode);
        if WipeData and (InstallDir <> '') then
          DelTree(InstallDir, True, True, True);
        MsgBox('Uninstallation finished.', mbInformation, MB_OK);
      end
      else
        MsgBox('Uninstaller not found. Please uninstall manually from Windows Settings.', mbError, MB_OK);
      Result := False;
    end
    else
      Result := False;
  end;
end;
