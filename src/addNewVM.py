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
import datetime

DEBUG = 0

#Variables for max memory and cpu
#FIXME: for cpu at this moment using one core
# to one socket it can't be greater than 16
MAXCPU = 16
MAXMEMORY = 64

VERSION = "0.0.3"

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
usagestr = usagestr + "--cluster CLUSTERNAME --os OSVERSION [--osrelease OSRELEASE] --vmname VMNAME "
usagestr = usagestr + "--memory GB --cpu NUM"

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
                  help="Operating system version, eg rhel_6x64")

parser.add_option("--osrelease", type="int",dest="OSRELEASE",
                  help="Optional operating system release version, eg 5, means level 5 of minor release")

parser.add_option("--vmname", type="string",dest="VMNAME",
                  help="VM Name")

parser.add_option("--memory", type="string",dest="MEMORY",
                  help="Memory on GB")

parser.add_option("--cpu", type="string",dest="CPU",
                  help="Number of CPUs")

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

if options.CPU == "" or not options.CPU:
    parser.error("incorrect number of arguments, no cpu")
    sys.exit(1)
elif not str(options.CPU).isdigit():
    #FIXME: check maximum number of cpu, and value greater than zero
    parser.error("CPUs must be digit")
    sys.exit(1)

AUTH_FILE = options.AUTH_FILE
DATACENTER = options.DATACENTER
CLUSTER = options.CLUSTER
OSVERSION = options.OSVERSION
OSRELEASE = None
VMNAME = options.VMNAME
MEMORY = int(options.MEMORY)
CPU = int(options.CPU)

#now check cpu and memory value
if MEMORY < 1 or MEMORY > MAXMEMORY:
    serr = 'Memory must be a value between 1 and %s' %( MAXMEMORY )
    parser.error(serr)
    sys.exit(1)
if CPU < 1 or CPU > MAXCPU:
    serr = 'CPU must be a value between 1 and %s' %( MAXCPU )
    parser.error(serr)
    sys.exit(1)

if options.DEBUGOPT:
    if type( options.DEBUGOPT ) == int:
        DEBUG = int( options.DEBUGOPT )
else:
    DEBUG = 0

if options.OSRELEASE:
    if type( options.OSRELEASE ) == int:
        OSRELEASE = int( options.OSRELEASE )

def logDebug( strDebug, intDebug=None ):
    global DEBUG
    if intDebug == None:
        intDebug = DEBUG
        if DEBUG > 1:
            intDebug = 1
    if (intDebug > 0) and (intDebug < 2):
        print ("%s DEBUG: %s" %(datetime.datetime.now(), strDebug))
    elif intDebug > 1:
        #always print intDebug messages if are > 1
        print ("%s ERROR: %s" %(datetime.datetime.now(), strDebug))

logDebug( "Authorization filename: %s " %(AUTH_FILE) )
logDebug( "Data Center name: %s " %(DATACENTER) )
logDebug( "Cluster name: %s " %(CLUSTER) )
logDebug( "OS Version: %s " %(OSVERSION) )
logDebug( "VM name: %s " %(VMNAME) )
logDebug( "Memory: %s " %(MEMORY) )
logDebug( "CPU: %s " %(CPU) )
logDebug( "OS Release: %s" %(OSRELEASE))

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
    logDebug( "Try to read Username from " + AUTH_FILE )
    SUSERNAME = Config.get("Auth", "Username")
    logDebug( "Found Username: " + SUSERNAME )
    logDebug( "Try to read Password from " + AUTH_FILE )
    SPASSWORD = Config.get("Auth", "Password")
    logDebug( "Found Password: ***********" )
    logDebug( "Try to read Hostname from " + AUTH_FILE )
    SHOSTNAME = Config.get("Auth", "Hostname")
    logDebug( "Found Hostname: " + SHOSTNAME )
    logDebug( "Try to read protocol from " + AUTH_FILE )
    SPROTOCOL = Config.get("Auth", "Protocol")
    logDebug( "Found Protocol: " + SPROTOCOL )
    logDebug( "Try to read Port from " + AUTH_FILE )
    SPORT = Config.get("Auth", "Port")
    logDebug( "Found Port: " + SPORT )
    ENGINE_CONN = SPROTOCOL + '://' + SHOSTNAME + ':' + SPORT
    logDebug( "Connection string: " + ENGINE_CONN )
