import os
import customtkinter as ctk

from src.processar_geometria import ler_layers_logicas, elementos_layers_logicas, transferir_para_geopkg
from src.elementos import EmptyLayersListError

from .cfg import CONCELHOS



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
		self.choice_versoes.configure(values=self.choices_versoes_vals)	# updates the dropdown list
		self.choice_versoes.set(self.choices_versoes_vals[0] if len(self.choices_versoes_vals) > 0 else "")  # updates the displayed text

	def choice_versoes_callback(self, choice):
		app = self.winfo_toplevel()
		app.choice_versoes_callback(choice)


class OpsFrame(BaseFrame):
	def __init__(self, master, title):
		super().__init__(master, title)

		# Chaves abaixo são arbitrárias, servem apenas para ajudar a gerir internamente 
		#  os recursos a alocar a cada operação
		operacoes = {
			"process_files": ("Ler layers de shapefiles", self.read_layers_callback),
			"logic_layers": ("Layers lógicas", self.logic_layers_callback),
			"tokenize_logic_layers": ("Separar elementos layers", self.tokenizelogiclayers_callback)
		}

		self.op_buttons = {}

		for i, item in enumerate(operacoes.items()):
			k, v = item
			caption, callb_func = v
			self.op_buttons[k] = ctk.CTkButton(self, width=200, text=caption, command=callb_func)
			self.op_buttons[k].grid(row=i+2, column=0, padx=30, pady=(10, 0), sticky="w")

	def read_layers_callback(self):
		app = self.winfo_toplevel()
		app.exec_readlayers_callback()

	def logic_layers_callback(self):
		app = self.winfo_toplevel()
		app.exec_logiclayers_callback()

	def tokenizelogiclayers_callback(self):
		app = self.winfo_toplevel()
		app.exec_tokenizelogiclayers_callback()

class WarningPopup(ctk.CTkToplevel):
	def __init__(self, master, message):
		super().__init__(master)
		self.title("Atenção")
		self.geometry("320x140")
		self.resizable(False, False)
		self.transient(master)			  # stay on top of parent
		ctk.CTkLabel(self, text="⚠ " + message, wraplength=280).pack(pady=20, padx=20)
		ctk.CTkButton(self, text="OK", command=self.destroy).pack()
		self.after(100, self.grab_set)	  # make modal (delay avoids a CTk timing issue)

class InfoPopup(ctk.CTkToplevel):
	def __init__(self, master, message):
		super().__init__(master)
		self.title("Informação")
		self.geometry("320x140")
		self.resizable(False, False)
		self.transient(master)			  # stay on top of parent
		ctk.CTkLabel(self, text=message, wraplength=280).pack(pady=20, padx=20)
		ctk.CTkButton(self, text="OK", command=self.destroy).pack()
		self.after(100, self.grab_set)	  # make modal (delay avoids a CTk timing issue)

# class InfoPopupList(ctk.CTkToplevel):
# 	def __init__(self, master, message_list):
# 		super().__init__(master)
# 		self.title("Informação")
# 		self.geometry("320x140")
# 		self.resizable(False, False)
# 		self.transient(master)			  # stay on top of parent
# 		#ctk.CTkLabel(self, text=message, wraplength=280).pack(pady=20, padx=20)
# 		textbox = ctk.CTkTextbox(self)
# 		textbox.pack(pady=20, padx=20)
# 		ctk.CTkButton(self, text="OK", command=self.destroy).pack()
# 		self.after(100, self.grab_set)	  # make modal (delay avoids a CTk timing issue)

# 		for mi, msg in enumerate(message_list):
# 			textbox.insert(f"{mi}.0", msg)

class InfoPopupListOld(ctk.CTkToplevel):
	def __init__(self, master, message_list):
		super().__init__(master)
		self.title("Informação")
		self.geometry("320x140")
		self.resizable(False, False)
		self.transient(master)

		# Create textbox and button
		self.textbox = ctk.CTkTextbox(self)
		self.textbox.pack(pady=20, padx=20, fill='both', expand=True)  # Fill available space

		# Add scrollbar to handle long content
		self.textbox.configure(state="normal")
		for mi, msg in enumerate(message_list):
			self.textbox.insert(f"{mi}.0", msg + "\n")  # Add newline after each item
		self.textbox.configure(state="disabled")  # Make textbox read-only

		ok_button = ctk.CTkButton(self, text="OK", command=self.destroy)
		ok_button.pack(pady=(0, 10), padx=20)  # Adjust padding to ensure visibility

		self.after(100, lambda: self.grab_set())  # Make modal after initial render

