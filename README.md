cts200_validator

The CTS200 validator attempts to vlaidate configuration settings of a CTS200 against a 
known set of values stored locally on an sqlite database. The software displays and checks
for the correct IP address as well as the MD5 has of several key files. If succesful a record 
is created in ./records and the operator is notifed. Failures are presented to the operator but not 
otherwise logged. 

Dependencies:
Software relies on python 3.x, several built in libraries and paramiko. 
Software makes use of several standard GNU linux commands and is therfore not
cross platform. 



Use:
Execute main.py to load user interface.  Populate fields and select scan followed by validate. 