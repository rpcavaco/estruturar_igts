
import os
import customtkinter as ctk


from .cfg import CONCELHOS

from src.processar_regulamento import genfiles_regulamento
from src.reconhecer_elementos_regulamento import reconhecer, resolver_pos, matches_faceis, obter_lista_plantas

TOKENS_REGULAMENTO = "tokens_regulamento.json"

def get_dados_folder():
    ret = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'dados')
    assert os.path.exists(ret), f"pasta 'dados' não existe em '{ret}'"
    return ret

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

        self.choice_concelhos = ctk.CTkComboBox(self, width=250, values=choices_concelhos, command=self.choice_concelhos_callback)
        self.choice_concelhos.grid(row=1, column=0, padx=10, pady=(10, 0), sticky="w")

    def choice_concelhos_callback(self, choice):
        app = self.winfo_toplevel()
        app.choice_concelhos_callback(choice)


class VersoesFrame(BaseFrame):
    def __init__(self, master, title):
        super().__init__(master, title)

        self.choices_versoes_vals = ['<aguarda concelho>'] 

        self.choice_versoes = ctk.CTkComboBox(self, width=250, values=self.choices_versoes_vals, command=self.choice_versoes_callback)
        self.choice_versoes.grid(row=1, column=0, padx=10, pady=(10, 0), sticky="w")

    def set_versoes(self, versoes):
        del self.choices_versoes_vals[:]
        self.choices_versoes_vals.append('<escolher versão>')
        for versao in versoes:
            if not versao in self.choices_versoes_vals:
                self.choices_versoes_vals.append(versao)

    def refresh_combo_versoes(self):
        self.choice_versoes.configure(values=self.choices_versoes_vals)    # updates the dropdown list
        self.choice_versoes.set(self.choices_versoes_vals[0] if len(self.choices_versoes_vals) > 0 else "")  # updates the displayed text

    def choice_versoes_callback(self, choice):
        app = self.winfo_toplevel()
        app.choice_versoes_callback(choice)


class OpsFrame(BaseFrame):
    def __init__(self, master, title):
        super().__init__(master, title)

        operacoes = {
            "estrut_regl": ("Estruturar", self.estrut_regl_callback),
            "recon_elems_regl": ("Reconhecer elementos", self.recon_elems_regl_callback),
            "resolver_pos_regl": ("Resolver POS em falta", self.resolver_pos_regl_callback),
            "match_facil_regl": ("Matches fáceis POS", self.match_facil_regl_callback),
            "obter_lista_plantas": ("Obter lista de plantas", self.obter_lista_plantas_callback)
        }

        self.op_buttons = {}

        for i, item in enumerate(operacoes.items()):
            k, v = item
            caption, callb_func = v
            self.op_buttons[k] = ctk.CTkButton(self, width=200, text=caption, command=callb_func)
            self.op_buttons[k].grid(row=i+2, column=0, padx=30, pady=(10, 0), sticky="w")

    def estrut_regl_callback(self):
        app = self.winfo_toplevel()
        app.exec_estruturarregl_callback()

    def recon_elems_regl_callback(self):
        app = self.winfo_toplevel()
        app.exec_recon_elems_regl_callback()

    def resolver_pos_regl_callback(self):
        app = self.winfo_toplevel()
        app.exec_resolver_pos_regl_callback()

    def match_facil_regl_callback(self):
        app = self.winfo_toplevel()
        app.exec_match_facil_regl_callback()

    def obter_lista_plantas_callback(self):
        app = self.winfo_toplevel()
        app.exec_obter_lista_plantas_callback()

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

