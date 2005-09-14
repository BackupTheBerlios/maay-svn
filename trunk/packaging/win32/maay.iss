; -- Maay.iss --

; Revision: $Id$

[Setup]
AppName=Maay
AppVerName=Maay version 0.1
DefaultDirName={pf}\Maay
DefaultGroupName=Maay
UninstallDisplayIcon={app}\maay_console.exe
Compression=bzip
SolidCompression=yes
LicenseFile=mysql\COPYING.txt
; Require 20 MB for the database files. We can tune this later.
ExtraDiskSpaceRequired=20000000
; Win9x is not supported
MinVersion=0,4.0

[Files]
Source: "python\dist\*"; DestDir: "{app}"
Source: "mysql\*"; DestDir: "{app}\mysql" ; Flags: recursesubdirs
[Icons]
Name: "{group}\Maay"; Filename: "{app}\maay_console.exe"

[Run]
Filename: "{app}\mysql\bin\mysqld-max-nt.exe"; Parameters:"--install MySQL --defaults-file=""{app}\mysql\my-maay.ini"""; StatusMsg: "Registering MySQL as a service"; WorkingDir:"{app}\mysql"
Filename: "NET"; Parameters:"start MySQL"; StatusMsg: "Starting MySQL server"; WorkingDir:"{app}\mysql"

[UninstallRun]
Filename: "NET"; Parameters: "stop MySQL"; StatusMsg: "Stopping MySQL database"
Filename: "{app}\mysql\bin\mysqld-max-nt.exe"; Parameters:"--remove MySQL"; StatusMsg: "Unregistering MySQL as a service"; WorkingDir:"{app}\mysql"

