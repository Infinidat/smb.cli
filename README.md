Overview
========
This project is the cli interface of the smb cluster.
The project main porpuse is to pars the cli passed by the user.


Development and testing 
=======================
take a python-build-capable windows slave
on this slave create the following folder:
```
c:\Program Files\INFINIDAT\SMB-Cluster
```
in this folder clone the follwoing projects:
```
git clone git@git.infinidat.com:amirr/smb.cli.git
```
```
git clone git@git.infinidat.com:amirr/smb-scripts.git
```
Now build smb.cli using projector


Syncing the code
----------------
As usally you can sync your developemt work using:
```
projector repository sync Administrator <hostname> /cygdrive/c/Program\ Files/Infinidat/smb-cluster/smb.cli
```
