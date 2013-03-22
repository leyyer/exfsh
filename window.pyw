from Tkinter import *
from ttk import *
from disk import *
import extfs
from commands import *
from ScrolledText import ScrolledText

class Widget(Frame):
    def __init__(self, master):
        self.builtins = {
                       'ls': fs_ls,
                       'copy': fs_copy,
                       'help': self.__help,
                       'clear': self.__clear
            }
        self.disk = None
        self.parts = []
        self.extfs = None
        self.master = master
        self.box_value = StringVar()
        self.main_window()
        self.create_menu()
    def __help(self, a, b):
        cmds = "commands:\n"
        k = self.builtins.keys()
        cmds += '\n'.join(k)
        self.text.insert(END, cmds)
    def __clear(self, a, b):
        self.text.delete('1.0', END)
    def create_menu(self):
        self.menu = Menu(self.master)
        self.master.config(menu = self.menu)
        self.filemenu = Menu(self.menu)
        self.menu.add_cascade(label="File", menu = self.filemenu)
        self.filemenu.add_command(label="Exit", command = self.__file_exit)
        self.helpmenu = Menu(self.menu)
        self.menu.add_cascade(label="Help", menu=self.helpmenu)
        self.helpmenu.add_command(label="About")
    def __file_exit(self):
        self.master.quit()
    def main_window(self):
        self.combo_label = Label(self.master, text="Driver")
        self.combo_label.grid(column=0,row=0,sticky=W)
        self.box = Combobox(self.master, textvariable=self.box_value,state = 'readonly')
        self.box['values'] = (r'PhysicalDrive0', r'PhysicalDrive1')
        self.box.current(0)
        self.box.grid(column=1,row=0)
        self.box.bind("<<ComboboxSelected>>", self.__driver_callback)
        
        self.partition_label = Label(self.master, text="Partitions")
        self.partition_label.grid(column=2,row=0,sticky=W)
        self.partition_combo = Combobox(self.master, state='readonly')
        self.partition_combo.grid(row=0,column=3)
        self.partition_combo.bind("<<ComboboxSelected>>", self.__part_callback)
        
        self.text = ScrolledText(self.master)
        self.text.grid(row=2,columnspan=4,sticky=S)
        
        Label(self.master, text="command: ").grid(row=3, sticky=W)
        self.cmdline = Entry(self.master)
        self.cmdline.grid(row=3,columnspan=3)
        self.cmdline.bind("<Return>", self.__cmdline_callback)
    def __cmdline_callback(self, event):    
        cmd = self.cmdline.get()
        self.cmdline.delete(0, END)
#        if not self.extfs: return
        cmds = cmd.split()
        args = "".join(cmds[1:])
        try:
            f = self.builtins[cmds[0]]
            s = f(self.extfs, args)
            if s : self.text.insert(END, s)
        except (KeyError,IndexError, extfs.EntryNotFound):
            self.text.insert(END, "execute: " + cmd + " failed!\n")
    def __part_callback(self, event):
        value = self.partition_combo.get().split()
        idx = int(value[1]) - 1
        sb = extfs.ExtSuperblock()
        r = sb.probe(self.parts[idx])
        if not r: 
            self.text.insert(END, "unknown filesystem type\n")
            return
        self.extfs = extfs.ExtFs(self.parts[idx], sb)
        self.text.insert(END, "partion %d is ext2 filesystem\n" % (idx + 1))
            
    def __driver_callback(self, event):
        if self.disk:
            self.disk.close
            self.disk = None
            self.parts = []
            self.extfs = None
        self.disk = Disk('\\\\.\\' +self.box_value.get())
        p = self.disk.get_partitions()
        part_values = []
        part_descr = self.box_value.get() + ":\n"
        for idx in range(len(p)):
            value = "partition %d" % (idx + 1)
            descr = "status: 0x%02x\ttype: %d\toffset: 0x%08x\tlength: 0x%08x\n" % (p[idx].status, p[idx].type, p[idx].offset, p[idx].length)
            part_descr += value + "> " + descr
            part_values.append(value)
        self.partition_combo['values'] = part_values
        self.partition_combo.current(0)
        self.text.insert(END, part_descr)
        self.parts = p

if __name__ == '__main__':
    root = Tk()
    root.title("exfsh")
    w = Widget(root)
    root.mainloop()
