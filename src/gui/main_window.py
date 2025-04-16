import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gio, GdkPixbuf

class ERPCTMainWindow(Gtk.ApplicationWindow):
    def __init__(self, application):
        Gtk.ApplicationWindow.__init__(self, application=application)
        self.set_title("ERPCT - Enhanced Rapid Password Cracking Tool")
        self.set_default_size(1200, 800)
        self.set_position(Gtk.WindowPosition.CENTER)
        
        # Main layout
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(self.main_box)
        
        # Header bar with logo
        self.header = Gtk.HeaderBar()
        self.header.set_show_close_button(True)
        self.header.props.title = "ERPCT"
        self.set_titlebar(self.header)
        
        # Menu button
        menu_button = Gtk.MenuButton()
        menu_button.set_tooltip_text("Menu")
        menu_icon = Gtk.Image.new_from_icon_name("open-menu-symbolic", Gtk.IconSize.BUTTON)
        menu_button.add(menu_icon)
        self.header.pack_end(menu_button)
        
        # Create the main interface components
        self.create_notebook()
        
        # Show all widgets
        self.show_all()
    
    def create_notebook(self):
        notebook = Gtk.Notebook()
        self.main_box.pack_start(notebook, True, True, 0)
        
        # Target Configuration tab
        target_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        target_page.set_border_width(10)
        notebook.append_page(target_page, Gtk.Label(label="Target"))
        
        # Attack Configuration tab
        attack_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        attack_page.set_border_width(10)
        notebook.append_page(attack_page, Gtk.Label(label="Attack"))
        
        # Wordlist Manager tab
        wordlist_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        wordlist_page.set_border_width(10)
        notebook.append_page(wordlist_page, Gtk.Label(label="Wordlists"))
        
        # Execution tab
        execution_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        execution_page.set_border_width(10)
        notebook.append_page(execution_page, Gtk.Label(label="Execution"))
        
        # Results tab
        results_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        results_page.set_border_width(10)
        notebook.append_page(results_page, Gtk.Label(label="Results"))
        
        # Settings tab
        settings_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        settings_page.set_border_width(10)
        notebook.append_page(settings_page, Gtk.Label(label="Settings"))

class ERPCTApplication(Gtk.Application):
    def __init__(self):
        Gtk.Application.__init__(self,
                                application_id="com.example.erpct",
                                flags=Gio.ApplicationFlags.FLAGS_NONE)
        
    def do_activate(self):
        win = ERPCTMainWindow(self)
        win.show_all()
    
    def do_startup(self):
        Gtk.Application.do_startup(self)

def main():
    app = ERPCTApplication()
    return app.run(None)

if __name__ == "__main__":
    main()
