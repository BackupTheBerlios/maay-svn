; -- Maay.iss --

; Revision: $Id: maay.iss 40 2005-09-16 14:42:33Z afayolle $

; TODO: Optionnally install sources to comply with the GPL requirements

[Setup]
AppName=Maay
AppVerName=Maay-0.2.2
DefaultDirName={pf}\Maay
DefaultGroupName=Maay
UninstallDisplayIcon={app}\maay_node.exe
Uninstallable=yes
SolidCompression=yes
LicenseFile=COPYING
; Require 50 MB for the database files. We can tune this later.
ExtraDiskSpaceRequired=50000000
; Win9x is not supported
MinVersion=0,4.0
InfoBeforeFile=ReleaseNotes.txt
InfoAfterFile=README.txt

[Dirs]
Name: "{userdesktop}\Maay Documents";
Name: "{userdesktop}\Maay Documents\downloaded";

[Files]
Source: "dist\*"; DestDir: "{app}"
Source: "maay\data\*.css"; DestDir: "{app}\data"
Source: "maay\data\*.html"; DestDir: "{app}\data"
Source: "maay\data\images\*.gif"; DestDir: "{app}\data\images"
Source: "maay\data\images\*.png"; DestDir: "{app}\data\images"
Source: "maay\data\images\*.ico"; DestDir: "{app}\data\images"
Source: "maay\data\*.js"; DestDir: "{app}\data\"
Source: "maay\sql\mysql.sql"; DestDir: "{app}"
Source: "thirdparty\mysql\data\*"; DestDir: "{app}\mysql\data" ; Flags: recursesubdirs
Source: "thirdparty\mysql\share\*"; DestDir: "{app}\mysql\share" ; Flags: recursesubdirs
Source: "thirdparty\mysql\bin\mysqlshutdown.exe"; DestDir: "{app}\mysql\bin"
Source: "thirdparty\mysql\bin\mysqld-max-nt.exe"; DestDir: "{app}\mysql\bin"
Source: "thirdparty\mysql\bin\mysql.exe"; DestDir: "{app}\mysql\bin"
Source: "thirdparty\antiword\*"; DestDir: "\antiword" ; Flags: recursesubdirs
Source: "thirdparty\pdftohtml-0.36\*"; DestDir: "{app}\pdftohtml" ; Flags: recursesubdirs
Source: "maay\configuration\win32\*.ini"; DestDir: "{app}"
Source: "maay\configuration\win32\Maay.url"; DestDir: "{app}"
Source: "maay\configuration\win32\Maay.url"; DestDir: "{userdesktop}"
Source: "maay\configuration\win32\Maay.url"; DestDir: "{userstartmenu}\Programs\Maay\"
Source: "doc\README.html"; DestDir: "{app}\documentation"
Source: "doc\default.css"; DestDir: "{app}\documentation"
Source: "ChangeLog"; DestDir: "{app}"
Source: "ReleaseNotes.txt"; DestDir: "{app}\"

[Icons]
Name: "{group}\Documentation"; Filename: "{app}\documentation\README.html"; Comment: "Required reading before launching Maay"
Name: "{group}\Node Configuration"; Filename: "{app}\node.ini"; Comment: "Maay node configuration"
Name: "{group}\Release Notes"; Filename: "{app}\ReleaseNotes.txt"; Comment: "Required reading before launching Maay"
Name: "{group}\Uninstall"; Filename: "{app}\unins000.exe"; Comment: "Maay uninstaller"


[Run]
Filename: "{app}\mysql\bin\mysqld-max-nt.exe"; Parameters:"--install MySQL --defaults-file=""{app}\mysql\my-maay.ini"""; StatusMsg: "Registering MySQL as a service"; WorkingDir:"{app}\mysql"; Flags:runhidden
Filename: "NET"; Parameters:"start MySQL"; StatusMsg: "Starting MySQL server"; WorkingDir:"{app}\mysql"; Flags:runhidden
Filename: "{app}\createdb.exe"; StatusMsg: "Installing database"; WorkingDir:"{app}"; Flags:runhidden
Filename: "{app}\updateconfig.exe"; Parameters:"""{userdesktop}"" ""{userdocs}"""; WorkingDir:"{app}"; StatusMsg: "Auto configuration";
Filename: "{app}\maay.exe"; Parameters:"-install -auto"; StatusMsg: "Registering Maay as a service"; WorkingDir:"{app}"; Flags:runhidden
Filename: "NET"; Parameters: "start Maay"; StatusMsg: "Starting Maay node"; Flags:runhidden
;Filename: "{app}\maay_node.exe"; StatusMsg: "Launching maay node"; WorkingDir:"{app}"; Flags:postinstall nowait


[UninstallRun]
Filename: "NET"; Parameters: "stop Maay"; StatusMsg: "Stopping Maay node"; Flags:runhidden
Filename: "NET"; Parameters: "stop MySQL"; StatusMsg: "Stopping MySQL database"; Flags:runhidden
Filename: "{app}\mysql\bin\mysqld-max-nt.exe"; Parameters:"--remove MySQL"; StatusMsg: "Unregistering MySQL as a service"; WorkingDir:"{app}\mysql"; Flags:runhidden
Filename: "{app}\maay.exe"; Parameters:"-remove"; StatusMsg: "Unregistering Maay as a service"; WorkingDir:"{app}\mysql"; Flags:runhidden

[UninstallDelete]
Type: filesandordirs; Name: {app}\mysql\data
Type: files; Name: {app}\node_id