except:
    logDebug( "Error on reading auth file: " + AUTH_FILE, 2)
    sys.exit(1)

def checkDCExist( datacentername ):
    logDebug( "Check if DC exist and is up: '" + datacentername + "'" )
    dc = api.datacenters.get(name=datacentername)
    if dc == None:
        logDebug( "Error: DC " + datacentername + " doesn't exist... Exit", 2)
        sys.exit(1)
    else:
        logDebug( "DC " + datacentername + " is present...continue" )
    dcstat = dc.get_status().state
    if dcstat != "up":
        logDebug( "Error: DC " + datacentername + " is not up... Exit", 2)
        sys.exit(1)

def checkCluster( clustername, datacentername ):
    logDebug( "Check if Cluster %s is on DC %s" %(clustername, datacentername) )
    dc = api.datacenters.get(name=datacentername)
    c1 = api.clusters.get(name=clustername)
    dctemp = c1.get_data_center()
    
    if dctemp.get_id() == dc.get_id():
        logDebug( "Cluster %s is on DC %s... Continue" %( clustername, datacentername ) )

def getTemplateFromOS( osversion, datacentername, osrelease=None ):
    logDebug( "Check if there are almost one template for OS %s on DC %s" %( osversion, datacentername ) )
    if osrelease != None:
        logDebug("and try to finding template with release number %s" %(osrelease))
    templatelist = api.templates.list("datacenter=" + datacentername)
    tname = ""
    tnum = 0
    for t in templatelist:
        logDebug( "Found template %s" %( t.get_name() ) )
        if t.get_os().get_type() == osversion:
            logDebug( "Template %s is for os %s, now check it's name" %( t.get_name(), osversion ) )
            if osrelease == None:
                searchObj = re.search( r'^(\D\w*)-(\d*)-(\D\w*)', str(t.get_name()), re.M|re.I)
            else:
                searchObj = re.search( r'^(\D\w*' + str(osrelease) + ')-(\d*)-(\D\w*)', str(t.get_name()), re.M|re.I)
            if searchObj != None:
                if tname == "":
                    logDebug( "Setting template %s for DC %s" %( t.get_name(), datacentername ) )
                    tname = t.get_name()
                    tnum = searchObj.group(2)
                else:
                    if searchObj.group(2) > tnum:
                        logDebug( "Setting template %s for DC %s" %( t.get_name(), datacentername ) )
                        tname = t.get_name()
                        tnum = searchObj.group(2)
        else:
            logDebug( "Template %s is for os %s and NOT for os %s " %( t.get_name(), t.get_os().get_type(), osversion ) )
    return tname

def checkVMName( vmname ):
    logDebug( "Check if vm name %s already exist..." %( vmname ) )
    vm1 = api.vms.get(name = vmname)
    if vm1 != None:
        logDebug( "Error: VM %s is already present...Exit" %( vmname ), 2)
        sys.exit(1)

def updateDiskAlias( vmname ):
    logDebug( "Updating disk alias for VM %s" %( vmname ) )
    try:
        vm = api.vms.get(name=vmname)
        vmdisk = vm.disks.list()[0]
        if vmdisk.get_status().state == 'ok':
            logDebug( "Disk %s is on ok status, continue" %( vmdisk.get_alias() ) )
            dname = str(vmname) + '_Disk1'
            vmdisk.set_alias( dname )
            vmdisk.update()
        else:
            logDebug( "Error: disk is not on ok status...Exit", 2 )
    except Exception, err:
        logDebug( "Error on updating disk alias for VM %s" %( vmname ), 2 )
        logDebug( Exception, 2)
        logDebug( err, 2)
        sys.exit(1)

