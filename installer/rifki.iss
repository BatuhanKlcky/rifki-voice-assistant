; RIFKI Windows Setup — OmniRoute bilgilendirme + .env formu
#define MyAppName "RIFKI"
#define MyAppVersion "2.1.0"
#define MyAppPublisher "RIFKI"
#define MyAppExeName "RIFKI.exe"
; Resmi Windows kurulum: OmniRoute.Setup.3.8.51.exe (~555 MB)
#define OmniDownloadURL "https://github.com/diegosouzapw/OmniRoute/releases/tag/v3.8.51"
#define OmniSetupURL "https://github.com/diegosouzapw/OmniRoute/releases/download/v3.8.51/OmniRoute.Setup.3.8.51.exe"


[Setup]
AppId={{8F3C2A91-6B4E-4D1A-9C7F-2A91B4E6D1A9}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\RIFKI
DefaultGroupName=RIFKI
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=RIFKI-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
SetupLogging=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
VersionInfoVersion=2.1.0.0
VersionInfoProductName=RIFKI

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Masaüstü kısayolu oluştur"; GroupDescription: "Ek görevler:"; Flags: unchecked

[Files]
; Ana uygulama (PyInstaller onedir)
Source: "..\dist\RIFKI\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; OmniRoute payload (varsa)
Source: "payload\omniroute\*"; DestDir: "{app}\omniroute"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
; Kurulum yardımcıları (kurulum + gecici cikarma)
Source: "scripts\write_env.ps1"; DestDir: "{app}\installer"; Flags: ignoreversion
Source: "scripts\check_omniroute.ps1"; DestDir: "{app}\installer"; Flags: ignoreversion
Source: "scripts\start_omniroute.ps1"; DestDir: "{app}\installer"; Flags: ignoreversion
Source: "pages\omniroute_info.txt"; DestDir: "{app}\installer"; Flags: ignoreversion
; Wizard sirasinda {src} yok — gecici klasore cikar
Source: "scripts\check_omniroute.ps1"; Flags: dontcopy
Source: "pages\omniroute_info.txt"; Flags: dontcopy

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\RIFKI kaldır"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\installer\start_omniroute.ps1"" -OmniDir ""{app}\omniroute"""; \
  StatusMsg: "OmniRoute başlatılıyor (varsa)..."; Flags: runhidden waituntilterminated skipifdoesntexist
Filename: "{app}\{#MyAppExeName}"; Description: "RIFKI'yi şimdi aç"; Flags: nowait postinstall skipifsilent

[Code]
var
  InfoPage: TOutputMsgMemoWizardPage;
  StatusPage: TWizardPage;
  StatusLabel: TNewStaticText;
  CheckBtn: TNewButton;
  OpenLinkBtn: TNewButton;
  SettingsPage: TInputQueryWizardPage;
  OmniOk: Boolean;

function HasOmniPayload: Boolean;
begin
  Result := DirExists(ExpandConstant('{src}\payload\omniroute')) and
    (not FileExists(ExpandConstant('{src}\payload\omniroute\README.md')) or
     FileExists(ExpandConstant('{src}\payload\omniroute\OmniRoute.exe')) or
     FileExists(ExpandConstant('{src}\payload\omniroute\omniroute.exe')));
  { Daha genis: herhangi bir exe var mi }
  if not Result then
    Result := FileExists(ExpandConstant('{src}\payload\omniroute\OmniRoute.exe'));
end;

function CheckOmniRunning: Boolean;
var
  ResultCode: Integer;
  ScriptPath: String;
begin
  // Setup.exe runtime: scripts come from dontcopy into tmp
  Result := False;
  ExtractTemporaryFile('check_omniroute.ps1');
  ScriptPath := ExpandConstant('{tmp}\check_omniroute.ps1');
  if FileExists(ScriptPath) then
  begin
    if Exec('powershell.exe',
      '-NoProfile -ExecutionPolicy Bypass -File "' + ScriptPath + '"',
      '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
      Result := (ResultCode = 0);
  end;
end;




procedure RefreshStatus;
begin
  OmniOk := CheckOmniRunning;
  if OmniOk then
    StatusLabel.Caption :=
      'Durum: OmniRoute CALISIYOR (127.0.0.1:20128).'#13#10 +
      '«Sonraki» ile devam edin.'
  else
    StatusLabel.Caption :=
      'Durum: OmniRoute KAPALI (127.0.0.1:20128).'#13#10#13#10 +
      'OmniRoute penceresi acik olsa bile port 20128 dinlemiyorsa'#13#10 +
      'burada KAPALI gorunur. OmniRoute''u tamamen acip bekleyin,'#13#10 +
      'sonra «Tekrar kontrol et»e basin.'#13#10#13#10 +
      'Yoksa «OmniRoute indir (v3.8.51)» ile kurun.'#13#10 +
      'RIFKI kurulumu yine de «Sonraki» ile tamamlanabilir.';
end;



procedure CheckBtnClick(Sender: TObject);
begin
  RefreshStatus;
end;

procedure OpenLinkBtnClick(Sender: TObject);
var
  Err: Integer;
begin
  { Once Windows Setup exe indir; sayfa yedek }
  if not ShellExec('open', '{#OmniSetupURL}', '', '', SW_SHOWNORMAL, ewNoWait, Err) then
    ShellExec('open', '{#OmniDownloadURL}', '', '', SW_SHOWNORMAL, ewNoWait, Err);
end;


procedure InitializeWizard;
begin
  // OmniRoute bilgi: metin dogrudan scriptte (encoding bozuklugu yok)
  InfoPage := CreateOutputMsgMemoPage(wpWelcome,
    'OmniRoute nedir?',
    'RIFKI yapay zeka icin OmniRoute kullanir',
    'Lutfen okuyun, sonra Sonraki''ye basin.',
    '');
  InfoPage.RichEditViewer.RTFText :=
    'OmniRoute nedir?'#13#10#13#10 +
    'RIFKI''nin beyni OmniRoute adli yerel bir yapay zeka koprusudur.'#13#10 +
    'Bilgisayarinizda 127.0.0.1:20128 adresinde calisir. RIFKI komutlari'#13#10 +
    'anlamak ve yanit uretmek icin bu servise baglanir.'#13#10#13#10 +
    'Neden gerekli?'#13#10 +
    '- Sesli / mobil komutlar OmniRoute uzerinden modele gider.'#13#10 +
    '- OmniRoute kapalysa RIFKI acilir ama cevap veremez.'#13#10#13#10 +
    'Nereden indirilir? (Windows)'#13#10 +
    'https://github.com/diegosouzapw/OmniRoute/releases/tag/v3.8.51'#13#10 +
    'Dosya: OmniRoute.Setup.3.8.51.exe'#13#10#13#10 +
    'Kurulumda ne yapacaksiniz?'#13#10 +
    '1) OmniRoute''un calisip calismadigi kontrol edilir.'#13#10 +
    '2) Yoksa "OmniRoute indir" ile v3.8.51 Setup indirilir; kurup acin.'#13#10 +
    '3) API anahtarinizi forma yapistirirsiniz - .env otomatik yazilir.'#13#10 +
    '   Elle TXT duzenlemeniz gerekmez.'#13#10#13#10 +
    'Varsayilan model: antigravity/gemini-2.5-flash';

  { --- Durum / kontrol --- }
  StatusPage := CreateCustomPage(InfoPage.ID,
    'OmniRoute durumu',
    'Yerel servis kontrolü (port 20128)');
  StatusLabel := TNewStaticText.Create(StatusPage);
  StatusLabel.Parent := StatusPage.Surface;
  StatusLabel.Left := ScaleX(0);
  StatusLabel.Top := ScaleY(0);
  StatusLabel.Width := StatusPage.SurfaceWidth;
  StatusLabel.Height := ScaleY(140);
  StatusLabel.WordWrap := True;
  StatusLabel.AutoSize := False;

  CheckBtn := TNewButton.Create(StatusPage);
  CheckBtn.Parent := StatusPage.Surface;
  CheckBtn.Left := ScaleX(0);
  CheckBtn.Top := ScaleY(150);
  CheckBtn.Width := ScaleX(160);
  CheckBtn.Caption := 'Tekrar kontrol et';
  CheckBtn.OnClick := @CheckBtnClick;

  OpenLinkBtn := TNewButton.Create(StatusPage);
  OpenLinkBtn.Parent := StatusPage.Surface;
  OpenLinkBtn.Left := ScaleX(170);
  OpenLinkBtn.Top := ScaleY(150);
  OpenLinkBtn.Width := ScaleX(180);
  OpenLinkBtn.Caption := 'OmniRoute indir (v3.8.51)';
  OpenLinkBtn.OnClick := @OpenLinkBtnClick;


  RefreshStatus;

  { --- API anahtarı / model --- }
  SettingsPage := CreateInputQueryPage(StatusPage.ID,
    'Yapay zekâ ayarları',
    'OmniRoute API anahtarı',
    'Anahtarı yapıştırın. .env dosyası kurulumda otomatik yazılır (TXT düzenlemeniz gerekmez).');
  SettingsPage.Add('OMNIROUTE_API_KEY:', False);
  SettingsPage.Add('Model (varsayılan önerilir):', False);
  SettingsPage.Values[1] := 'antigravity/gemini-2.5-flash';
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = SettingsPage.ID then
  begin
    if Trim(SettingsPage.Values[0]) = '' then
    begin
      MsgBox('OmniRoute API anahtarı boş olamaz. OmniRoute panelinizdeki anahtarı yapıştırın.',
        mbError, MB_OK);
      Result := False;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  Key, Model, Ps: String;
begin
  if CurStep = ssPostInstall then
  begin
    Key := SettingsPage.Values[0];
    Model := SettingsPage.Values[1];
    if Trim(Model) = '' then
      Model := 'antigravity/gemini-2.5-flash';
    Ps :=
      '-NoProfile -ExecutionPolicy Bypass -File "' + ExpandConstant('{app}\installer\write_env.ps1') + '"' +
      ' -AppDir "' + ExpandConstant('{app}') + '"' +
      ' -ApiKey "' + Key + '"' +
      ' -Model "' + Model + '"';
    Exec('powershell.exe', Ps, '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;
