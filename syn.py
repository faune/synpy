#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

import signal
from gi.repository import GLib
from gi.repository import GObject

import sys
import copy
import fcntl
import iplib
import subprocess


SYNERGY_RUNNING = 'Synergy %s is running'
SYNERGY_STOPPED = 'Synergy %s is stopped'


class SynergyProcess(object):
    cmd=[]
    def __init__(self, config=None):
        self.subProcess = None
        self.cmd = copy.deepcopy(self.__class__.cmd) # Prevent mutable lists
        if config is not None:
            self.cmd.append(config)
    def __str__(self):
        return '(unknown)'
    def start(self):
        print('CMD: %s' % self.cmd)
        self.subProcess = subprocess.Popen(self.cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Configure read from stdout pipe as non-blocking
        flags = fcntl.fcntl(self.subProcess.stdout, fcntl.F_GETFL) # get current p.stdout flags
        fcntl.fcntl(self.subProcess.stdout, fcntl.F_SETFL, flags | os.O_NONBLOCK)
    def stop(self):
        if self.subProcess is not None:
            self.subProcess.terminate()
            return self.subProcess.returncode
        return 0
    def read(self, length=1024):
        try:
            return os.read(self.subProcess.stdout.fileno(), 1024)
        except Exception, err:
            return ''
    
        
class SynergyClient(SynergyProcess):
    cmd=['../build/bin/synergy-core','--client','-f']
    def __str__(self, config=None):
        return 'client'

class SynergyServer(SynergyProcess):
    cmd=['../build/bin/synergy-core','--server','-f','-c']
    def __str__(self):
        return 'server'
    
    
class SignalHandler(object):
    def __init__(self, parent):
        self.parent = parent

        self.quitID = self.parent.window.connect('destroy', self.onDestroy)
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, self.onDestroy)        

        # Checkboxes
        self.chkboxServerID = self.parent.chkboxServer.connect('toggled', self.onCheckboxServer)
        self.chkboxClientID = self.parent.chkboxClient.connect('toggled', self.onCheckboxClient)
        self.chkboxInteractiveID = self.parent.chkboxInteractive.connect('toggled', self.onCheckboxInteractive)
        self.chkboxConfigFileID = self.parent.chkboxConfigFile.connect('toggled', self.onCheckboxConfigFile)

        # Buttons
        self.btnApplyID = self.parent.btnApply.connect('clicked', self.onButtonApply)
        self.btnStartID = self.parent.btnStart.connect('clicked', self.onButtonStart)
        self.btnConfigureID = self.parent.btnConfigure.connect('clicked', self.onButtonConfigure)
        self.btnFileSelectedID = self.parent.btnFileSelected.connect('file-set', self.onButtonFileSelected)
        
        
    def onDestroy(self, *args):
        if self.parent.synergy is not None:
            self.parent.synergy.stop()
        self.parent.writeConfig()
        Gtk.main_quit()
        
    def onCheckboxServer(self, *args):
        print('Checkbox server')
        # Uncheck client checkbox
        if self.parent.chkboxClient.get_active() is True:
            self.parent.chkboxClient.handler_block(self.chkboxClientID)
            self.parent.chkboxClient.set_active(False)
            self.parent.chkboxClient.handler_unblock(self.chkboxClientID)

        # Set correct referrence
        self.parent.synergy = self.parent._server
            
        # Enable/disable start button
        if self.parent.chkboxServer.get_active() is True:
            self.parent.btnStart.set_sensitive(True)
        else:
            self.parent.btnStart.set_sensitive(False)

    def onCheckboxClient(self, *args):
        # Uncheck server checkbox
        if self.parent.chkboxServer.get_active() is True:
            self.parent.chkboxServer.handler_block(self.chkboxServerID)
            self.parent.chkboxServer.set_active(False)
            self.parent.chkboxServer.handler_unblock(self.chkboxServerID)

        # Set correct referrence
        self.parent.synergy = self.parent._client
            
        # Enable/disable start button
        if self.parent.chkboxClient.get_active() is True:
            self.parent.btnStart.set_sensitive(True)
        else:
            self.parent.btnStart.set_sensitive(False)
                
    def onCheckboxInteractive(self, *args):
        print('Checkbox interactive')
        if self.parent.chkboxConfigFile.get_active() is True:
            self.parent.chkboxConfigFile.handler_block(self.chkboxConfigFileID)
            self.parent.chkboxConfigFile.set_active(False)
            self.parent.chkboxConfigFile.handler_unblock(self.chkboxConfigFileID)
            
    def onCheckboxConfigFile(self, *args):
        print('Checkbox config file')
        if self.parent.chkboxInteractive.get_active() is True:
            self.parent.chkboxInteractive.handler_block(self.chkboxInteractiveID)
            self.parent.chkboxInteractive.set_active(False)
            self.parent.chkboxInteractive.handler_unblock(self.chkboxInteractiveID)

    def onButtonApply(self, *args):       
        # Write config
        self.parent.writeConfig()

        
    def onButtonStart(self, *args):
        # Configure synergy proxy object
        if self.parent.chkboxServer.get_active() is True:
            # Start server process
            self.parent.synergy = self.parent._server
        elif self.parent.chkboxClient.get_active() is True:
            # Start client process
            self.parent.synergy = self.parent._client
        else:
            self.parent.synergy = None
            
        # Start/stop synergy proxy
        if self.parent.btnStart.get_label() == 'Start':
            print('Changing label to Stop')
            self.parent.btnStart.set_label('Stop')
            self.parent.synergy.start()
            self.parent.frameServer.set_sensitive(False)
            self.parent.frameClient.set_sensitive(False)
            self.parent.labelStatus.set_label(SYNERGY_RUNNING % self.parent.synergy)
        elif self.parent.btnStart.get_label() == 'Stop':
            print('Changing label to Start')
            self.parent.btnStart.set_label('Start')
            self.parent.synergy.stop()
            self.parent.frameServer.set_sensitive(True)
            self.parent.frameClient.set_sensitive(True)
            self.parent.labelStatus.set_label(SYNERGY_STOPPED % self.parent.synergy)
        else:
            #TODO: Popup?
            pass
        
    def onButtonConfigure(self, *args):
        print('Button configure')
        
    def onButtonFileSelected(self, *args):
        print('Button file selected')

        # Re-instantiate synergy object with config file set
        self.parent._server = SynergyServer(self.parent.btnFileSelected.get_filename())
        self.parent.synergy = self.parent._server