class InfoPopup(ctk.CTkToplevel):
    def __init__(self, master, message):
        super().__init__(master)
        self.title("Informação")
        self.geometry("320x140")
        self.resizable(False, False)
        self.transient(master)              # stay on top of parent
        ctk.CTkLabel(self, text=message, wraplength=280).pack(pady=20, padx=20)
        ctk.CTkButton(self, text="OK", command=self.destroy).pack()
        self.after(100, self.grab_set)      # make modal (delay avoids a CTk timing issue)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Regulamento PDM")
        self.geometry("810x400")
        self.minsize(810, 400)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.concelho_escolhido = None
        self.versao_escolhida = None

        # Frame 'concelhos'

        self.concelhos_frame = ConcelhosFrame(self, "Concelhos")
        self.concelhos_frame.grid(row=0, column=0, padx=10, pady=(10,0), sticky="nsw")

       # Frame 'versoes'

        self.versoes_frame = VersoesFrame(self, "Versões")
        self.versoes_frame.grid(row=0, column=1, padx=(0, 10), pady=(10,0), sticky="nsw")

        # Frame 'operações'

        self.ops_frame = OpsFrame(self, "Operações regulamento")
        self.ops_frame.grid(row=0, column=2, padx=(0, 10), pady=(10,0), sticky="ns")


        self.exit_button = ctk.CTkButton(self, text="Sair", command=self.exit_button_callback)
        self.exit_button.grid(row=3, column=2, padx=10, pady=10, sticky="e")

        self.maxsize(810, 400)

    def choice_concelhos_callback(self, choice):
        self.concelho_escolhido = choice
        self.versoes_frame.set_versoes(CONCELHOS[self.concelho_escolhido]["versoes"].keys())
        self.versoes_frame.refresh_combo_versoes()

    def choice_versoes_callback(self, choice):
        self.versao_escolhida = choice

    def exec_estruturarregl_callback(self):
        if self.concelho_escolhido is None:
            WarningPopup(app, "Necessário escolher um concelho primeiro")
        elif self.versao_escolhida is None:
            WarningPopup(app, "Necessário escolher uma versão primeiro")
        else:
            folder_dados = get_dados_folder()
            pasta_concelho = CONCELHOS[self.concelho_escolhido]["pasta"]
            cfgs = CONCELHOS[self.concelho_escolhido]["versoes"][self.versao_escolhida]
            tipo_numeracao_alineas = cfgs["tipo_numeracao"]
            path = os.path.join(folder_dados, 'PDM', pasta_concelho, self.versao_escolhida)
            if "lim_genfiles_regulamento" in cfgs.keys():
                lim_genfiles_regulamento = cfgs["lim_genfiles_regulamento"]
            else:
                lim_genfiles_regulamento = 0
            # print("lim_genfiles_regulamento:", lim_genfiles_regulamento)
            genfiles_regulamento(path, tipo_numeracao_alineas, limite=lim_genfiles_regulamento)
            InfoPopup(app, "Gerados ficheiros extraídos do Regulamento")

    def exec_recon_elems_regl_callback(self):
        if self.concelho_escolhido is None:
            WarningPopup(app, "Necessário escolher um concelho primeiro")
        elif self.versao_escolhida is None:
            WarningPopup(app, "Necessário escolher uma versão primeiro")
        else:
            folder_dados = get_dados_folder()
            pasta_concelho = CONCELHOS[self.concelho_escolhido]["pasta"]
            path = os.path.join(folder_dados, 'PDM', pasta_concelho, self.versao_escolhida)
            reconhecer(path, TOKENS_REGULAMENTO, limite=0)
            InfoPopup(app, f"Gerado ficheiro de tokens ({TOKENS_REGULAMENTO}) extraídos do Regulamento")

    def exec_resolver_pos_regl_callback(self):
        if self.concelho_escolhido is None:
            WarningPopup(app, "Necessário escolher um concelho primeiro")
        elif self.versao_escolhida is None:
            WarningPopup(app, "Necessário escolher uma versão primeiro")
        else:
            folder_dados = get_dados_folder()
            pasta_concelho = CONCELHOS[self.concelho_escolhido]["pasta"]
            path = os.path.join(folder_dados, 'PDM', pasta_concelho, self.versao_escolhida)

            lenfaltas = resolver_pos(path, TOKENS_REGULAMENTO)

            InfoPopup(app, f"Ver alterações a ficheiro upd_pos.json na pasta da versão respetiva, faltas pendentes: {lenfaltas}")

    def exec_match_facil_regl_callback(self):
        if self.concelho_escolhido is None:
            WarningPopup(app, "Necessário escolher um concelho primeiro")
        elif self.versao_escolhida is None:
            WarningPopup(app, "Necessário escolher uma versão primeiro")
        else:
            folder_dados = get_dados_folder()
            pasta_concelho = CONCELHOS[self.concelho_escolhido]["pasta"]
            path = os.path.join(folder_dados, 'PDM', pasta_concelho, self.versao_escolhida)

            faltas_plurais, faltas_lhe_se, len_faltas = matches_faceis(path, TOKENS_REGULAMENTO, 'matches_faceis.json')

            InfoPopup(app, f"Ver alterações a ficheiro matches_faceis.json na pasta da versão respetiva, faltas pendentes, plurais: {faltas_plurais}, -lhe/-se:{faltas_lhe_se}, total faltas:{len_faltas}")

    def exec_obter_lista_plantas_callback(self):
        if self.concelho_escolhido is None:
            WarningPopup(app, "Necessário escolher um concelho primeiro")
        elif self.versao_escolhida is None:
            WarningPopup(app, "Necessário escolher uma versão primeiro")
        else:
            folder_dados = get_dados_folder()
            pasta_concelho = CONCELHOS[self.concelho_escolhido]["pasta"]
            path = os.path.join(folder_dados, 'PDM', pasta_concelho, self.versao_escolhida)
            path_catalogo_objetos = os.path.join(folder_dados, 'PDM', 'CatalogoObjetos')

            tokens_plantas_primnivel_path = os.path.join(path_catalogo_objetos, 'plantas_primeiro_nivel_tokens.json')

            tr_file = os.path.join(path, 'output', TOKENS_REGULAMENTO)
            if not os.path.exists(tr_file):
                WarningPopup(app, "Não existe ficheiro de tokens de regulamento, tem de executar 'Reconhecer elementos' primeiro")
            else:
                obter_lista_plantas(path, tokens_plantas_primnivel_path, TOKENS_REGULAMENTO, 'lista_plantas.json', strict=True)

            InfoPopup(app, f"OK")





    def exit_button_callback(self):
        self.destroy()

ctk.set_appearance_mode("dark")      # "dark" / "light" / "system"
ctk.set_default_color_theme("blue")

app = App()
app.after(10, lambda: app.resizable(False, False))
app.mainloop()