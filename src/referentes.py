
import os
import json
import re

# from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Type
from typing import Dict, Type, Any, List
from copy import copy

from nlp import injetarTemposVerbais, genTokensList, genPOS, POSNotFound #, presenca_nomes_proprios, presenca_datas
from dict_list_manager import DictListManager

PT_ALPHA_CHAR_PATT = "[a-zàáâãçèéêìíîòóôõùúü]"
PT_INV_ALPHA_CHAR_PATT = "[^a-zàáâãçèéêìíîòóôõùúü]"

def set_token_repr(p_tkn: Dict[str, Any]) -> None:
	if 'lower' in p_tkn.keys():
		p_tkn.update(repr=p_tkn['lower'])
	elif 'string' in p_tkn.keys():
		p_tkn.update(repr=p_tkn['string'])

def buildRepr(p_list: 'DictListManager') -> None:
	p_list.walk(
		lambda item: set_token_repr(item)
	)

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

		self.nomes = []
		self.nomes_compostos = []

		with open(os.path.join('setup', 'nomes_proprios.json'), 'r', encoding='utf-8') as fp: 
			nomes = json.load(fp)

		assert len(nomes) > 0

		for nome in nomes:
			nome_splits = [t.lower() for t in nome.split()]	
			if len(nome_splits) == 0:
				continue
			if len(nome_splits) == 1:
				self.nomes.append(nome_splits[0])
			else:
				self.nomes_compostos.append(copy(nome_splits))


		self.palavras_remover = self.pos_admissiveis["palavras_remover"]

		self.inicios_admissiveis = set(self.pos_admissiveis["antecedentes_admissiveis"].keys())


	def marcarSiglas(self, p_list: 'DictListManager', out_siglas: List[str]) -> None:

		del out_siglas[:]

		def add_sigla(p_out_siglas, p_str):
			if not p_str in p_out_siglas:
				p_out_siglas.append(p_str)

		p_list.walk(
			lambda item: item.update(pos=['sigla']),
			predicate=lambda item: 'repr' in item.keys() and item['repr'] in self.substituicoes.keys(),
			afterfunc=lambda item: add_sigla(out_siglas, item['repr'])
		)

	def buildPOS(self, p_ret: Dict[str, Any], out_siglas: List[str]) -> None:

		token_list = p_ret['tokens_list']
		this_out_siglas = []
		del out_siglas[:]

		for idx, grp_tokens in token_list.iterateGroups(group_size=2, prev_is_null=True):
			
			if len(grp_tokens) < 2:
				continue

			prev_tkn, tkn = grp_tokens

			do_continue = False
			for k in ('construct', 'numero'):
				if k in tkn.keys():
					do_continue = True
					break

			if do_continue:
				continue

			if prev_tkn is None:
				the_prev_tkn = None
			else:
				for k in ('construct', 'numero'):
					if k in prev_tkn.keys():
						the_prev_tkn = None
						break
		
			try:
				genPOS(self.part_of_speech_dict, self.nomes, self.substituicoes.keys(), tkn, prev_tkn=the_prev_tkn)	
				token_list.validate(tkn)
			except POSNotFound as pnf:
				p_ret.setdefault('faltas', [])
				p_ret['faltas'].append(str(pnf))

	def reconhecerURLs(self, p_list: 'DictListManager') -> None:

		idxs_lists = []
		for idxs_list in p_list.iterNextContiguousConstructElements(
				lambda item: 'lower' in item.keys() and (item["lower"].startswith("http:") or item["lower"].startswith("https:"))
			):		
				idxs_lists.append(idxs_list)

		for idxs_list_1 in reversed(idxs_lists):
			p_list.buildConstruct(idxs_list_1, "URL")

	def reconhecerNomes(self, p_list: 'DictListManager'):

		idxs_lists = []
		for idx, indices in p_list.iterateMatches(self.nomes_compostos):
			idxs_lists.append(idxs_list)

		for idxs_list_1 in reversed(idxs_lists):
			p_list.buildConstruct(idxs_list_1, "nome_ou_designacao")

		seps = ['da', 'do', 'de', 'e', 'em', 'na', 'no']

		idxs_lists = []
		for idxs_list in p_list.iterNextContiguousConstructElements(
				lambda item: 'repr' in item.keys() and (item["repr"] in self.nomes or item["repr"] in seps or item["ok"][0].isupper())
				# testlist=["vítor", "ramalho"]
			):

			# Se não existirem nomes nos elementos selecionados (podem ser outras palavras em maiúsculas ou separadores), continuar loop
			nomes_idx = [idx for idx in idxs_list if 'repr' in p_list[idx].keys() and p_list[idx]['repr'] in self.nomes]
			if len(nomes_idx) == 0:
				continue

			while len(idxs_list) > 0 and p_list[idxs_list[0]]['repr'] in seps:
				idxs_list.pop(0)
			if len(idxs_list) > 0:
				idxs_lists.append(idxs_list)

		for idxs_list_2 in reversed(idxs_lists):
			p_list.buildConstruct(idxs_list_2, "nome_ou_designacao")

	def reconhecerDatas(self, p_list: 'DictListManager') -> None:

		meses = [
			"janeiro", "fevereiro", "março", "abril", "maio", "junho",
			"julho", "agosto", "setembro", "outubro", "novembro", "dezembro"
		]

		idxs_lists = []
		for idx, grp_tokens in p_list.iterateGroups(group_size=5, prev_is_null=False):	
			if len(grp_tokens) < 5:
				continue
			atkn, btkn, ctkn, dtkn, etkn = grp_tokens	
			if 'numero' in atkn.keys() and 'repr' in btkn.keys() and 'repr' in ctkn.keys() and 'repr' in dtkn.keys() and 'numero' in etkn.keys():
				if atkn['numero'] == 'int' and btkn['repr'] == 'de' and ctkn['repr'] in meses and dtkn['repr'] == 'de' and etkn['numero'] == 'int':
					idxs_lists.append([j+idx for j in range(5)])

		for idxs_list_1 in reversed(idxs_lists):
			p_list.buildConstruct(idxs_list_1, "data")

		del idxs_lists[:]
		for idx, grp_tokens in p_list.iterateGroups(group_size=3, prev_is_null=False):	
			if len(grp_tokens) < 3:
				continue
			atkn, btkn, ctkn = grp_tokens	
			if 'repr' in atkn.keys() and 'repr' in btkn.keys() and 'numero' in ctkn.keys():
				if atkn['repr'] in meses and btkn['repr'] == 'de' and ctkn['numero'] == 'int':
					idxs_lists.append([j+idx for j in range(3)])

		for idxs_list_2 in reversed(idxs_lists):
			p_list.buildConstruct(idxs_list_2, "data_mes")

	def reconhecerExpansaoSiglas(self, p_list: 'DictListManager', p_siglas_list) -> None:

		if len(p_siglas_list) == 0:
			return

		for sigla in p_siglas_list:

			words_subst = self.substituicoes[sigla].split()


			idxs_lists = []
			for idx, indices in p_list.iterateMatches([words_subst]):
				idxs_lists.append(indices)

			for idxs_list_1 in reversed(idxs_lists):
				p_list.buildConstruct(idxs_list_1, "nome_ou_designacao", adic_attribs=[('sigla', sigla)])


	def reconhecerEmJanela(self, p_janela: str) -> Dict[str, Type]:

		ret = {}

		# Limpeza de artefactos prejudiciais ##################################

		in_window_text = p_janela.replace(r"\n", " ")  				## remover caracteres newline
		# in_window_text = re.sub(r"http[s]?://[\S]+", " ", in_window_text)   ## remover URLs
		in_window_text = re.sub(fr"({PT_ALPHA_CHAR_PATT})/({PT_ALPHA_CHAR_PATT})", r"\1 / \2", in_window_text)   ## tornar barras separadoras contíguas a texto em barras isoladas
		in_window_text = in_window_text.replace("e/ou", "ou").replace("e / ou", "ou")

		cleantext = in_window_text

		ret['tokens_list'] = genTokensList(cleantext)

		# Definir 'repr' onde possível ########################################

		buildRepr(ret['tokens_list'])

		# Reconhecer construções (q precisam de 'repr' mas não de 'pos') ######

		self.reconhecerURLs(ret['tokens_list'])
		self.reconhecerDatas(ret['tokens_list'])

		# Reconhecer construções nome ou designação ###########################

		self.reconhecerNomes(ret['tokens_list'])

		# Marcasr siglas e nomes ou designações de expansão de sigla  #########

		out_siglas = []
		self.marcarSiglas(ret['tokens_list'], out_siglas)	
		self.reconhecerExpansaoSiglas(ret['tokens_list'], out_siglas)

		# Obter POS ###########################################################

		# pos=['sigla'] já se encontram preenchidos

		# 'sigla' tem de ser equiparado a 'nome', bem como certos constructs, na atribuição de POSS

		self.buildPOS(ret, out_siglas)

		




		return ret