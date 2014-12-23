#!/bin/bash
#
PYTHON2=`which python2`
VMNAME=FSBOVTESTTMP
#create vm 
$PYTHON2 addNewVM.py --authfile /home/amedeo/DR/.authpass --datacenter IBRIXTMP --cluster IBRIXTMP --os rhel_6x64 --vmname $VMNAME --memory 3 --cpu 2
#configure vm 
$PYTHON2 configureVM.py  --authfile /home/amedeo/DR/.authpass --vmname $VMNAME --ip 10.156.7.162 --netmask 255.255.248.0 --gateway 10.156.0.1 --sshkey /home/amedeo/.ssh/id_rsa