import customtkinter as ctk


class InfoPopupList(ctk.CTkToplevel):
	def __init__(self, master, message_list):
		super().__init__(master)
		self.title("Informação")
		self.geometry("650x450")
		self.resizable(True, True)
		self.transient(master)

		# Pack the button FIRST so its space is reserved at the bottom
		ok_button = ctk.CTkButton(self, text="OK", command=self.destroy)
		ok_button.pack(side="bottom", pady=(0, 15), padx=20)

		# Textbox fills whatever space is left
		self.textbox = ctk.CTkTextbox(self)
		self.textbox.pack(side="top", pady=(20, 10), padx=20, fill="both", expand=True)

		self.textbox.configure(state="normal")
		for msg in message_list:
			self.textbox.insert("end", msg + "\n")
		self.textbox.configure(state="disabled")  # read-only

		# Make modal after the window is rendered, and make sure it's on top
		self.after(100, self._make_modal)

	def _make_modal(self):
		self.lift()
		self.focus_force()
		self.grab_set()


class App(ctk.CTk):
	def __init__(self):
		super().__init__()

		self.title("Geometria PDM")
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

		self.ops_frame = OpsFrame(self, "Operações geometria")
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

	def exec_readlayers_callback(self):
		if self.concelho_escolhido is None:
			WarningPopup(app, "Necessário escolher um concelho primeiro")
		elif self.versao_escolhida is None:
			WarningPopup(app, "Necessário escolher uma versão primeiro")
		else:
			folder_dados = get_dados_folder()
			pasta_concelho = CONCELHOS[self.concelho_escolhido]["pasta"]
			cfgs = CONCELHOS[self.concelho_escolhido]["versoes"][self.versao_escolhida]
			geom_format = cfgs["geom_format"]
			geom_path = cfgs["geom_path"]

			path_versao = os.path.join(folder_dados, 'PDM', pasta_concelho, self.versao_escolhida)
			path = os.path.join(path_versao, *geom_path)
			msgs_list = []
			file_count = transferir_para_geopkg(app, path, os.path.join(path_versao, geom_path[0], "read_layers.gpkg"), geom_format, cfgs["encoding"], msgs_list)
			msgs_list.insert(0, f"Camadas detectadas, transferidas para GPKG: {file_count}")
			msgs_list.insert(1, "")
			InfoPopupList(app, msgs_list)

	def exec_logiclayers_callback(self):
		if self.concelho_escolhido is None:
			WarningPopup(app, "Necessário escolher um concelho primeiro")
		elif self.versao_escolhida is None:
			WarningPopup(app, "Necessário escolher uma versão primeiro")
		else:
			folder_dados = get_dados_folder()
			pasta_concelho = CONCELHOS[self.concelho_escolhido]["pasta"]
			cfgs = CONCELHOS[self.concelho_escolhido]["versoes"][self.versao_escolhida]
			layer_field = cfgs["layer_field"]
			geom_ext = cfgs["geom_ext"]
			geom_path = cfgs["geom_path"]

			path_versao = os.path.join(folder_dados, 'PDM', pasta_concelho, self.versao_escolhida)
			path = os.path.join(path_versao, *geom_path)
			ler_layers_logicas(path_versao, path, layer_field, geom_ext)
			InfoPopup(app, "Layers lógicas lidas para 'layers.json'")

	def exec_tokenizelogiclayers_callback(self):
		if self.concelho_escolhido is None:
			WarningPopup(app, "Necessário escolher um concelho primeiro")
		elif self.versao_escolhida is None:
			WarningPopup(app, "Necessário escolher uma versão primeiro")
		else:
			folder_dados = get_dados_folder()
			pasta_concelho = CONCELHOS[self.concelho_escolhido]["pasta"]
			path_versao = os.path.join(folder_dados, 'PDM', pasta_concelho, self.versao_escolhida)
			lyrfile_path = os.path.join(path_versao, 'output', 'layers.json')
			if not os.path.exists(lyrfile_path):
				WarningPopup(app, "Não existe ficheiro 'layers.json', necessário executar 'Layers lógicas' primeiro")
			else:
				try:
					elementos_layers_logicas(path_versao)
					InfoPopup(app, "Tokenização de layers terminada")
				except EmptyLayersListError:
					WarningPopup(app, "Necessário ler 'Layers lógicas' primeiro")

	def exit_button_callback(self):
		self.destroy()

ctk.set_appearance_mode("dark")	  # "dark" / "light" / "system"
ctk.set_default_color_theme("blue")

app = App()
app.after(10, lambda: app.resizable(False, False))
app.mainloop()