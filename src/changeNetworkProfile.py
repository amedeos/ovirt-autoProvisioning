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
        Change VM network profile
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
import socket
import datetime

DEBUG = 0

VERSION = "0.0.1"

DOMAIN = ''
FQDN = ''

SHOSTNAME = ''
SPORT = ''
SPROTOCOL = ''
ENGINE_CONN = ''
SUSERNAME = ''
SPASSWORD = ''

EXIT_ON = ''

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

parser = OptionParser()
usagestr = "usage: %prog [--debug NUMBER] --authfile AUTHFILE --vmname VMNAME "
usagestr = usagestr + "--netname NETNAME --netprofile NETPROFILE"


parser = OptionParser(usage=usagestr, version="%prog Version: " + VERSION)

parser.add_option("-d", "--debug", type="int",dest="DEBUGOPT",
                  help="Print debug information")

parser.add_option("--authfile", type="string",dest="AUTH_FILE", 
                  help="Authorization File name")

parser.add_option("--vmname", type="string",dest="VMNAME",
                  help="VM Name")

parser.add_option("--netname", type="string",dest="NETNAME",
                  help="Network interfate on VM, ex: eth0")

parser.add_option("--netprofile", type="string",dest="NETPROFILE",
                  help="Network profile for interface, ex: InternetPROD")

(options, args) = parser.parse_args()

if options.AUTH_FILE == "" or not options.AUTH_FILE:
    parser.error("incorrect number of arguments")
    sys.exit(1)

if options.VMNAME == "" or not options.VMNAME:
    parser.error("incorrect number of arguments, no vmname")
    sys.exit(1)

if options.NETNAME == "" or not options.NETNAME:
    parser.error("incorrect number of arguments, no netname")
    sys.exit(1)

if options.NETPROFILE == "" or not options.NETPROFILE:
    parser.error("incorrect number of arguments, no netprofile")
    sys.exit(1)

AUTH_FILE = options.AUTH_FILE
VMNAME = options.VMNAME
NETNAME = options.NETNAME
NETPROFILE = options.NETPROFILE

if options.DEBUGOPT:
    if type( options.DEBUGOPT ) == int:
        DEBUG = int( options.DEBUGOPT )
else:
    DEBUG = 0

strD = ( "Using AUTH_FILE: '%s'" %(AUTH_FILE) )
logDebug(strD)
strD = ( "Using VMNAME: '%s'" %(VMNAME) )
logDebug(strD)
strD = ( "Using NETNAME: '%s'" %(NETNAME) )
logDebug(strD)
strD = ( "Using NETPROFILE: '%s'" %(NETPROFILE) )
logDebug(strD)

# get auth user / pass
try:
    Config = ConfigParser.ConfigParser()
    Config.read(AUTH_FILE)
    if len( Config.sections() ) == 0:
        logDebug( "Error: Wrong auth file: " + AUTH_FILE + ", now try to use default /root/DR/.authpass", 2)
        AUTH_FILE = '/root/DR/.authpass'
        Config.read(AUTH_FILE)
        if len( Config.sections() ) == 0:
            logDebug( "Error: Wrong auth file: " + AUTH_FILE + ", now exit", 2)
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

def checkVM( vmname, netname ):
    try:
        logDebug( "Checking if vm %s exist..." %(vmname) )
        vm = api.vms.get(name=vmname)
        if vm != None:
            logDebug( "VM %s exist...Continue" %(vmname) )
        else:
            logDebug( "Error: VM %s doesn't exist, Exit" %(vmname), 2 )
            sys.exit(1)
        # now check vm interface
        logDebug("Try to found network interface '%s' on VM %s" %(netname, vmname))
        hasInterface = False
        nicsList = vm.nics.list()
        for n in nicsList:
            if n.get_name() == netname:
                hasInterface = True
        if hasInterface == False:
            logDebug("Network interface '%s' not found!...Exit" %(netname), 2)
            raise Exception("Network interface '%s' not present" %(netname))
        else:
            logDebug("Found Network interface '%s'...Continue" %(netname))
    except Exception, err:
        logDebug( "Error on check status for vm %s" %( vmname ), 2 )
        print Exception, err
        sys.exit(1)

def getCluster( vmname ):
    try:
        c2 = ""
        logDebug(  "Getting cluster id for VM %s" %( vmname ) )
        vm = api.vms.get(name=vmname)
        c1 = vm.get_cluster()
        logDebug("Found Cluster ID: %s" %(c1.get_id()))
        c2 = api.clusters.get(id=c1.get_id())
        logDebug("Found Cluster Name: %s" %(c2.get_name()))
    except Exception, err:
        logDebug( "Error on getting the cluster for VM %s" %(vmname) , 2)
        logDebug("Error Description: %s" %(Exception), 2)
        logDebug("Error Code: %s" %(err), 2)
        sys.exit(1)
    return c2

def getNetworkProfile( c1, networkProfile ):
    try:
        np1 = ""
        logDebug("Getting network profile %s for cluster %s" %(networkProfile, c1.get_name()))
        nList = c1.networks.list()
        hasNetwork = False
        for n in nList:
            if n.get_name() == networkProfile:
                hasNetwork = True
                logDebug("Found network profile %s on cluster %s" %(networkProfile, c1.get_name()))
        if hasNetwork:
            np1 = c1.networks.get(name=networkProfile)
        else:
            logDebug("Failed to get network profile %s on cluster %s" %(networkProfile, c1.get_name()), 2)
            raise Exception("Failed to get network profile %s on cluster %s" %(networkProfile, c1.get_name()))
    except Exception, err:
        logDebug( "Error on getting the network profile %s for cluster %s" %(networkProfile, c1.get_name()) , 2)
        logDebug("Error Description: %s" %(Exception), 2)
        logDebug("Error Code: %s" %(err), 2)
        sys.exit(1)
    return np1

def setNetworkProfile( vmname, networkProfile, networkInterface ):
    try:
        logDebug("Setting network for interface %s on VM %s" %(networkInterface, vmname) )
        vm = api.vms.get(name=vmname)
        nList = vm.nics.list()
        for n in nList:
            if n.get_name() == networkInterface:
                n.network = networkProfile
                n.update()
    except Exception, err:
        logDebug( "Error on setting the network profile %s for VM %s" %(networkProfile, vmname) , 2)
        logDebug("Error Description: %s" %(Exception), 2)
        logDebug("Error Code: %s" %(err), 2)
        sys.exit(1)

# connect to engine
try:
    logDebug( 'Now try to connect to the engine: ' + ENGINE_CONN )
    
    api = None
    api = API(ENGINE_CONN, insecure=True, username=SUSERNAME, password=SPASSWORD)
    logDebug( 'Connection established to the engine: ' + ENGINE_CONN )
    
    EXIT_ON = 'CHECKVM'
    checkVM(VMNAME, NETNAME)
    
    EXIT_ON = 'GETCLUSTER'
    c1 = getCluster(VMNAME)
    
    EXIT_ON = 'GETNETWORKPROFILE'
    np1 = getNetworkProfile(c1, NETPROFILE)
    
    EXIT_ON = 'SETNETWORKPROFILE'
    setNetworkProfile(VMNAME, np1, NETNAME)
except:
    if EXIT_ON == '':
        logDebug( 'Error: Connection failed to server: ' + ENGINE_CONN, 2 )
    else:
        logDebug( 'Error on ' + EXIT_ON, 2)
        sys.exit(1)
finally:
    if api != None:
        logDebug( 'Closing connection to the engine: ' + ENGINE_CONN )
        api.disconnect()
