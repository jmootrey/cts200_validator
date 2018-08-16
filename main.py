#!/usr/bin/env python3
import signal
import os
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
# Release 20180807
#  Including CWR45x
# Release 20180321
#  Added run mode config.
# Release: 20180302
#  Initial Release
#########################################################



# Signal Handler
class Handler:

    def __init__(self):
        self.store = Gtk.ListStore(str)
        self.validate_button = builder.get_object('validate_button')
        self.scan_button = builder.get_object('scan_button')
        self.message_dialog = builder.get_object('message_dialog')
        self.order_entry = builder.get_object('order_entry')
        self.customer_entry = builder.get_object('customer_entry')
        self.platform_entry = builder.get_object('part_entry')
        self.variant_entry = builder.get_object('variant_entry')
        self.lot_entry = builder.get_object('lot_entry')
        self.ip_entry = builder.get_object('ip_entry')
        self.db_colorbox = builder.get_object('db_colorbox')
        self.cts_colorbox = builder.get_object('cts_colorbox')
        self.ip_colorbox = builder.get_object('ip_colorbox')
        self.md5_colorbox = builder.get_object('md5_colorbox')
        self.version_colorbox = builder.get_object('version_colorbox')
        self.dbfile = Path(cfg['DATABASE']['file'])
        self.customer_model = builder.get_object('customer_model')
        self.platform_model = builder.get_object('component_model')
        self.variant_model = builder.get_object('variant_model')
        self.statusbar = builder.get_object('statusbar')
        self.context_id = self.statusbar.get_context_id('main')
        self.statusbar.push(self.context_id, 'Status: Idle')
        if self.dbfile.is_file():
            self.sq_conn = sqlite3.connect(str(self.dbfile))
            self.c = self.sq_conn.cursor()
            self.c.execute("SELECT customer FROM customer;")
            self.customers = self.c.fetchall()
            self.customer_model.clear()
            for self.item in self.customers:
                self.customer_model.append(self.item)
            db_colorbox = builder.get_object('db_colorbox')
            db_colorbox.set_rgba(Gdk.RGBA(0,0.8,0,1))
        
    def customer_entry_changed(self, *args):
        index = self.customer_entry.get_active()
        if index >= 0:
            model = self.customer_entry.get_model()
            customer = model[index]
            self.customer = customer[0]
            platforms = self.get_local_data(self.customer, self.dbfile, 'platform')
            if platforms:
                self.validate_button.set_sensitive(False)
                self.platform_entry.set_sensitive(True)
                self.platform_model.clear()
                for item in platforms:
                    self.platform_model.append(item)
                self.platform_entry.set_active(0) 

    def part_changed(self, *args):
        index = self.platform_entry.get_active()
        if index >= 0:
            model = self.platform_entry.get_model()
            part = model[index]
            self.part = part[0]
            variants = self.get_local_data(self.part, self.dbfile, 'variant')
            if variants:
                self.validate_button.set_sensitive(False)
                self.variant_model.clear()
                for item in variants:
                    self.variant_model.append(item)
                self.variant_entry.set_active(0)
                       
    def variant_changed(self, *args):
        index = self.variant_entry.get_active()
        if index >= 0:
            model = self.variant_entry.get_model()
            variant = model[index]
            self.variant=variant[0]
            config_id = self.get_local_data(self.variant, self.dbfile, 'config_id')
            if config_id :
                self.scan_button.set_sensitive(True)
                self.config_id = config_id[0]
                self.config_id = self.config_id[0]
                config_ip = self.get_local_data(self.config_id, self.dbfile, 'config_ip')
                self.config_ip = config_ip[0]
                self.config_ip = self.config_ip[0]
                self.ip_entry.set_text(self.config_ip +' | Hex: '+hex(int(self.config_ip.split(".")[3])))
    
    # Validates prescence of CTS device by checking for open ssh port
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

    
    def error_message(self, msg):
        error_dialog.format_secondary_text(msg)
        error_dialog.show_all()
        self.reset_indicators()
        self.validate_button.set_sensitive(False)
        self.status_update('Status: Scan / Validation Failed!')
        return

    def error_ok_clicked(self, *args):
        error_dialog.hide()
        return
        
    def message_ok_clicked(self, *args):
        message_dialog.hide()
        return

    def user_message(self, msg):
        message_dialog.format_secondary_text(msg)
        message_dialog.show_all()

    def scan_clicked(self, *args):
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
            if self.check_socket(self.config_ip):
                self.cts_colorbox.set_rgba(Gdk.RGBA(0,0.8,0,1))
                self.ip_colorbox.set_rgba(Gdk.RGBA(0,0.8,0,1))
                test_cases = self.get_local_data(self.config_id, self.dbfile, 'test_case')
                if test_cases:
                    self.user_message("Located " + str(len(test_cases)) + " Test Cases. \nClose This Message And Press Validate To Continue.")
                    self.test_cases = test_cases  
                    self.validate_button.set_sensitive(True)
            else:
                self.error_message('Unable to locate device at ip:\t'+self.config_ip)
    def status_update(self, msg):
        self.statusbar.push(self.context_id, msg)
        while Gtk.events_pending():     #this forces GTK to refresh the screen
                Gtk.main_iteration()
    
    def validate_clicked(self, *args):
    
        if self.run_tests():
            self.md5_colorbox.set_rgba(Gdk.RGBA(0,0.8,0,1))
            while Gtk.events_pending():     #this forces GTK to refresh the screen
                Gtk.main_iteration()
            version_data = self.get_remote_data(self.config_ip, '/opt/eConnect/scripts/misc/ecms-versions.sh', 'version')
            if self.create_record(version_data):
                self.version_colorbox.set_rgba(Gdk.RGBA(0,0.8,0,1))
                self.status_update('Status: Validation Complete!')
                self.user_message('Validation Completed Succesfully!')
        else:
            while Gtk.events_pending():     #this forces GTK to refresh the screen
                Gtk.main_iteration()
            return

    def run_tests(self):
        iteration=0
        for test in self.test_cases:
            iteration+=1
            self.status_update("Status: Performing Test Case "+ str(iteration) + " of " + str(len(self.test_cases)))
            
            result = self.get_remote_data(self.config_ip, test[1], test[0])
            if str(result) != str(test[2]):
                self.error_message("Target:\t"+str(test[1])+"\nExpected Value:\t"+str(test[2])+"\nActual Value:\t"+str(result))
                return False
        return True
                

    def get_remote_data(self, ip, target, datatype):
        passwd = 'Q3tm36170'
        try:
            s = paramiko.SSHClient()
            s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            s.connect(hostname=ip, port=22, username='emteq', password=passwd)
        except:
            self.error_message('Secure Shell Connection Error')
            return False
        if datatype == 'md5':
            stdin, stdout, stderr = s.exec_command("sudo -S -p ' ' md5sum "+target+" | cut -d ' ' -f1 | tr -d %'\n'")
            stdin.write(passwd + "\n")
            stdin.flush()
            while not stdout.channel.exit_status_ready():
                time.sleep(.1)
            s.close()
            return stdout.readline()
        elif datatype == 'text':
            stdin, stdout, stderr = s.exec_command("sudo -S -p ' ' cat "+target+" | cut -d ' ' -f1 | tr -d %'\n'")
            stdin.write(passwd + "\n")
            stdin.flush()
            while not stdout.channel.exit_status_ready():
                time.sleep(.1)
            s.close()
            return stdout.readline()
        elif datatype == 'version':
            stdin, stdout, stderr = s.exec_command("sudo -S -p ' ' "+ target +'\n')
            stdin.write(passwd + "\n")
            stdin.flush()
            while not stdout.channel.exit_status_ready():
                time.sleep(.1)
            s.close()
            return stdout.readlines()

 #   def config_runmode(self, config_id, database): #This function is for future use.
 #       keys = ['customer', 'bm', 'vlan', 'vip', 'vnet', 'vgw', 'vdns', 'capf', 'wd']
 #       data = list(self.get_local_data(self.customer_text, self.dbfile, 'run_mode'))
 #       try:
 #           s = paramiko.SSHClient()
 #           s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
 #           s.connect(hostname=dbdata[1], port=22, username='emteq',
 #               password='Q3tm36170')
 #       except:
 #           self.error_message('Secure Shell Connection Error')
 #           return False
 #       for k, v in zip(keys, data):
 #           if k != 'customer' and v:
 #               stdin, stdout, stderr = s.exec_command("sudo /opt/testapps/eeprom/ta_eeprom {} {}".format(k, v))
 #               while not stdout.channel.exit_status_ready():
 #                   time.sleep(.1)    
 #               if stdout.channel.recv_exit_status() != 0:
 #                   self.error_message('Unable to set {}'.format(k))
 #                   s.close()
 #                   return False
 #       s.close()
 #       return True

    def reset_indicators(self):
        self.cts_colorbox.set_rgba(Gdk.RGBA(0.64,0,0,1))
        self.ip_colorbox.set_rgba(Gdk.RGBA(0.64,0,0,1))
        self.md5_colorbox.set_rgba(Gdk.RGBA(0.64,0,0,1))
        self.version_colorbox.set_rgba(Gdk.RGBA(0.64,0,0,1))

    def get_local_data(self, key, database, datatype):
        sq_conn = sqlite3.connect(str(database))
        c = sq_conn.cursor()
        if datatype == 'customer':
            try:
                c.execute("SELECT * FROM cts WHERE customer=?;", (key, ))
                data = c.fetchone()
                sq_conn.close()
                return data
            except:
                self.error_message('Unable To Locate Customer In Database')
                sq_conn.close()
                return False
        elif datatype == 'run_mode':
            try:
                c.execute("SELECT * FROM run_mode WHERE customer=?;", (key, ))
                data = c.fetchone()
                sq_conn.close()
                return data
            except:
                self.error_message('Unable To Locate Customer In Database')
                sq_conn.close()
                return False
        elif datatype == 'platform':
            try:
                c.execute("select platform from platform where platform_id in \
                (select platform_id from config where customer_id in \
                (select customer_id from customer where customer.customer = ?));", (key, ))
                data = c.fetchall()
                sq_conn.close()
                return data
            except:
                self.error_message('Unable To Locate Customer In Database')
                sq_conn.close()
                return False
        elif datatype == 'variant':
            try:
                c.execute("select variant from config where customer_id in \
                (select customer_id from customer where customer.customer = ?) AND platform_id in \
                (select platform_id from platform where platform  = ?)", (self.customer, key, ))
                data = c.fetchall()
                sq_conn.close()
                return data
            except:
                self.error_message('Unable To Locate Variants In Database')
                sq_conn.close()
                return False
        elif datatype == 'config_id':
            try:
                c.execute("select config_id from config where customer_id in \
                (select customer_id from customer where customer.customer = ?) AND platform_id in \
                (select platform_id from platform where platform  = ?) AND variant = ?", (self.customer, self.part, key, ))
                data = c.fetchall()
                sq_conn.close()
                return data
            except:
                self.error_message('Unable To Locate ConfigID In Database')
                sq_conn.close()
                return False
        elif datatype == 'config_ip':
            try:
                c.execute("select ip_address from config where config_id = ?;", (key, ))
                data = c.fetchall()
                sq_conn.close()
                return data
            except:
                self.error_message('Unable To Locate IP address In Database')
                sq_conn.close()
                return False
        elif datatype == 'test_case':
            try:
                c.execute("select type, target, value from test_case where config_id = ?;", (key, ))
                data = c.fetchall()
                sq_conn.close()
                return data
            except:
                self.error_message('Unable To Locate Test Cases In Database')
                sq_conn.close()
                return False


    def create_record(self, version_data):
        tstamp = time.strftime("%Y%m%d.%H%M")
        fn = 'records/'+ self.customer_text + '-' + self.lot_text + '-' + tstamp + '.txt'
        self.status_update("Status: Generating Report '" + fn +"'")
        try:
            with open(fn, 'w') as record:
                record.write('Order Number: \t'+ self.order_text)
                record.write('\nCustomer:\t' + self.customer_text)
                record.write('\nLot:\t\t'+ self.lot_text)
                record.write('\nComponent:\t'+ self.part)
                record.write('\nConfig Variant:\t' + self.variant)
                record.write('\n\nVersion Data:\n')
                record.writelines(version_data)
            return True
        except:
            self.error_message('Unable To Write Record!')
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
                try:
                    self.c.execute("SELECT customer FROM customer;")
                except:
                    self.error_message('Not A CTS200 Database File\nConfiguration NOT updated')
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
   # os.chdir('/home/econnect/cts200_validator')
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
