; -- Maay.iss --

; Revision: $Id: maay.iss 40 2005-09-16 14:42:33Z afayolle $

[Setup]
AppName=Maay
AppVerName=Maay snapshot 2005-10-06
DefaultDirName={pf}\Maay
DefaultGroupName=Maay
UninstallDisplayIcon={app}\maay_server.exe
Compression=bzip
SolidCompression=yes
LicenseFile=thirdparty\mysql\COPYING.txt
; Require 50 MB for the database files. We can tune this later.
ExtraDiskSpaceRequired=20000000
; Win9x is not supported
MinVersion=0,4.0
InfoBeforeFile=ReleaseNotes
InfoAfterFile=README.txt

[Files]
Source: "dist\*"; DestDir: "{app}"
Source: "maay\data\*.css"; DestDir: "{app}\data"
Source: "maay\data\*.html"; DestDir: "{app}\data"
Source: "maay\data\images\*.gif"; DestDir: "{app}\data\images"
Source: "maay\data\images\*.png"; DestDir: "{app}\data\images"
Source: "maay\data\images\*.ico"; DestDir: "{app}\data\images"
Source: "maay\sql\mysql.sql"; DestDir: "{app}"
Source: "thirdparty\mysql\*"; DestDir: "{app}\mysql" ; Flags: recursesubdirs
Source: "thirdparty\antiword\*"; DestDir: "c:\antiword" ; Flags: recursesubdirs
Source: "thirdparty\pdftohtml-0.36\*"; DestDir: "{app}\pdftohtml" ; Flags: recursesubdirs
Source: "maay\configuration\*.ini"; DestDir: "{app}"
Source: "README.txt"; DestDir: "{app}"
Source: "ChangeLog"; DestDir: "{app}"
Source: "ReleaseNotes"; DestDir: "{app}"

[Icons]
Name: "{group}\README.txt"; Filename: "{app}\README.txt"; Comment: "Required reading before launching Maay"
Name: "{group}\ReleaseNotes.txt"; Filename: "{app}\ReleaseNotes"; Comment: "Required reading before launching Maay"
Name: "{group}\Maay Server"; Filename: "{app}\maay_server.exe"; WorkingDir: "{app}"; Comment: "The Maay server component"
Name: "{group}\Maay Indexer"; Filename: "{app}\maay_indexer.exe"; WorkingDir: "{app}"; Comment: "The Maay indexer component"
Name: "{group}\webapp.ini"; Filename: "{app}\webapp.ini"; Comment: "Maay server configuration"
Name: "{group}\indexer.ini"; Filename: "{app}\indexer.ini"; Comment: "Maay indexer configuration"


[Run]
Filename: "{app}\mysql\bin\mysqld-max-nt.exe"; Parameters:"--install MySQL --defaults-file=""{app}\mysql\my-maay.ini"""; StatusMsg: "Registering MySQL as a service"; WorkingDir:"{app}\mysql"; Flags:runhidden
Filename: "NET"; Parameters:"start MySQL"; StatusMsg: "Starting MySQL server"; WorkingDir:"{app}\mysql"; Flags:runhidden
Filename: "{app}\createdb.exe"; StatusMsg: "Installing database"; WorkingDir:"{app}";


[UninstallRun]
Filename: "NET"; Parameters: "stop MySQL"; StatusMsg: "Stopping MySQL database"; Flags:runhidden
Filename: "{app}\mysql\bin\mysqld-max-nt.exe"; Parameters:"--remove MySQL"; StatusMsg: "Unregistering MySQL as a service"; WorkingDir:"{app}\mysql"; Flags:runhidden

