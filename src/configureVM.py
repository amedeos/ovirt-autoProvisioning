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
import datetime

DEBUG = 0

VERSION = "0.0.2"

DOMAIN = ''
FQDN = ''

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
usagestr = usagestr + "--ip IPADDRESS --netmask NETMASK --gateway GATEWAY "
usagestr = usagestr + "--sshkey SSHPRIVATEKEY"

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

parser.add_option("--gateway", type="string",dest="GATEWAY",
                  help="GATEWAY")

parser.add_option("--sshkey", type="string",dest="SSHKEY",
                  help="SSH private key to use, alse public key must be on same path")

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

if options.GATEWAY == "" or not options.GATEWAY:
    parser.error("incorrect number of arguments, no gateway")
    sys.exit(1)

if options.SSHKEY == "" or not options.SSHKEY:
    parser.error("incorrect number of arguments, no ssh private key")
    sys.exit(1)

AUTH_FILE = options.AUTH_FILE
VMNAME = options.VMNAME
IPADDR = options.IP
NETMASK = options.NETMASK
#TODO: automatic calculation of ip address of gateway
GATEWAY = options.GATEWAY
try:
    socket.inet_aton(IPADDR)
    socket.inet_aton(NETMASK)
    socket.inet_aton(GATEWAY)
except socket.error:
    parser.error("IP / Netmask or gateway illegal")
    sys.exit(1)

SSHKEY = options.SSHKEY

if options.DEBUGOPT:
    if type( options.DEBUGOPT ) == int:
        DEBUG = int( options.DEBUGOPT )
else:
    DEBUG = 0

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
logDebug( "VM name: %s " %(VMNAME) )
logDebug( "IP Address: %s " %(IPADDR) )
logDebug( "Netmask: %s " %(NETMASK) )
logDebug( "Gateway: %s " %(GATEWAY) )
logDebug( "SSH private key: %s " %(SSHKEY) )

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

    DOMAIN = Config.get("Cloud-init", "Domain")
    if( DOMAIN == "" ):
        DOMAIN = "example.com"
    logDebug( "Domain name used is: %s" %(DOMAIN) )
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
        #now check vm os version
        osVersion = vm.get_os().get_type()
        if (osVersion == "rhel_6x64" or osVersion == "rhel_6" or osVersion == "rhel_7x64"):
            logDebug( "VM %s has OS version %s which support cloud-init, continue..." %( vmname, osVersion ) )
        else:
            logDebug( "Error: VM %s has OS version %s which doesn't support cloud-init, Exit" %( vmname, osVersion ), 2 )
            sys.exit(1)
    except Exception, err:
        logDebug( "Error on check status for vm %s" %( vmname ) )
        logDebug( Exception, 2)
        logDebug( err, 2)
        sys.exit(1)

def checkSshKey( sshkey ):
    try:
        logDebug( "Try to read private key %s" %(sshkey) )
        open( sshkey ).read()
        sshkeypub = '%s.pub' %(sshkey)
        logDebug( "Try to read public key %s" %(sshkeypub) )
        open( sshkeypub ).read()
        logDebug( "Either private and public keys are readable, continue" )
        return open( sshkeypub ).read()
    except:
        logDebug( "Error on reading ssh private/pub key %s" %( sshkey ), 2 )
        sys.exit(1)

def buildYamlFile():
    str1 = "write_files:\n-   content: |\n"
    str1 = str1 + "        Configured by configureVM.py on " + datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S") + "\n"
    str1 = str1 + "    path: /etc/motd\n\n"
    str1 = str1 + "runcmd:\n"
    str1 = ("%s- [ sh, -c, \"/bin/hostname %s\" ]\n" %(str1, FQDN))
    str1 = str1 + "- [ sh, -c, \"/root/bootstrap-standard.sh\" ]\n"
    str1 = str1 + "- [ sh, -c, \"/root/setup-ipaclient.sh\" ]\n"
    return str1

# connect to engine
try:
    logDebug( 'Now try to connect to the engine: ' + ENGINE_CONN )
    
    api = None
    api = API(ENGINE_CONN, insecure=True, username=SUSERNAME, password=SPASSWORD)
    logDebug( 'Connection established to the engine: ' + ENGINE_CONN )

    #check if vm exist and is down
    EXIT_ON = 'CHECKVM'
    checkVM( VMNAME )

    #check private and pub key
    EXIT_ON = 'CHECKSSHKEY'
    SSHKEY = checkSshKey( SSHKEY )
    logDebug( "ssh pub key is: " )
    logDebug( SSHKEY )

    #now try to launch vm whith cloud-init options
    EXIT_ON = 'STARTVM'
    FQDN = VMNAME + "." + DOMAIN
    FQDN = FQDN.lower()
    logDebug( "FQDN: %s" %(FQDN) )
    scontent = buildYamlFile()
    logDebug("Cloud-init user data content: ")
    logDebug( scontent )

    try:
        vm = api.vms.get(name=VMNAME)
        action = params.Action(
                        vm=params.VM(
                            initialization=params.Initialization(
                                cloud_init=params.CloudInit(
                                    host=params.Host(address=FQDN),
                                    authorized_keys=params.AuthorizedKeys(
                                        authorized_key=[params.AuthorizedKey(user=params.User(user_name="root"), key=SSHKEY)]
                                        ),
                                    regenerate_ssh_keys=True,
                                    users=params.Users(
                                        user=[params.User(user_name="root", password=SPASSWORD)]
                                        ),
                                    network_configuration=params.NetworkConfiguration(
                                        nics=params.Nics(nic=[params.NIC(name="eth0",
                                                            boot_protocol="STATIC",
                                                            on_boot=True,
                                                            network=params.Network(ip=params.IP(
                                                                                    address=IPADDR,
                                                                                    netmask=NETMASK,
                                                                                    gateway=GATEWAY)))])
                                        ),
                                    files=params.Files(
                                        file=[params.File(name="/etc/motd", content=scontent, type_="PLAINTEXT")]
                                        )
                                    )
                                )
                            )
                        )
        logDebug( "Starting VM %s with cloud-init options" %(VMNAME) )
        vm.start( action )

        #vm started add sleeptime
        vm = api.vms.get(name=VMNAME)
        while ( vm.get_status().state != 'up' ):
            logDebug( "VM %s is on state %s, sleeping %s seconds" %( vm.get_name(), vm.get_status().state, str( SLEEPTIME ) ) )
            sleep(SLEEPTIME)
            vm = api.vms.get(name=VMNAME)
        print ( "VM %s is up, with ip %s an IPA client configured, finish." %( vm.get_name(), IPADDR ) )
    except Exception, err:
        logDebug( "Error on starting VM", 2 )
        logDebug( err, 2) 
except:
    if EXIT_ON == '':
        logDebug( 'Error: Connection failed to server: ' + ENGINE_CONN, 2)
    else:
        logDebug( 'Error on ' + EXIT_ON, 2)
finally:
    if api != None:
        logDebug( 'Closing connection to the engine: ' + ENGINE_CONN )
        api.disconnect()
