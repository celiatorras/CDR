import queue
import sys
import threading
import gi
import json
import requests
#from nfc import Rfid
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib

import http.client

class CourseManager(Gtk.Window):
    def __init__(self):
        super().__init__()
        self.set_default_size(400, 200)
        self.user = None
        self.uid = None
        self.table = None
        self.conn = http.client.HTTPConnection("localhost", 8080)
        self.entry = None
        self.lock = threading.Lock()
        self.liststore = None
        self.inactivity_timeout = 15  # segon
        self.input_queue = queue.Queue()
        
        self.login_event = threading.Event()
        self.login_event.set()
        self.read_user_input()
        
        # Configurar la interfaz gráfica
        self.box = Gtk.VBox(spacing=6)
        self.label = Gtk.Label()
        self.label.set_text("Acerca la tarjeta")
        self.box.pack_start(self.label, True, True, 0)
        self.add(self.box)
        self.show_all()
        
        self.create_logout_button()
        self.create_entry("Introduce lo que quieras ver:")
        self.start_inactivity_timer()
        
    def start_inactivity_timer(self):
        self.inactivity_timer_id = GLib.timeout_add_seconds(self.inactivity_timeout, self.logout_thread)

    def reset_inactivity_timer(self):
        self.stop_inactivity_timer()
        self.start_inactivity_timer()

    def read_user_input(self):
        user_input = input("Enter UID: ")
        self.input_queue.put(user_input)
        self.login_event.set()
        self.login()

    def get(self, url):
        try:
            self.conn.request("GET", url)
            response = self.conn.getresponse()
            if response.status == 200:
                json_arr = response.read().decode('utf-8')  
                return json.loads(json_arr) #retornem l'objecte json
        finally:
            self.conn.close()
        
    def login(self):
        try:
            self.uid = self.input_queue.get(timeout=0.1)     #D1FDE202, 938B506
            
            data = self.get("/CriticalDesignPBE/back/index.php/students?uid={}".format(self.uid))
            if data:
                with self.lock:
                    self.user = data[0]['userName']
                    GLib.idle_add(self.update_label, "Welcome: " + self.user)
        except queue.Empty:
            pass
            
    def create_logout_button(self):
        self.outbutton = Gtk.Button(label = 'LOGOUT')
        self.box.pack_start(self.outbutton, True, True, 0)
        self.outbutton.connect("clicked", lambda button: self.logout_thread())

    def logout_thread(self):
        threading.Thread(target=self.logout).start()

    def logout(self):
        with self.lock:
            self.user = None
            self.uid = None
        if self.conn:
            self.conn.close()
        self.stop_inactivity_timer()
        self.read_user_input()

    def update_label(self, text):
        self.label.set_text(text) 
        self.show_all()

    def stop_inactivity_timer(self):
        if hasattr(self, 'inactivity_timer_id') and self.inactivity_timer_id is not None:
            GLib.source_remove(self.inactivity_timer_id)
            self.inactivity_timer_id = None

    def create_entry(self, text):
        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text(text)
        
        self.entry.connect("activate", lambda entry: self.entry_activated(entry = self.entry))
        self.box.pack_start(self.entry, True, True, 0)

    def entry_activated(self, entry):
        self.consultaThread(entry)
        self.reset_inactivity_timer()
        entry.set_text("")

    def consultaThread(self, entry):  #creem un thread per consultar el server de forma concurrent
        text = entry.get_text()
        thread1 = threading.Thread(target= self.consultarServer, args=(text, ))  #li passem el que esta escrit i el uid
        thread1.start()   # Reseteja el temporitzador quan es rep una acció de l'usuari
        
    def consultarServer(self, text):
        self.table = text
        
        self.aux = self.table.split("?") #mirem primera part de la query per saber si és marks i enviar uid
        
        if (self.aux[0]=="marks" and self.uid):
            if(len(self.aux)==1):
                self.table = self.table + "?uid=" + self.uid
        data = self.get("/CriticalDesignPBE/back/index.php/{}".format(self.table))
        self.create_table(data)
        
        self.show_all()

    def create_table(self, json_array):
        if hasattr(self, 'treeview'):
            self.treeview.destroy()

        if self.table == 'tasks':
            self.liststore = Gtk.ListStore(str, str, str)
        else:
            self.liststore = Gtk.ListStore(str, str, str, str)

        for item in json_array:
            self.liststore.append(list(item.values()))
        self.treeview = Gtk.TreeView(model=self.liststore)

        nombres_campos = set()

        for obj in json_array:
            for campo in obj:
                nombres_campos.add(campo)

        for i, column_title in enumerate(nombres_campos):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(column_title, renderer, text=i)
            self.treeview.append_column(column)

        self.box.pack_start(self.treeview, True, True, 0)

    def destroy_table(self):
        self.liststore = None
        

win = CourseManager()
win.connect("destroy", Gtk.main_quit)
Gtk.main()
