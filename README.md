Overview
========
smb.cli Purpose is to give single interface of managing SMB MS failvoer cluster with InfiniBox.
Current capabilities include:
- Managing MS and InfiniBox config.
- Creating Clustered filesystems which reside on InfiniBox.
- Creating SMBv3 file shares on the MS cluster
- Setting Quotas 

Installation
============
Go to https://github.com/Infinidat/smb.cli/releases
Download the latest msi package
Verify msi using the md5sum.
You can get help for the setup using the the pdf docs attached to the release
Install using the grafical interface at default path location.
(C:\Program Files\Infinidat\smb.cli)

Development
===========

If you'd like to develop and build from scratch this package you have 2 options:

(Option 1 ) Developing on top of the MSI installation ( less recomanded ) 
-------------------------------------------------------------------------
In this option install the MSI package.
Perform the changes you'd like in the code.
Override your new code with the code folder here:
C:\Program Files\Infinidat\smb.cli\src\smb\cli\
The "new" version now contains your fixes ( assuming no new python dependencies where added )

(Option 2) Create you own development enviroment
------------------------------------------------

1. Get a windows 2016
2. install python and make sure you can succesfuly run infi.projector module 
```
https://github.com/Infinidat/infi.projector 
```
3. Clone the smb.cli code
```
git clone <add repo name here>
```
4. Perform the changes you'd like
5. Build a new version and copy or pack
```
projector devenv build --use-isolated-python 
```
6. If you'd like to install the code on another host pack the code using:
```
projector devenv pack
```
MSI will be presented in <project_root/parts>


General Notes and Limitations
=============================
Paths in this projects are *absolute paths* !
Powershell is used in this project and takes only Absolut path for most of it's commands / scripts
Therefore make sure, project is installed at the right location.
Host Power Tools ( HPT ) should also be installed at it's default location.