class Application():
    def __init__(self):

        # Object attributes
        self.config = None
        self.configFile = None

        # Initialize GUI
        self.initGladeInterface()
        self.initWidgets()
        self.initLabels()
        self.initLogging()
        self.initImages()
        self.initSignalHandlers()

        # Configuration
        self.initConfig()
        
        # Show main window
        self.window.show_all()
        if self.config.getboolean('STARTUP', 'minimized') is True:
            self.window.minimize()
        if self.config.getboolean('STARTUP', 'autorun') is True:
            #TODO: Start
            pass

        
    def initConfig(self):
        # Create/load configuration file
        home = os.path.expanduser("~")
        self.config = configparser.ConfigParser()
        if sys.platform.startswith('linux'):
            self.configFile = '%s%s.local%ssynpy%ssynpy.conf' % (home, os.sep, os.sep, os.sep)
        elif sys.platform.startswith('win'):
            self.configFile = '%s%ssynpy%ssynpy.conf' % (os.getenv('LOCALAPPDATA'), os.sep, os.sep)
        elif sys.platform.startswith('macos'):
            self.configFile = '%s%s.synpy.conf' % (home, os.sep)
        else:
            print('ERROR: Unknown platform: %s' % sys.platform)
            sys.exit(-1)

    
        if len(self.config.read(self.configFile)) == 0:
            # No config file preset, create default one
            self.config.add_section('STARTUP')
            self.config.add_section('SERVER')
            self.config.add_section('CLIENT')
            
            self.config.set('DEFAULT', 'server_mode', 'true')
            self.config.set('STARTUP', 'minimized', 'false')
            self.config.set('STARTUP', 'autorun', 'false')
            self.config.set('SERVER', 'interactive', 'true')
            self.config.set('SERVER', 'config_file', '')
            self.config.set('CLIENT', 'connect_address', '')
            self.writeConfig()

                    
        
        serverMode = self.config.getboolean('DEFAULT', 'server_mode')
        serverInteractive = self.config.getboolean('SERVER', 'interactive')
        serverConfigFile = self.config.get('SERVER', 'config_file')
        clientConnectAdr = self.config.get('CLIENT', 'connect_address')

        if len(serverConfigFile) > 0:
            self.btnFileSelected.set_filename(serverConfigFile)
        if len(clientConnectAdr) > 0:
            self.clientConnectAddress.set_text(clientConnectAdr)        
        if serverMode is True:
            # Server configuration
            self.chkboxServer.handler_block(self.signalHandler.chkboxServerID)
            self.chkboxServer.set_active(True)
            self.chkboxServer.handler_unblock(self.signalHandler.chkboxServerID)

            if serverInteractive is True:
                self.chkboxInteractive.handler_block(self.signalHandler.chkboxInteractiveID)
                self.chkboxInteractive.set_active(True)
                self.chkboxInteractive.handler_unblock(self.signalHandler.chkboxInteractiveID)
            else:
                self.chkboxConfigFile.handler_block(self.signalHandler.chkboxConfigFileID)
                self.chkboxConfigFile.set_active(True)
                self.chkboxConfigFile.handler_unblock(self.signalHandler.chkboxConfigFileID)
            
        else:
            # Client configuration
            # TODO
            pass


        # Server and client proxy objects
        self.synergy = None
        self._server = SynergyServer(config=serverConfigFile)
        self._client = SynergyClient(config=clientConnectAdr)

        

    def writeConfig(self):
        """
        Write current configuration to file
        """
        print('Button apply')
        self.config.set('DEFAULT', 'server_mode', '%i' % self.chkboxServer.get_active())
        #self.config.set('STARTUP', 'minimized', 'false')
        #self.config.set('STARTUP', 'autorun', 'false')
        self.config.set('SERVER', 'interactive', '%i' % self.chkboxInteractive.get_active())
        self.config.set('SERVER', 'config_file', '%s' % self.btnFileSelected.get_filename())
        self.config.set('CLIENT', 'connect_address', '%s' % self.clientConnectAddress.get_text())


        # Write config to disk
        try:
            os.makedirs(os.path.dirname(self.configFile))
        except Exception, err:
            pass
        with open(self.configFile, 'w+') as fileh:
            self.config.write(fileh)
    
        
    def initGladeInterface(self):
        # Load GLADE interface
        self.gladefile = 'glade/main.glade'
        self.builder = Gtk.Builder()
        self.builder.add_from_file(self.gladefile)

    def initWidgets(self):
        # Create objects for accessing widgets
        self.window = self.builder.get_object('ID_MAIN')

        self.frameServer = self.builder.get_object('ID_FRAME_SERVER')
        self.frameClient = self.builder.get_object('ID_FRAME_CLIENT')
        
        self.chkboxServer = self.builder.get_object('ID_CHKBOX_SERVER')
        self.chkboxClient = self.builder.get_object('ID_CHKBOX_CLIENT')
        self.chkboxInteractive = self.builder.get_object('ID_CHKBOX_INTERACTIVE')
        self.chkboxConfigFile = self.builder.get_object('ID_CHKBOX_CONFIG_FILE')

        self.labelServerIP = self.builder.get_object('ID_LABEL_SERVER_IP')
        self.labelScreenName = self.builder.get_object('ID_LABEL_SCREEN_NAME')
        self.labelStatus = self.builder.get_object('ID_LABEL_STATUS')

        self.clientConnectAddress = self.builder.get_object('ID_CLIENT_CONNECT_ADDRESS')
                
        self.btnApply = self.builder.get_object('ID_BTN_APPLY')
        self.btnStart = self.builder.get_object('ID_BTN_START')
        self.btnConfigure = self.builder.get_object('ID_BTN_CONFIGURE')
        self.btnFileSelected = self.builder.get_object('ID_BTN_FILE_SELECTED')


    def initLabels(self):
        """
        Function for setting GTK.Label values
        """
        # Server IP
        ipLabel=''
        for ip in iplib.getIPs():
            if len(ipLabel) != 0:
                ipLabel += ', '
            ipLabel += '%s ' % ip
        self.labelServerIP.set_label(ipLabel)
        
        # Client screen name
        if sys.platform.startswith('win'):
            pass
        elif sys.platform.startswith('linux'):
            p = subprocess.Popen(['xdpyinfo'], stdout=subprocess.PIPE)
            for line in p.communicate()[0].split('\n'):
                if line.startswith('name of display'):
                    k, screenLabel = line.split(':', 1)
                    screenLabel = screenLabel.strip()
                    self.labelScreenName.set_label(screenLabel)
        elif sys.platform.startswith('macos'):
            pass
        else:
            pass

        
    def initLogging(self):
        # Logging widgets
        self.logScrolledWindow = self.builder.get_object('ID_SCROLLED_WINDOW')
        self.logTextView = self.builder.get_object('ID_TXTVIEW_LOG')
                
        
    def initSignalHandlers(self):
        # Install signal handlers
        self.signalHandler = SignalHandler(self)
        GObject.idle_add(self.onIdleUpdateLog)


    def initImages(self):
        """
        Create a taskbar and program icon
        """
        # Taskbar status icon
        self.statusIcon = Gtk.StatusIcon()
        self.statusIcon.set_from_file('../src/cmd/synergys/synergys.ico')
        self.statusIcon.set_visible(True)
        self.statusIcon.connect('popup-menu', self.onRightClickTaskbar)
        self.statusIcon.connect('activate', self.onLeftClickTaskbar)

        # Main window icon
        self.window.set_icon_from_file('../src/cmd/synergys/synergys.ico')
        
        
    def onRightClickTaskbar(self, evt_btn, evt_time, data=None):
        """
        Event handler for right click on taskbar icon
        """
        # Create GTK Menu on right click
        menu = Gtk.Menu()

        # Create Quit item
        quitItem = Gtk.MenuItem('Quit')
        quitItem.connect_object('activate', self.signalHandler.onDestroy, 'Close Synergy')
        quitItem.show()

        # Append and popup meu
        menu.append(quitItem)
        menu.popup(None, None, None, evt_btn, evt_time, data)

        
    def onLeftClickTaskbar(self, statusIcon):
        """
        Event handler for left click on taskbar icon
        """
        if self.window.get_property('visible') is True:
            # Iconify and hide main window
            self.window.iconify()
            self.window.hide()
        else:
            # Deiconify and show main window
            self.window.deiconify()
            self.window.show()

            
    def onIdleUpdateLog(self):
        """
        Callback for GTK on_idle handler
        """
        if self.synergy is not None:
            data = self.synergy.read()
            if len(data) > 0:
                # Insert data at cursor position
                self.logTextView.get_buffer().insert_at_cursor(data)
                # Adjust scrollbar to accommodate newly inserted data
                adj = self.logScrolledWindow.get_vadjustment()
                adj.set_value(adj.get_upper() - adj.get_page_size())

        # Call again on next on_idle
        return True
        

        
if __name__ == "__main__":
    import os
    import configparser

    app = Application()
    Gtk.main()
