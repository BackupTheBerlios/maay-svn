; -- Maay.iss --

; Revision: $Id: maay.iss 40 2005-09-16 14:42:33Z afayolle $

[Setup]
AppName=Maay
AppVerName=Maay version 0.1
DefaultDirName={pf}\Maay
DefaultGroupName=Maay
UninstallDisplayIcon={app}\maay_server.exe
Compression=bzip
SolidCompression=yes
LicenseFile=thirdparty\mysql\COPYING.txt
; Require 20 MB for the database files. We can tune this later.
ExtraDiskSpaceRequired=20000000
; Win9x is not supported
MinVersion=0,4.0

[Files]
Source: "dist\*"; DestDir: "{app}"
Source: "maay\data\*.css"; DestDir: "{app}\data"
Source: "maay\data\*.html"; DestDir: "{app}\data"
Source: "maay\data\images\*.gif"; DestDir: "{app}\data\images"
Source: "maay\data\images\*.png"; DestDir: "{app}\data\images"
Source: "maay\data\images\*.ico"; DestDir: "{app}\data\images"
Source: "maay\sql\mysql.sql"; DestDir: "{app}"
Source: "thirdparty\mysql\*"; DestDir: "{app}\mysql" ; Flags: recursesubdirs
Source: "thirdparty\antiword\*"; DestDir: "{app}\antiword" ; Flags: recursesubdirs
Source: "thirdparty\pdftohtml-0.36\*"; DestDir: "{app}\pdftohtml" ; Flags: recursesubdirs

[Icons]
Name: "{group}\Maay Server"; Filename: "{app}\maay_server.exe"; WorkingDir: "{app}"; Comment: "The Maay server component"
Name: "{group}\Maay Indexer"; Filename: "{app}\maay_indexer.exe"; WorkingDir: "{app}"; Comment: "The Maay indexer component"

[Run]
Filename: "{app}\mysql\bin\mysqld-max-nt.exe"; Parameters:"--install MySQL --defaults-file=""{app}\mysql\my-maay.ini"""; StatusMsg: "Registering MySQL as a service"; WorkingDir:"{app}\mysql"; Flags:runhidden
Filename: "NET"; Parameters:"start MySQL"; StatusMsg: "Starting MySQL server"; WorkingDir:"{app}\mysql"; Flags:runhidden
Filename: "{app}\createdb.exe"; StatusMsg: "Installing database"; WorkingDir:"{app}";


[UninstallRun]
Filename: "NET"; Parameters: "stop MySQL"; StatusMsg: "Stopping MySQL database"; Flags:runhidden
Filename: "{app}\mysql\bin\mysqld-max-nt.exe"; Parameters:"--remove MySQL"; StatusMsg: "Unregistering MySQL as a service"; WorkingDir:"{app}\mysql"; Flags:runhidden

