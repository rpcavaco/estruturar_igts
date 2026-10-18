
import customtkinter as ctk


from cfg import CONCELHOS

class BaseFrame(ctk.CTkFrame):
    def __init__(self, master, title):
        super().__init__(master)
        self.title_str = title
        self.grid_columnconfigure(0, weight=1)

        self.title = ctk.CTkLabel(self, text=self.title_str, fg_color="gray30", corner_radius=6)
        self.title.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="ew")

class ConcelhosFrame(BaseFrame):
    def __init__(self, master, title):
        super().__init__(master, title)

        choices_concelhos = ['<escolha concelho>'] 
        choices_concelhos.extend(CONCELHOS.keys())

        self.choice_concelhos = ctk.CTkComboBox(self, width=200, values=choices_concelhos, command=self.choice_concelhos_callback)
        self.choice_concelhos.grid(row=1, column=0, padx=10, pady=(10, 0), sticky="w")

    def choice_concelhos_callback(self, choice):
        app = self.winfo_toplevel()
        app.choice_concelhos_callback(choice)


class OpsFrame(BaseFrame):
    def __init__(self, master, title):
        super().__init__(master, title)

        operacoes = {
            "estrut_regl": ("Estruturar", self.estrut_regl_callback),
            "recon_elems_regl": ("Reconhecer elementos", self.recon_elems_regl_callback),
            "resolver_pos_regl": ("Resolver POS em falta", self.resolver_pos_regl_callback),
            "match_facil_regl": ("Matches fáceis POS", self.match_facil_regl_callback)
        }

        self.op_buttons = {}

        for i, item in enumerate(operacoes.items()):
            k, v = item
            caption, callb_func = v
            self.op_buttons[k] = ctk.CTkButton(self, width=200, text=caption, command=callb_func)
            self.op_buttons[k].grid(row=i+1, column=0, padx=30, pady=(10, 0), sticky="w")

    def estrut_regl_callback(self):
        app = self.winfo_toplevel()
        app.exec_estruturarregl_callback()

    def recon_elems_regl_callback(self):
        print("recon_elems_regl_callback")

    def resolver_pos_regl_callback(self):
        print("resolver_pos_regl_callback")

    def match_facil_regl_callback(self):
        print("match_facil_regl_callback")


class WarningPopup(ctk.CTkToplevel):
    def __init__(self, master, message):
        super().__init__(master)
        self.title("Atenção")
        self.geometry("320x140")
        self.resizable(False, False)
        self.transient(master)              # stay on top of parent
        ctk.CTkLabel(self, text="⚠ " + message, wraplength=280).pack(pady=20, padx=20)
        ctk.CTkButton(self, text="OK", command=self.destroy).pack()
        self.after(100, self.grab_set)      # make modal (delay avoids a CTk timing issue)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Estruturar IGTs")
        self.geometry("480x400")
        self.minsize(480, 400)
        self.maxsize(481, 401)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.concelho_escolhido = None

        # Frame 'concelhos'

        self.concelhos_frame = ConcelhosFrame(self, "Concelhos")
        self.concelhos_frame.grid(row=0, column=0, padx=10, pady=(10,0), sticky="nsw")

        # Frame 'operações'

        self.ops_frame = OpsFrame(self, "Operações regulamento")
        self.ops_frame.grid(row=0, column=1, padx=(0, 10), pady=(10,0), sticky="ns")


        self.exit_button = ctk.CTkButton(self, text="Sair", command=self.exit_button_callback)
        self.exit_button.grid(row=3, column=1, padx=10, pady=10, sticky="e")

        self.maxsize(480, 400)

    def choice_concelhos_callback(self, choice):
        self.concelho_escolhido = choice

    def exec_estruturarregl_callback(self):
        if self.concelho_escolhido is None:
            WarningPopup(app, "Necessário escolher um concelho primeiro")


    def exit_button_callback(self):
        self.destroy()

ctk.set_appearance_mode("dark")      # "dark" / "light" / "system"
ctk.set_default_color_theme("blue")

app = App()
app.after(10, lambda: app.resizable(False, False))
app.mainloop()