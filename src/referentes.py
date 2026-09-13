
import os
import json
import re

# from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Type
from typing import Dict, Type

from nlp import injetarTemposVerbais, genTokensList #, setTokenRepr, genPOS, POSNotFound, presenca_nomes_proprios, presenca_datas

PT_ALPHA_CHAR_PATT = "[a-zàáâãçèéêìíîòóôõùúü]"
PT_INV_ALPHA_CHAR_PATT = "[^a-zàáâãçèéêìíîòóôõùúü]"

class ReconhecimentoReferentes(object):

	def __init__(self):

		self.part_of_speech_dict = None
		with open(os.path.join('setup', 'part_of_speech.json'), 'r', encoding='utf-8') as fp: 
			self.part_of_speech_dict = json.load(fp)		
			injetarTemposVerbais(self.part_of_speech_dict)

		self.substituicoes = None
		with open(os.path.join('setup', 'substituicoes.json'), 'r', encoding='utf-8') as fp: 
			self.substituicoes = json.load(fp)	

		self.pos_admissiveis = None
		with open(os.path.join('setup', 'pos_admissiveis.json'), 'r', encoding='utf-8') as fp: 
			self.pos_admissiveis = json.load(fp)	

		self.sufixos_plurais = None
		with open(os.path.join('setup', 'sufixos_plurais,json'), 'r', encoding='utf-8') as fp: 
			self.sufixos_plurais = json.load(fp)

		self.remover_para_comparabilidade = set([])
		check_list = set(['artigo', 'preposicao', 'contracao', 'conjuncao'])
		for wrd in self.part_of_speech_dict.keys():
			if len(set(self.part_of_speech_dict[wrd]).intersection(check_list)) > 0:
				self.remover_para_comparabilidade.add(wrd)

		self.pos_admissiveis_final = []
		for k in self.pos_admissiveis["antecedentes_admissiveis"].keys():
			if not k in self.pos_admissiveis["proibidos_final"]:
				self.pos_admissiveis_final.append(k)

		self.palavras_remover = self.pos_admissiveis["palavras_remover"]

		self.inicios_admissiveis = set(self.pos_admissiveis["antecedentes_admissiveis"].keys())

	def reconhecerEmJanela(self, p_janela: str) -> Dict[str, Type]:

		ret = {}

		# Limpeza de artefactos prejudiciais ##################################

		in_window_text = p_janela.replace(r"\n", " ")  				## remover caracteres newline
		# in_window_text = re.sub(r"http[s]?://[\S]+", " ", in_window_text)   ## remover URLs
		in_window_text = re.sub(fr"({PT_ALPHA_CHAR_PATT})/({PT_ALPHA_CHAR_PATT})", r"\1 / \2", in_window_text)   ## tornar barras separadoras contíguas a texto em barras isoladas
		in_window_text = in_window_text.replace("e/ou", "ou").replace("e / ou", "ou")

		cleantext = in_window_text

		ret['entry_token_lists'] = genTokensList(cleantext)

		return ret