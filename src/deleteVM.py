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
        11-02-2015
        Delete VM 
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

parser = OptionParser(usage=usagestr, version="%prog Version: " + VERSION)

parser.add_option("-d", "--debug", type="int",dest="DEBUGOPT",
                  help="Print debug information")

parser.add_option("--authfile", type="string",dest="AUTH_FILE", 
                  help="Authorization File name")

parser.add_option("--vmname", type="string",dest="VMNAME",
                  help="VM Name")

(options, args) = parser.parse_args()

if options.AUTH_FILE == "" or not options.AUTH_FILE:
    parser.error("incorrect number of arguments")
    sys.exit(1)

if options.VMNAME == "" or not options.VMNAME:
    parser.error("incorrect number of arguments, no vmname")
    sys.exit(1)

AUTH_FILE = options.AUTH_FILE
VMNAME = options.VMNAME

if options.DEBUGOPT:
    if type( options.DEBUGOPT ) == int:
        DEBUG = int( options.DEBUGOPT )
else:
    DEBUG = 0

logDebug( "Authorization filename: %s " %(AUTH_FILE) )
logDebug( "VM name: %s " %(VMNAME) )

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

def checkVM( vmname ):
    try:
        logDebug( "Checking if vm %s exist..." %(vmname) )
        vm = api.vms.get(name=vmname)
        if vm != None:
            logDebug( "VM %s exist, now check if is down" %(vmname) )
            if vm.get_status().state == 'down':
                logDebug( "VM %s is down, continue" %(vmname) )
            else:
                logDebug( "Error: VM %s is not down is on status %s, Exit" %(vmname, vm.get_status().state), 2 )
                sys.exit(1)
        else:
            logDebug( "Error: VM %s doesn't exist, Exit" %(vmname), 2 )
            sys.exit(1)
    except Exception, err:
        logDebug( "Error on check status for vm %s" %( vmname ) )
        logDebug( Exception, 2)
        logDebug( err, 2)
        sys.exit(1)

# connect to engine
try:
    logDebug( 'Now try to connect to the engine: ' + ENGINE_CONN )
    
    api = None
    api = API(ENGINE_CONN, insecure=True, username=SUSERNAME, password=SPASSWORD)
    logDebug( 'Connection established to the engine: ' + ENGINE_CONN )
    
    EXIT_ON = 'CHECKVM'
    checkVM(VMNAME)
    
    #now we can delete
    logDebug("Now we can delete the vm %s" %(VMNAME))
    
    EXIT_ON = 'DELETEVM'
    vm = api.vms.get(name=VMNAME)
    vm.delete()
    logDebug("Deleted VM %s" %(VMNAME))
    print ( "Deleted VM %s" %(VMNAME) )
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
