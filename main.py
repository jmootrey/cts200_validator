#!/usr/bin/env python3
import signal
import sys
import sqlite3
import subprocess
import paramiko
import socket
import configparser
import time
from pathlib import Path
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

#########################################################
#
# CTS Validation system. Validates MD5 Hash on critical
# configuration files. 
#
# Author: Jeff Mootrey
# Release: 20180302
#
#########################################################

class Handler:

    def __init__(self):
        self.store = Gtk.ListStore(str)
        self.validate_button = builder.get_object('validate_button')
        self.message_dialog = builder.get_object('message_dialog')
        self.order_entry = builder.get_object('order_entry')
        self.customer_entry = builder.get_object('customer_entry1')
        self.lot_entry = builder.get_object('lot_entry')
        self.ip_entry = builder.get_object('ip_entry')
        self.db_colorbox = builder.get_object('db_colorbox')
        self.cts_colorbox = builder.get_object('cts_colorbox')
        self.ip_colorbox = builder.get_object('ip_colorbox')
        self.md5_colorbox = builder.get_object('md5_colorbox')
        self.version_colorbox = builder.get_object('version_colorbox')
        self.dbfile = Path(cfg['DATABASE']['file'])
        self.customer_model = builder.get_object('customer_model')
        if self.dbfile.is_file():
            self.sq_conn = sqlite3.connect(str(self.dbfile))
            self.c = self.sq_conn.cursor()
            self.c.execute("SELECT customer FROM cts;")
            self.customers = self.c.fetchall()
            self.customer_model.clear()
            for self.item in self.customers:
                self.customer_model.append(self.item)
            db_colorbox = builder.get_object('db_colorbox')
            db_colorbox.set_rgba(Gdk.RGBA(0,0.8,0,1))
        
    def customer_entry_changed(self, *args):
        self.validate_button.set_sensitive(False)
    
    def check_socket(self, ip):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(2)
        self.result = self.sock.connect_ex((ip, 22))
        if self.result == 0:
            self.sock.close()
            return True
        else:
            self.sock.close()
            return False

    def get_remote_data(self, ip):
        self.d = {}
        try:
            self.s = paramiko.SSHClient()
            self.s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.s.connect(hostname=ip, port=22, username='emteq',
                password='Q3tm36170')
        except:
            self.error_message('Secure Shell Connection Error')
            return False
        self.stdin, self.ecmd5, self.stderr = self.s.exec_command("md5sum /opt/eConnect/App/econapp | cut -d ' ' -f1 | tr -d %'\n'")
        self.stdin2, self.dbmd5, self.stderr2 = self.s.exec_command("md5sum /opt/database/database.tgz | cut -d ' ' -f1 | tr -d %'\n'")
        self.stdin3, self.ver, self.stderr3 = self.s.exec_command("sudo /opt/eConnect/scripts/misc/ecms-versions.sh")
        while not self.ecmd5.channel.exit_status_ready() or not self.dbmd5.channel.exit_status_ready() or not self.ver.channel.exit_status_ready():
            time.sleep(.1)    
        if self.ecmd5.channel.recv_exit_status() == 0:
            self.d['ecmd5'] = self.ecmd5.readline()
        else:
            self.d['ecmd5'] = 'Error'
            self.error_message('Error Retreiving EC MD5 Hash')
            return
        if self.dbmd5.channel.recv_exit_status() == 0:
            self.d['dbmd5'] = self.dbmd5.readline()
        else:
            self.d['dbmd5'] = 'Error'
            self.error_message('Error Retreiving DB MD5 Hash')
            return
        if self.ver.channel.recv_exit_status() == 0:
            self.d['version'] = self.ver.readlines()
        else:
            self.d['version'] = 'Error'
            self.error_message('Error Retreiving Version Data')
            return
        return self.d
    
    def error_message(self, msg):
        error_dialog.format_secondary_text(msg)
        error_dialog.show_all()
        self.reset_indicators()
        self.validate_button.set_sensitive(False)
        return

    def validate_clicked(self, *args):
        self.c = 0
        while True:
            self.result = self.check_socket(dbdata[1])
            self.c += 1
            if self.result:
                self.ip_colorbox.set_rgba(Gdk.RGBA(0,0.8,0,1))
                self.cts_colorbox.set_rgba(Gdk.RGBA(0,0.8,0,1))
                break
            if self.c >= 1:
                # raise error 1432
                self.ip_colorbox.set_rgba(Gdk.RGBA(0.64,0,0,1))
                self.cts_colorbox.set_rgba(Gdk.RGBA(0.64,0,0,1))
                self.error_message('Unable To Locate CTS')
                return
        self.remote_data = self.get_remote_data(dbdata[1])
        if self.remote_data:
            if self.remote_data['version'] != 'Error':
                self.version_colorbox.set_rgba(Gdk.RGBA(0,0.8,0,1))
            if 'Error' not in self.remote_data.values():
                if self.validate(self.remote_data):
                    #commit to record
                    self.create_record(self.remote_data)
                    self.message_dialog.show_all()
                    return
                else:
                    self.error_message('Fail!\nMD5 Hash Match Error')
                    
            else:
                self.error_message('Fail!\nUnable to Generate Remote MD5')
                
                return
        else:
            return
    def validate(self, data):
        if data['ecmd5'] == dbdata[2]:
            if data['dbmd5'] == dbdata[3]:
                self.md5_colorbox.set_rgba(Gdk.RGBA(0,0.8,0,1))
                return True
            else:
                return False
        else:
            return False
        

    def reset_indicators(self):
        self.cts_colorbox.set_rgba(Gdk.RGBA(0.64,0,0,1))
        self.ip_colorbox.set_rgba(Gdk.RGBA(0.64,0,0,1))
        self.md5_colorbox.set_rgba(Gdk.RGBA(0.64,0,0,1))
        self.version_colorbox.set_rgba(Gdk.RGBA(0.64,0,0,1))
    
    def scan_clicked(self, *args):
        global dbdata
        # Reset Indicators
        self.reset_indicators()
        self.order_text = self.order_entry.get_text()
        self.customer_text = self.customer_model[self.customer_entry.get_active()][0]
        self.lot_text = self.lot_entry.get_text()
        if not self.order_text:
            # call error
            self.error_message('Order Number Required')
        elif not self.customer_text:
            self.error_message('Customer Required')
        elif not self.lot_text:
            self.error_message('Lot Number Required')
        else:
            dbdata = self.get_local_data(self.customer_text, self.dbfile)
            if dbdata:
                self.ip_entry.set_text(dbdata[1])
                self.c = 0
                while True:
                    self.result = self.check_socket(dbdata[1])
                    self.c += 1
                    if self.result:
                        self.ip_colorbox.set_rgba(Gdk.RGBA(0,0.8,0,1))
                        self.cts_colorbox.set_rgba(Gdk.RGBA(0,0.8,0,1))
                        break
                    if self.c >= 1:
                        # raise error 1432
                        break
                self.validate_button.set_sensitive(True)
            else:
                self.ip_entry.set_text('')
                self.error_message('Unable To Locate Customer')

    def get_local_data(self, customer, database):
        self.sq_conn = sqlite3.connect(str(database))
        self.c = self.sq_conn.cursor()
        try:
            self.c.execute("SELECT * FROM cts WHERE customer=?;", (customer, ))
            self.data = self.c.fetchone()
            return self.data
        except:
            self.error_message('Unable To Locate Customer In Database')
            self.sq_conn.close()
            return False

    def create_record(self, data):
        self.tstamp = time.strftime("%Y%m%d.%H%M")
        data['Timestamp'] = self.tstamp
        data['Customer' ] = self.customer_text
        data['Lot'] = self.lot_text
        self.rec = configparser.ConfigParser()
        self.rec['Record'] = data
        self.fn = 'records/'+ self.customer_text + '-' + self.lot_text + '-' + self.tstamp + '.txt'
        try:
            with open(self.fn, 'w') as self.cfile:
                self.rec.write(self.cfile)
            return
        except:
            #raise error
            self.error_message('Unable To Write Record')
            return False

    def exit_app(self, *args):
        Gtk.main_quit()
    
    def menu_open_select(self, *args):
        file_open.show_all()

    def file_open_clicked(self, *args):
        self.filename = file_open.get_filename()
        cfg['DATABASE']['file'] = self.filename
        self.dbfile = Path(cfg['DATABASE']['file'])
        if self.dbfile.is_file():
            self.t = subprocess.check_output(['file', '-b', self.filename])
            self.t = self.t.decode('UTF-8')
            if 'SQLite 3.x database' in self.t:
                self.sq_conn = sqlite3.connect(str(self.dbfile))
                self.c = self.sq_conn.cursor()
                self.c.execute("SELECT customer FROM cts;")
                self.customers = self.c.fetchall()
                self.customer_model.clear()
                for self.item in self.customers:
                    self.customer_model.append(self.item)
                    self.db_colorbox.set_rgba(Gdk.RGBA(0,0.8,0,1))
                with open('.config.ini', 'w') as self.configfile:
                    cfg.write(self.configfile)
            else:
                self.error_message('Not A CTS200 Database File\nConfiguration NOT updated')
        file_open.hide()
        

def devent(self, *args):
    self.hide()
    return True

if __name__ == '__main__':
    # capture signals
    def sig_handle(signal, frame):
        window.connect("delete-event", Gtk.main_quit)
        sys.exit(0)
    signal.signal(signal.SIGINT, sig_handle)
    # Build UI
    builder = Gtk.Builder()
    builder.add_from_file('main.glade')
    cfg = configparser.ConfigParser()
    cfg.read('.config.ini')
    builder.connect_signals(Handler())
    window = builder.get_object("main_window")
    error_dialog = builder.get_object("error_dialog")
    file_open = builder.get_object("file_open")
    message_dialog = builder.get_object("message_dialog")
    window.connect("delete-event", Gtk.main_quit)
    error_dialog.connect("delete-event", devent)
    file_open.connect("delete-event", devent)
    message_dialog.connect("delete-event", devent)

    window.show_all()
    Gtk.main()
