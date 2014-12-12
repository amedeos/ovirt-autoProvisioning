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
import socket

DEBUG = 0

VERSION = "0.0.1"

SHOSTNAME = ''
SPORT = ''
SPROTOCOL = ''
ENGINE_CONN = ''
SUSERNAME = ''
SPASSWORD = ''

EXIT_ON = ''

#FIXME: make SLEEPTIME an optional parameter
SLEEPTIME = 10

parser = OptionParser()
usagestr = "usage: %prog [--debug NUMBER] --authfile AUTHFILE --vmname VMNAME "
usagestr = usagestr + "--ip IPADDRESS --netmask NETMASK"

parser = OptionParser(usage=usagestr, version="%prog Version: " + VERSION)

parser.add_option("-d", "--debug", type="int",dest="DEBUGOPT",
                  help="Print debug information")

parser.add_option("--authfile", type="string",dest="AUTH_FILE", 
                  help="Authorization File name")

parser.add_option("--vmname", type="string",dest="VMNAME",
                  help="VM Name")

parser.add_option("--ip", type="string",dest="IP",
                  help="IP Address")

parser.add_option("--netmask", type="string",dest="NETMASK",
                  help="Netmask")

(options, args) = parser.parse_args()

if options.AUTH_FILE == "" or not options.AUTH_FILE:
    parser.error("incorrect number of arguments")
    sys.exit(1)

if options.VMNAME == "" or not options.VMNAME:
    parser.error("incorrect number of arguments, no vmname")
    sys.exit(1)

if options.IP == "" or not options.IP:
    parser.error("incorrect number of arguments, no IP address")
    sys.exit(1)

if options.NETMASK == "" or not options.NETMASK:
    parser.error("incorrect number of arguments, no netmask")
    sys.exit(1)

AUTH_FILE = options.AUTH_FILE
VMNAME = options.VMNAME
IP = options.IP
NETMASK = options.NETMASK
try:
    socket.inet_aton(IP)
    socket.inet_aton(NETMASK)
except socket.error:
    parser.error("IP / Netmask illegal")
    sys.exit(1)

if options.DEBUGOPT:
    if type( options.DEBUGOPT ) == int:
        DEBUG = int( options.DEBUGOPT )
else:
    DEBUG = 0

if( DEBUG > 0 ):
    print ( "Authorization filename: %s " %(AUTH_FILE) )
    print ( "VM name: %s " %(VMNAME) )
    print ( "IP Address: %s " %(IP) )

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

def checkVM( vmname ):
    try:
        if( DEBUG > 0):
            print ( "Checking if vm %s exist..." %(vmname) )
        vm = api.vms.get(name=vmname)
        if vm != None:
            if( DEBUG > 0):
                print ( "VM %s exist, now check if is down" %(vmname) )
            if vm.get_status().state == 'down':
                if( DEBUG > 0):
                    print ( "VM %s is down, continue" %(vmname) )
            else:
                print ( "Error: VM %s is not down is on status %s, Exit" %(vmname, vm.get_status().state) )
                sys.exit(1)
        else:
            print ( "Error: VM %s doesn't exist, Exit" %(vmname) )
            sys.exit(1)
    except Exception, err:
        print ( "Error on check status for vm %s" %( vmname ) )
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

    #check if vm exist and is down
    EXIT_ON = 'CHECKVM'
    checkVM( VMNAME )
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