def updateCpuNumber( vmname, cpunum ):
    logDebug( "Updating CPU number for VM %s setting total CPU to: %s" %( vmname, cpunum ) )
    #check if is down
    try:
        vm = api.vms.get(name=vmname)
        if vm.get_status().state == 'down':
            c1 = vm.get_cpu()
            c1.set_topology(params.CpuTopology(cores=1,sockets=cpunum))
            vm.set_cpu(c1)
            vm.update()
    except Exception, err:
        logDebug( "Error on updating CPU for VM %s" %( vmname ), 2 )
        logDebug( Exception, 2)
        logDebug( err, 2)
        sys.exit(1)

# connect to engine
try:
    logDebug( 'Now try to connect to the engine: ' + ENGINE_CONN )
    
    api = None
    api = API(ENGINE_CONN, insecure=True, username=SUSERNAME, password=SPASSWORD)
    logDebug( 'Connection established to the engine: ' + ENGINE_CONN )
    
    # verify if datacenter is up
    EXIT_ON = "CHECKDC"
    checkDCExist(DATACENTER)

    # verify if cluster is present and is on datacenter
    EXIT_ON = "CHECKCLUSTER"
    checkCluster(CLUSTER, DATACENTER)

    # get template name from os version
    EXIT_ON = "GETTEMPLATE"
    templatename = getTemplateFromOS(OSVERSION, DATACENTER, OSRELEASE)
    if templatename == "":
        if OSRELEASE == None:
            logDebug( "Error: Template not found on DC %s for os %s...Exit" %( DATACENTER, OSVERSION ), 2 )
        else:
            logDebug( "Error: Template not found on DC %s for os %s and release %s...Exit" %( DATACENTER, OSVERSION, OSRELEASE ), 2 )
        sys.exit(1)
    logDebug( "Using template %s" %( templatename ) )
    
    # check if vmname already exist
    EXIT_ON = "CHECKVMNAME"
    checkVMName(VMNAME)

    #now try to create a new vm
    try:
        logDebug( "Creating VM %s..." %( VMNAME ) )
        sdesc = "Created by addNewVM.py"
        # 70% memory guaranteed
        mguaranteed = int(MEMORY*GB*0.70)
        api.vms.add(params.VM(name=VMNAME, memory=MEMORY*GB, cluster=api.clusters.get(CLUSTER),
                              template=api.templates.get(templatename), description=sdesc,
                              memory_policy=params.MemoryPolicy(guaranteed=mguaranteed),
                              disks=params.Disks(clone=False)
                              ))
        logDebug( "VM %s created, waiting to disk allocation (preallocated disk)" %( VMNAME ) )
        #now wait until is down
        vm = api.vms.get(name=VMNAME)
        while ( vm.get_status().state != 'down' ):
            logDebug( "VM %s is on state %s, sleeping %s seconds" %( vm.get_name(), vm.get_status().state, str( SLEEPTIME ) ) )
            sleep(SLEEPTIME)
            vm = api.vms.get(name=VMNAME)

    except Exception, err:
        logDebug( "Error on creating a new vm %s" %( VMNAME ), 2 )
        logDebug( Exception, 2)
        logDebug( err, 2)

    #rename disk alias
    EXIT_ON = "UPDATEDISKALIAS"
    updateDiskAlias( VMNAME )

    #update cpu number
    EXIT_ON = "UPDATECPU"
    updateCpuNumber(VMNAME, CPU)

    #finish
    print ( "Created VM %s from template %s, with %sGB memory and %s CPU" %( VMNAME, templatename, MEMORY, CPU ) )

except:
    if EXIT_ON == '':
        logDebug( 'Error: Connection failed to server: ' + ENGINE_CONN, 2)
    else:
        logDebug( 'Error on ' + EXIT_ON, 2)
finally:
    if api != None:
        logDebug( 'Closing connection to the engine: ' + ENGINE_CONN )
        api.disconnect()
