; -- Maay.iss --

; Revision: $Id: maay.iss 40 2005-09-16 14:42:33Z afayolle $

; TODO: Optionnally install sources to comply with the GPL requirements

[Setup]
AppName=Maay
AppVerName=Maay snapshot 2005-10-07
DefaultDirName={pf}\Maay
DefaultGroupName=Maay
UninstallDisplayIcon={app}\maay_node.exe
Compression=bzip
SolidCompression=yes
LicenseFile=thirdparty\mysql\COPYING.txt
; Require 50 MB for the database files. We can tune this later.
ExtraDiskSpaceRequired=50000000
; Win9x is not supported
MinVersion=0,4.0
InfoBeforeFile=ReleaseNotes
InfoAfterFile=README.txt

[Dirs]
Name: "{userdesktop}\Maay Documents";

[Files]
Source: "dist\*"; DestDir: "{app}"
Source: "maay\data\*.css"; DestDir: "{app}\data"
Source: "maay\data\*.html"; DestDir: "{app}\data"
Source: "maay\data\images\*.gif"; DestDir: "{app}\data\images"
Source: "maay\data\images\*.png"; DestDir: "{app}\data\images"
Source: "maay\data\images\*.ico"; DestDir: "{app}\data\images"
Source: "maay\sql\mysql.sql"; DestDir: "{app}"
Source: "thirdparty\mysql\data\*"; DestDir: "{app}\mysql\data" ; Flags: recursesubdirs
Source: "thirdparty\mysql\share\*"; DestDir: "{app}\mysql\share" ; Flags: recursesubdirs
Source: "thirdparty\mysql\bin\mysqlshutdown.exe"; DestDir: "{app}\mysql\bin"
Source: "thirdparty\mysql\bin\mysqld-max-nt.exe"; DestDir: "{app}\mysql\bin"
Source: "thirdparty\mysql\bin\mysql.exe"; DestDir: "{app}\mysql\bin"
Source: "thirdparty\antiword\*"; DestDir: "c:\antiword" ; Flags: recursesubdirs
Source: "thirdparty\pdftohtml-0.36\*"; DestDir: "{app}\pdftohtml" ; Flags: recursesubdirs
Source: "maay\configuration\win32\*.ini"; DestDir: "{app}"
Source: "README.txt"; DestDir: "{app}"
Source: "ChangeLog"; DestDir: "{app}"
Source: "ReleaseNotes"; DestDir: "{app}"

[Icons]
Name: "{group}\README.txt"; Filename: "{app}\README.txt"; Comment: "Required reading before launching Maay"
Name: "{group}\ReleaseNotes.txt"; Filename: "{app}\ReleaseNotes"; Comment: "Required reading before launching Maay"
Name: "{group}\Maay Node"; Filename: "{app}\maay_node.exe"; WorkingDir: "{app}"; Comment: "The Maay node component"
Name: "{group}\Maay Indexer"; Filename: "{app}\maay_indexer.exe"; WorkingDir: "{app}"; Comment: "The Maay indexer component"
Name: "{group}\node.ini"; Filename: "{app}\node.ini"; Comment: "Maay node configuration"
Name: "{group}\indexer.ini"; Filename: "{app}\indexer.ini"; Comment: "Maay indexer configuration"
Name: "{group}\image.ini"; Filename: "{app}\image.ini"; Comment: "Maay indexer configuration"


[Run]
Filename: "{app}\mysql\bin\mysqld-max-nt.exe"; Parameters:"--install MySQL --defaults-file=""{app}\mysql\my-maay.ini"""; StatusMsg: "Registering MySQL as a service"; WorkingDir:"{app}\mysql"; Flags:runhidden
Filename: "NET"; Parameters:"start MySQL"; StatusMsg: "Starting MySQL server"; WorkingDir:"{app}\mysql"; Flags:runhidden
Filename: "{app}\createdb.exe"; StatusMsg: "Installing database"; WorkingDir:"{app}"; Flags:runhidden
Filename: "{app}\updateconfig.exe"; Parameters:"""{userdesktop}"" ""{userdocs}"""; WorkingDir:"{app}"; Flags:runhidden
Filename: "{app}\maay.exe"; Parameters:"-install"; StatusMsg: "Registering Maay as a service"; WorkingDir:"{app}"; Flags:runhidden
Filename: "NET"; Parameters: "start Maay"; StatusMsg: "Starting Maay node"; Flags:runhidden
;Filename: "{app}\maay_node.exe"; StatusMsg: "Launching maay node"; WorkingDir:"{app}"; Flags:postinstall nowait


[UninstallRun]
Filename: "NET"; Parameters: "stop MySQL"; StatusMsg: "Stopping MySQL database"; Flags:runhidden
Filename: "NET"; Parameters: "stop Maay"; StatusMsg: "Stopping Maay node"; Flags:runhidden
Filename: "{app}\mysql\bin\mysqld-max-nt.exe"; Parameters:"--remove MySQL"; StatusMsg: "Unregistering MySQL as a service"; WorkingDir:"{app}\mysql"; Flags:runhidden
Filename: "{app}\maay.exe"; Parameters:"-remove"; StatusMsg: "Unregistering Maay as a service"; WorkingDir:"{app}\mysql"; Flags:runhidden

[UninstallDelete]
Type: filesandordirs; Name: {app}\mysql\
Type: files; Name: {app}\node_id
