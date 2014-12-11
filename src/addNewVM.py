#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
        Autore: Amedeo Salvati
        email: amedeo@linux.com
        
        
        Copyright (C) 2014 Amedeo Salvati.  All rights reserved.
        
        This program is free software; you can redistribute it and/or
        modify it under the terms of the GNU General Public License
        as published by the Free Software Foundation; either version 2
        of the License, or (at your option) any later version.
        
        This program is distributed in the hope that it will be useful,
        but WITHOUT ANY WARRANTY; without even the implied warranty of
        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
        GNU General Public License for more details.
        
        You should have received a copy of the GNU General Public License
        along with this program; if not, write to the Free Software
        Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
        
        Amedeo Salvati
        10-12-2014
        Create a new VM from parameter
"""

from ovirtsdk.xml import params
from ovirtsdk.api import API
from time import sleep
import os, sys
from optparse import OptionParser
from string import count
import ConfigParser
import os.path
import re
from subprocess import call

DEBUG = 0

VERSION = "0.0.1"

SHOSTNAME = ''
SPORT = ''
SPROTOCOL = ''
ENGINE_CONN = ''
SUSERNAME = ''
SPASSWORD = ''

EXIT_ON = ''

MB = 1024*1024
GB = 1024*MB
#FIXME: make SLEEPTIME an optional parameter
SLEEPTIME = 10

parser = OptionParser()
usagestr = "usage: %prog [--debug NUMBER] --authfile AUTHFILE --datacenter DATACENTERNAME "
usagestr = usagestr + "--cluster CLUSTERNAME --os OSVERSION --vmname VMNAME "
usagestr = usagestr + "--memory GB"

parser = OptionParser(usage=usagestr, version="%prog Version: " + VERSION)

parser.add_option("-d", "--debug", type="int",dest="DEBUGOPT",
                  help="Print debug information")

parser.add_option("--authfile", type="string",dest="AUTH_FILE", 
                  help="Authorization File name")

parser.add_option("--datacenter", type="string",dest="DATACENTER", 
                  help="Data Center name where VM will be created")

parser.add_option("--cluster", type="string",dest="CLUSTER",
                  help="Cluster name where VM will be reside")

parser.add_option("--os", type="string",dest="OSVERSION",
                  help="Operating system verion, eg rhel_6x64")

parser.add_option("--vmname", type="string",dest="VMNAME",
                  help="VM Name")

parser.add_option("--memory", type="string",dest="MEMORY",
                  help="Memory on GB")

(options, args) = parser.parse_args()

if options.AUTH_FILE == "" or not options.AUTH_FILE:
    parser.error("incorrect number of arguments")
    sys.exit(1)

if options.DATACENTER == "" or not options.DATACENTER:
    parser.error("incorrect number of arguments, no datacenter")
    sys.exit(1)

if options.CLUSTER == "" or not options.CLUSTER:
    parser.error("incorrect number of arguments, no cluster")
    sys.exit(1)

if options.OSVERSION == "" or not options.OSVERSION:
    parser.error("incorrect number of arguments, no os")
    sys.exit(1)

if options.VMNAME == "" or not options.VMNAME:
    parser.error("incorrect number of arguments, no vmname")
    sys.exit(1)

if options.MEMORY == "" or not options.MEMORY:
    parser.error("incorrect number of arguments, no memory")
    sys.exit(1)
elif not str(options.MEMORY).isdigit():
    parser.error("Memory must be digit")
    sys.exit(1)

AUTH_FILE = options.AUTH_FILE
DATACENTER = options.DATACENTER
CLUSTER = options.CLUSTER
OSVERSION = options.OSVERSION
VMNAME = options.VMNAME
MEMORY = int(options.MEMORY)

if options.DEBUGOPT:
    if type( options.DEBUGOPT ) == int:
        DEBUG = int( options.DEBUGOPT )
else:
    DEBUG = 0

if( DEBUG > 0 ):
    print "Authorization filename: '" + AUTH_FILE + "'"
    print "Data Center name: '" + DATACENTER + "'"

# get auth user / pass
try:
    Config = ConfigParser.ConfigParser()
    Config.read(AUTH_FILE)
    if len( Config.sections() ) == 0:
        print "Error: Wrong auth file: " + AUTH_FILE + ", now try to use default /root/DR/.authpass"
        AUTH_FILE = '/root/DR/.authpass'
        Config.read(AUTH_FILE)
        if len( Config.sections() ) == 0:
            print "Error: Wrong auth file: " + AUTH_FILE + ", now exit"
            sys.exit(1)
    if( DEBUG > 0 ):
        print "Try to read Username from " + AUTH_FILE
    SUSERNAME = Config.get("Auth", "Username")
    if( DEBUG > 0 ):
        print "Found Username: " + SUSERNAME
        print "Try to read Password from " + AUTH_FILE
    SPASSWORD = Config.get("Auth", "Password")
    if( DEBUG > 0 ):
        print "Found Password: ***********"
        print "Try to read Hostname from " + AUTH_FILE
    SHOSTNAME = Config.get("Auth", "Hostname")
    if( DEBUG > 0 ):
        print "Found Hostname: " + SHOSTNAME
        print "Try to read protocol from " + AUTH_FILE
    SPROTOCOL = Config.get("Auth", "Protocol")
    if( DEBUG > 0 ):
        print "Found Protocol: " + SPROTOCOL
        print "Try to read Port from " + AUTH_FILE
    SPORT = Config.get("Auth", "Port")
    if( DEBUG > 0 ):
        print "Found Port: " + SPORT
    ENGINE_CONN = SPROTOCOL + '://' + SHOSTNAME + ':' + SPORT
    if( DEBUG > 0 ):
        print "Connection string: " + ENGINE_CONN
except:
    print "Error on reading auth file: " + AUTH_FILE
    sys.exit(1)

def checkDCExist( datacentername ):
    if( DEBUG > 0 ):
        print "Check if DC exist and is up: '" + datacentername + "'"
    dc = api.datacenters.get(name=datacentername)
    if dc == None:
        print "Error: DC " + datacentername + " doesn't exist... Exit"
        sys.exit(1)
    else:
        if( DEBUG > 0 ):
            print "DC " + datacentername + " is present...continue"
    dcstat = dc.get_status().state
    if dcstat != "up":
        print "Error: DC " + datacentername + " is not up... Exit"
        sys.exit(1)

def checkCluster( clustername, datacentername ):
    if( DEBUG > 0 ):
        print ( "Check if Cluster %s is on DC %s" %(clustername, datacentername) )
    dc = api.datacenters.get(name=datacentername)
    c1 = api.clusters.get(name=clustername)
    dctemp = c1.get_data_center()
    
    if dctemp.get_id() == dc.get_id():
        if( DEBUG > 0 ):
            print ( "Cluster %s is on DC %s... Continue" %( clustername, datacentername ) )

def getTemplateFromOS( osversion, datacentername ):
    if( DEBUG > 0 ):
        print ( "Check if there are almost one template for OS %s on DC %s" %( osversion, datacentername ) )
    templatelist = api.templates.list("datacenter=" + datacentername)
    tname = ""
    tnum = 0
    for t in templatelist:
        if( DEBUG > 1 ):
            print ( "Found template %s" %( t.get_name() ) )
        if t.get_os().get_type() == osversion:
            if( DEBUG > 1 ):
                print ( "Template %s is for os %s, now check it's name" %( t.get_name(), osversion ) )
            searchObj = re.search( r'^(\D\w*)-(\d*)-(\D\w*)', str(t.get_name()), re.M|re.I)
            if searchObj != None:
                if tname == "":
                    if( DEBUG > 1 ):
                        print ( "Setting template %s for DC %s" %( t.get_name(), datacentername ) )
                    tname = t.get_name()
                    tnum = searchObj.group(2)
                else:
                    if searchObj.group(2) > tnum:
                        if( DEBUG > 1 ):
                            print ( "Setting template %s for DC %s" %( t.get_name(), datacentername ) )
                        tname = t.get_name()
                        tnum = searchObj.group(2)
        else:
            if( DEBUG > 1 ):
                print ( "Template %s is for os %s and NOT for os %s " %( t.get_name(), t.get_os().get_type(), osversion ) )
    return tname

def checkVMName( vmname ):
    if( DEBUG > 0):
        print ( "Check if vm name %s already exist..." %( vmname ) )
    vm1 = api.vms.get(name = vmname)
    if vm1 != None:
        print ( "Error: VM %s is already present...Exit" %( vmname ) )
        sys.exit(1)

def updateDiskAlias( vmname ):
    if( DEBUG > 0):
        print ( "Updating disk alias for VM %s" %( vmname ) )
    try:
        vm = api.vms.get(name=vmname)
        vmdisk = vm.disks.list()[0]
        if vmdisk.get_status().state == 'ok':
            if( DEBUG > 1):
                print ( "Disk %s is on ok status, continue" %( vmdisk.get_alias() ) )
            dname = str(vmname) + '_Disk1'
            vmdisk.set_alias( dname )
            vmdisk.update()
        else:
            print ( "Error: disk is not on ok status...Exit" )
    except Exception, err:
        print ( "Error on updating disk alias for VM %s" %( vmname ) )
        print Exception, err
        sys.exit(1)

# connect to engine
try:
    if( DEBUG > 0):
        print 'Now try to connect to the engine: ' + ENGINE_CONN
    
    api = None
    api = API(ENGINE_CONN, insecure=True, username=SUSERNAME, password=SPASSWORD)
    if( DEBUG > 0):
        print 'Connection established to the engine: ' + ENGINE_CONN
    
    # verify if datacenter is up
    EXIT_ON = "CHECKDC"
    checkDCExist(DATACENTER)

    # verify if cluster is present and is on datacenter
    EXIT_ON = "CHECKCLUSTER"
    checkCluster(CLUSTER, DATACENTER)

    # get template name from os version
    EXIT_ON = "GETTEMPLATE"
    templatename = getTemplateFromOS(OSVERSION, DATACENTER)
    if templatename == "":
        print ( "Error: Template not found on DC %s for os %s...Exit" %( DATACENTER, OSVERSION ) )
        sys.exit(1)
    if( DEBUG > 0):
        print ( "Using template %s" %( templatename ) )

    # check if vmname already exist
    EXIT_ON = "CHECKVMNAME"
    checkVMName(VMNAME)

    #now try to create a new vm
    try:
        if( DEBUG > 0):
            print ( "Creating VM %s..." %( VMNAME ) )
        sdesc = "Created by addNewVM.py"
        # 70% memory guaranteed
        mguaranteed = int(MEMORY*GB*0.70)
        api.vms.add(params.VM(name=VMNAME, memory=MEMORY*GB, cluster=api.clusters.get(CLUSTER),
                              template=api.templates.get(templatename), description=sdesc,
                              memory_policy=params.MemoryPolicy(guaranteed=mguaranteed),
                              disks=params.Disks(clone=False)
                              ))
        if( DEBUG > 0):
            print ( "VM %s created, waiting to disk allocation (preallocated disk)" %( VMNAME ) )
        #now wait until is down
        vm = api.vms.get(name=VMNAME)
        while ( vm.get_status().state != 'down' ):
            if( DEBUG > 0):
                print ( "VM %s is on state %s, sleeping %s seconds" %( vm.get_name(), vm.get_status().state, str( SLEEPTIME ) ) )
            sleep(SLEEPTIME)
            vm = api.vms.get(name=VMNAME)

    except Exception, err:
        print ( "Error on creating a new vm %s" %( VMNAME ) )
        print Exception, err

    #rename disk alias
    EXIT_ON = "UPDATEDISKALIAS"
    updateDiskAlias( VMNAME )

    #TODO: make cpu a parameter and update VM properties

    #finish
    print ( "Created VM %s from template %s, with memory %sGB" %( VMNAME, templatename, MEMORY ) )

except:
    if EXIT_ON == '':
        print 'Error: Connection failed to server: ' + ENGINE_CONN
    else:
        print 'Error on ' + EXIT_ON
finally:
    if api != None:
        if( DEBUG > 0):
            print 'Closing connection to the engine: ' + ENGINE_CONN
        api.disconnect()
