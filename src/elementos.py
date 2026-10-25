
import os
import json
import re

# from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Type
from typing import Dict, Type, Any, List, Optional
from copy import copy

from .nlp import injetarTemposVerbais, genTokensList, genPOS, POSNotFound, getNumPattern #, presenca_nomes_proprios, presenca_datas
from .dict_list_manager import DictListManager, ConstructValidationError, EmptyConstructError

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

def antecedente_compatível(
		p_prev_tkn: Dict[str, Any], 
		p_tkn: Dict[str, Any], 
		pos_admissiveis: Dict[str, List[str]]
	) -> bool | None:
	
	ret = None

	if 'pos' in p_prev_tkn.keys() and 'pos' in p_tkn.keys():
		ant_admiss = set([])
		for pos in p_tkn['pos']:
			if pos in pos_admissiveis.keys():
				ant_admiss.update(pos_admissiveis[pos])
		if len(ant_admiss) > 0:
			ret = bool(ant_admiss.intersection(p_prev_tkn['pos']))
		else:
			ret = False

	# se o antecedente não tem 'pos' definido ou este p_tkn não tem 'pos' definido ret +e None

	# if strict and ret is None:
	# 	raise AntecedenteIncompativelInconclusivoError(f"prev:'{p_prev_tkn['ok']}' este:'{p_tkn['ok']}'")

	return ret

def assocNumParts(p_list: 'DictListManager') -> None:
	r"""
	Associar partes de 'número', separadas por espaço. 
	Método criado por causa dos identificadores de estradas
	com espaços, mas permite reconhecer quaisquer padrões de 
	PATT_NUMERO que incluam espaço (\s).
	 """

	def assoc(p_prev_elems, p_chg_list, p_item):

		if len(p_prev_elems) < 1:
			p_prev_elems.append(p_item)
			return

		if not 'ok' in p_prev_elems[-1].keys() or not 'ok' in p_item.keys():
			return

		# Com espaço
		new_string = f"{p_prev_elems[-1]['ok']} {p_item['ok']}"
		if not " " in new_string.strip():
			return

		num_patt, val, string = getNumPattern(new_string.strip())
		if num_patt is None:
			# Também testar sem espaço
			new_string = f"{p_prev_elems[-1]['ok']}{p_item['ok']}"
			num_patt, val, string = getNumPattern(new_string.strip())

		if not num_patt is None:
			leng = len(p_prev_elems)
			p_chg_list.append((leng-1, leng, num_patt, val, string))

		p_prev_elems.append(p_item)

	last_elems = []
	chg_list = []

	p_list.walk(
		lambda item: assoc(last_elems, chg_list, item)
	)

	if len(chg_list) > 0:
		for idx0, idx1, num_patt, val, string in reversed(chg_list):
			p_list.remove_at(idx1)
			p_list.remove_at(idx0)
			p_list.insert(None, idx0, ok=string, numero=num_patt, valor=val, string=str(string), lower=str(string).lower())


def assocVariosTripletos(p_list: 'DictListManager') -> None:
	r"""
	Associar elementos, por exemplo, abreviaturas, compostas por dois elementos abreviados mais um separador
	 """

	def assoc(p_prev_elems, p_chg_list, p_item):

		if len(p_prev_elems) < 2:
			p_prev_elems.append(p_item)
			return

		if not 'ok' in p_prev_elems[-2].keys() or not 'lower' in p_prev_elems[-2].keys():
			p_prev_elems.append(p_item)
			return

		if not 'sep' in p_prev_elems[-1].keys() or not p_prev_elems[-1]['ok'] == '.':
			p_prev_elems.append(p_item)
			return

		if not 'ok' in p_item.keys() or not 'lower' in p_item.keys():
			p_prev_elems.append(p_item)
			return

		# Abreviaturas de santo / santa
		if p_prev_elems[-2]['lower'] == 's':
			if p_item['lower'] in ('o', 'a', 'to', 'ta', 'º', 'ª'):

				new_string = f"{p_prev_elems[-2]['ok']}{p_prev_elems[-1]['ok']}{p_item['ok']}"

				leng = len(p_prev_elems)
				p_chg_list.append((leng-1, 3, "abrev_santo", new_string))

		elif p_prev_elems[-2]['lower'] in ('dr', 'eng'):
			if p_item['lower'] in ('o', 'a', 'º', 'ª'):

				new_string = f"{p_prev_elems[-2]['ok']}{p_prev_elems[-1]['ok']}{p_item['ok']}"

				leng = len(p_prev_elems)
				p_chg_list.append((leng-1, 3, "inicial_titulo", new_string))

		p_prev_elems.append(p_item)

	last_elems = []
	chg_list = []

	p_list.walk(
		lambda item: assoc(last_elems, chg_list, item)
	)

	if len(chg_list) > 0:
		for idx, sz, tipostr, string in reversed(chg_list):
			for k in reversed(range(sz)):
				p_list.remove_at(idx+k)
			p_list.insert(None, idx, ok=string, especial=tipostr, string=str(string), lower=str(string).lower())

def assocVariosPares(p_list: 'DictListManager') -> None:
	r"""
	Associar elementos, por exemplo, abreviaturas, compostas por dois elementos um abreviado e um separador, exemplo Dr.
	 """

	def assoc(p_prev_elems, p_chg_list, p_item):

		if len(p_prev_elems) < 1:
			p_prev_elems.append(p_item)
			return

		if not 'ok' in p_prev_elems[-1].keys() or not 'lower' in p_prev_elems[-1].keys():
			p_prev_elems.append(p_item)
			return

		if not 'sep' in p_item.keys() or not p_item['ok'] == '.':
			p_prev_elems.append(p_item)
			return

		# Abreviaturas de santo / santa + DR
		if p_prev_elems[-1]['lower'] in ('s', 'sto', 'sta'):

			new_string = f"{p_prev_elems[-1]['ok']}{p_item['ok']}"

			leng = len(p_prev_elems)
			p_chg_list.append((leng-1, 2, "abrev_santo", new_string))

		elif p_prev_elems[-1]['lower'] in ('dr', 'eng'):

			new_string = f"{p_prev_elems[-1]['ok']}{p_item['ok']}"

			leng = len(p_prev_elems)
			p_chg_list.append((leng-1, 2, "inicial_titulo", new_string))

		elif p_prev_elems[-1]['lower'] in ('dec',):

			new_string = f"{p_prev_elems[-1]['ok']}{p_item['ok']}"

			leng = len(p_prev_elems)
			p_chg_list.append((leng-1, 2, None, new_string))

		p_prev_elems.append(p_item)

	last_elems = []
	chg_list = []

	p_list.walk(
		lambda item: assoc(last_elems, chg_list, item)
	)

	if len(chg_list) > 0:
		for idx, sz, tipostr, string in reversed(chg_list):
			for k in reversed(range(sz)):
				p_list.remove_at(idx+k)
			if tipostr is None:
				p_list.insert(None, idx, ok=string, string=str(string), lower=str(string).lower())
			else:
				p_list.insert(None, idx, ok=string, especial=tipostr, string=str(string), lower=str(string).lower())


def reconhecerURLs(p_list: 'DictListManager') -> None:

	idxs_list = []
	p_list.walk(
		lambda idx, item: idxs_list.append(idx),
		predicate=lambda item: 'lower' in item.keys() and (item["lower"].startswith("http:") or item["lower"].startswith("https:")),
		include_idx_as_func_param = True
	)

	for idx in reversed(idxs_list):
		p_list.buildConstruct([idx], "URL")



class Pesquisa(object):

	def __init__(self):

		src_path = os.path.dirname(os.path.abspath(__file__))

		self.sufixos_plurais = None
		with open(os.path.join(src_path, 'setup', 'sufixos_plurais,json'), 'r', encoding='utf-8') as fp: 
			self.sufixos_plurais = json.load(fp)	

	def similaridadeLists(self, p_lista_elementos_to_search: List[Dict[str, Type]], p_lista_elementos_searched: List[Dict[str, Type]]):

		base_count = 0
		base_count_relevantes = 0
		found_count = 0
		found_count_relevantes = 0

		seps = ['da', 'do', 'das', 'dos', 'de', 'e', 'em', 'na', 'no']

		for tkn_a in p_lista_elementos_to_search:

			if "repr" in tkn_a.keys():

				base_count += 1
				if not tkn_a["repr"] in seps:
					base_count_relevantes += 1

				for tkn_b in p_lista_elementos_searched:

					if "repr" in tkn_b.keys() and tkn_a["repr"] == tkn_b["repr"]:
						# seps não podem iniciar found_count
						if found_count > 0 or not tkn_a["repr"] in seps:
							found_count += 1
							if not tkn_b["repr"] in seps:
								found_count_relevantes += 1

		return base_count, base_count_relevantes, found_count, found_count_relevantes

	def similaridadeElementos2(self, p_lista_elementos_to_search: List[Dict[str, Type]], p_lista_elementos_searched: List[Dict[str, Type]], outlist: List[tuple], construct: Optional[str] = None):

		if not construct is None:
			
			for tkn_b in p_lista_elementos_searched:
				if 'construct' in tkn_b.keys() and tkn_b['construct'] == construct:
					outlist.append(self.similaridadeLists(p_lista_elementos_to_search, tkn_b["children"]))

		else:

			outlist.append(self.similaridadeLists(p_lista_elementos_to_search, p_lista_elementos_searched))


	def similaridadeElementos(self, p_lista_elementos_to_search: List[Dict[str, Type]], p_lista_elementos_searched: List[Dict[str, Type]], outlist: List[tuple]):
	
		to_search_tokens = []
		for tkn_a in p_lista_elementos_to_search:

			if 'construct' in tkn_a.keys():
			
				if len(to_search_tokens) > 0:
					use_tokens = deepcopy(to_search_tokens)
					del to_search_tokens[:]
					self.similaridadeElementos2(use_tokens, p_lista_elementos_searched, outlist)

				self.similaridadeElementos2(tkn_a["children"], p_lista_elementos_searched, outlist, construct=tkn_a['construct'])

			else:

				to_search_tokens.append(tkn_a)

		if len(to_search_tokens) > 0:
			# se ainda existirem elemetos em to_search_tokens, fazer yield self.similaridadeElementos2, 
			# à partida, serão elementos fora de construct
			self.similaridadeElementos2(to_search_tokens, p_lista_elementos_searched, outlist)

class ReconhecimentoElementos(object):

	def __init__(self, substituicoes_locais=None):

		self.part_of_speech_dict = None
		setup_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'setup')
		assert os.path.exists(setup_folder), f"não existe pasta 'setup' em {setup_folder}"

		with open(os.path.join(setup_folder, 'part_of_speech.json'), 'r', encoding='utf-8') as fp: 

			self.part_of_speech_dict = json.load(fp)	

			# Remover palavras que não tem POS definido (lista POS vazia)
			for k, v in self.part_of_speech_dict.items():
				if len(v) == 0:
					del self.part_of_speech_dict[k]

			injetarTemposVerbais(self.part_of_speech_dict)

		self.substituicoes = None
		with open(os.path.join(setup_folder, 'substituicoes.json'), 'r', encoding='utf-8') as fp: 
			self.substituicoes = json.load(fp)	

		if not substituicoes_locais is None:
			self.substituicoes_locais = substituicoes_locais
		else:
			self.substituicoes_locais = {}

		self.pos_admissiveis = None
		with open(os.path.join(setup_folder, 'pos_admissiveis.json'), 'r', encoding='utf-8') as fp: 
			self.pos_admissiveis = json.load(fp)	

		self.unidades = None
		with open(os.path.join(setup_folder, 'unidades.json'), 'r', encoding='utf-8') as fp: 
			self.unidades = json.load(fp)

		self.inicios_admissiveis = self.pos_admissiveis['permitidos_inicio']

		# self.sufixos_plurais = None
		# with open(os.path.join(setup_folder, 'sufixos_plurais,json'), 'r', encoding='utf-8') as fp: 
		# 	self.sufixos_plurais = json.load(fp)

		# self.remover_para_comparabilidade = set([])
		# check_list = set(['artigo', 'preposicao', 'contracao', 'conjuncao'])
		# for wrd in self.part_of_speech_dict.keys():
		# 	if len(set(self.part_of_speech_dict[wrd]).intersection(check_list)) > 0:
		# 		self.remover_para_comparabilidade.add(wrd)

		self.pos_admissiveis_final = set([])
		for k in self.pos_admissiveis["antecedentes_admissiveis"].keys():
			if not k in self.pos_admissiveis["proibidos_final"]:
				self.pos_admissiveis_final.add(k)

		self.nomes = []
		self.nomes_compostos = []

		with open(os.path.join(setup_folder, 'nomes_proprios.json'), 'r', encoding='utf-8') as fp: 
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

		print("Dimensão do vocabulário:", len(self.part_of_speech_dict.keys()), "palavras, nomes:", (len(self.nomes) + len(self.nomes_compostos)))

	def reconhecerUnidades(self, p_list: 'DictListManager') -> None:

		idxs_list = []
		p_list.walk(
			lambda idx, item: idxs_list.append(idx),
			predicate=lambda item: 'lower' in item.keys() and item["lower"] in self.unidades,
			include_idx_as_func_param = True
		)

		for idx in idxs_list:
			p_list[idx]['especial'] = 'unidade'

	def marcarSiglas(self, p_list: 'DictListManager', out_siglas: List[str]) -> None:

		del out_siglas[:]

		def add_sigla(p_out_siglas, p_str):
			if not p_str in p_out_siglas:
				p_out_siglas.append(p_str)

		siglas = list(self.substituicoes.keys())
		siglas.extend(self.substituicoes_locais.keys())

		p_list.walk(
			lambda item: item.update(pos=['sigla']),
			predicate=lambda item: 'repr' in item.keys() and item['repr'] in siglas,
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
			for k in ('construct', 'numero', 'especial'):
				if k in tkn.keys():
					do_continue = True
					break

			if do_continue:
				continue

			the_prev_tkn = prev_tkn

			if prev_tkn is None:
				the_prev_tkn = None
			else:
				for k in ('construct', 'numero'):
					if k in prev_tkn.keys():
						the_prev_tkn = None
						break

			siglas = list(self.substituicoes.keys())
			siglas.extend(self.substituicoes_locais.keys())

			try:
				genPOS(self.part_of_speech_dict, self.nomes, siglas, tkn, prev_tkn=the_prev_tkn)	
				token_list.validate(tkn)
			except POSNotFound as pnf:
				p_ret.setdefault('faltas', [])
				p_ret['faltas'].append(str(pnf))
			# except:
			# 	print("--156--", idx, grp_tokens, the_prev_tkn)
			# 	raise

	def reconhecerDenominacoes(self, p_list: 'DictListManager'):

		idxs_lists = []
		for idx, indices in p_list.iterateMatches(self.nomes_compostos):
			idxs_lists.append(indices)

		for idxs_list_1 in reversed(idxs_lists):
			p_list.buildConstruct(idxs_list_1, "denominacao")

		seps = ['da', 'do', 'das', 'dos', 'de', 'e', 'em', 'na', 'no']

		idxs_lists = []
		for idxs_list in p_list.iterNextContiguousConstructElements(
				lambda item: 'repr' in item.keys() \
					and (
						item["repr"] in self.nomes \
						or item["repr"] in seps \
						or item["ok"][0].isupper()
					)
				# testlist=["vítor", "ramalho"]
			):

			# Se não existirem nomes nos elementos selecionados (uma vez que, pelo critério de escolha definido
			# acima, podem ser outras palavras em maiúsculas ou separadores), continuar loop
			nomes_idx = [idx for idx in idxs_list if 'repr' in p_list[idx].keys() and p_list[idx]['repr'] in self.nomes]
			if len(nomes_idx) == 0:
				continue
		
			# remover separadoes que possam ocorrer no início
			while len(idxs_list) > 0 and p_list[idxs_list[0]]['repr'] in seps:
				idxs_list.pop(0)

			if len(idxs_list) == 0:
				continue

			# remover separadoes que possam ocorrer no final
			while len(idxs_list) > 0 and p_list[idxs_list[-1]]['repr'] in seps:
				idxs_list.pop()

			if len(idxs_list) == 0:
				continue

			# Tentativa de separar duas denominações juntas, desde que a primeira
			#   palavra a sequir à conjunção não seja um nome

			secnd_idxs_list = []
			for i, idx in enumerate(idxs_list):

				if i == 0:
					secnd_idxs_list.append(idx)
					continue

				pair = idxs_list[i:i+2]
				if len(pair) == 2:			
					if 'lower' in p_list[pair[0]].keys() and \
						p_list[pair[0]]['lower'] == 'e' and \
						not p_list[pair[1]]['repr'] in self.nomes:
							idxs_lists.append(copy(secnd_idxs_list))
							del secnd_idxs_list[:]
					else:
						# não deixar sep no inicio de nova lista, se tiver havido separação
						if len(secnd_idxs_list) > 0 or not p_list[pair[0]]['repr'] in seps:
							secnd_idxs_list.append(idx)
				else:
					# pair terá apenas um elemento no final da lista
					secnd_idxs_list.append(idx)

			if len(secnd_idxs_list) > 0:
				idxs_lists.append(secnd_idxs_list)

		for idxs_list_2 in reversed(idxs_lists):

			# # Verificar que indices são consecutivos
			# if len(idxs_list_2) == 0 or len(idxs_list_2) != (idxs_list_2[-1] - idxs_list_2[0]) + 1:
			# 	continue

			# p_list.buildConstruct(idxs_list_2, "denominacao", include_number="START")

			try:
				p_list.buildConstruct(idxs_list_2, "denominacao", include_number="START")
			except AssertionError as ae:
				aelist = json.loads(str(ae))
				print("idxs_list_2:", idxs_list_2)
				print([p_list[idx] for idx in aelist])

				
	def reconhecerDatas(self, p_list: 'DictListManager') -> None:

		meses = [
			"janeiro", "fevereiro", "março", "abril", "maio", "junho",
			"julho", "agosto", "setembro", "outubro", "novembro", "dezembro"
		]

		idxs_lists = []

		for idx, grp_tokens in p_list.iterateGroups(group_size=7, prev_is_null=False):	
			if len(grp_tokens) < 7:
				continue
			atkn, btkn, ctkn, dtkn, etkn, ftkn, gtkn = grp_tokens	
			if 'numero' in atkn.keys() and \
					'repr' in btkn.keys() and 'repr' in ctkn.keys() and 'repr' in dtkn.keys() and 'repr' in etkn.keys() \
					 and 'repr' in ftkn.keys() and 'numero' in gtkn.keys():
				if atkn['numero'] == 'int' and btkn['repr'] == 'de' and ctkn['repr'] in meses and dtkn['repr'] == 'do' \
						and etkn['repr'] == 'ano' and ftkn['repr'] == 'de' and gtkn['numero'] == 'int':
					idxs_lists.append([j+idx for j in range(7)])

		for idxs_list_0 in reversed(idxs_lists):
			p_list.buildConstruct(idxs_list_0, "data")

		del idxs_lists[:]

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

			if sigla in self.substituicoes.keys():
				words_subst = self.substituicoes[sigla].split()
			else:
				words_subst = self.substituicoes_locais[sigla].split()

			idxs_lists = []
			for idx, indices in p_list.iterateMatches([words_subst]):
				idxs_lists.append(indices)

			for idxs_list_1 in reversed(idxs_lists):
				p_list.buildConstruct(idxs_list_1, "denominacao", adic_attribs=[('sigla', sigla)])

	def reconhecerAtosNormativos(self, p_list: 'DictListManager') -> None:

		idxs_lists = []

		def is_tipo_ato(p_repr):
			return p_repr in ('decreto-lei', 'dec.-lei', 'dl', 'portaria', 'aviso', 'lei', 'dec.')

		for idx, grp_tokens in p_list.iterateGroups(group_size=4, prev_is_null=False):	
			if len(grp_tokens) < 4:
				continue
			atkn, btkn, ctkn, dtkn = grp_tokens	
			if 'lower' in atkn.keys() and 'lower' in btkn.keys() and 'lower' in ctkn.keys() and 'numero' in dtkn.keys():
				if is_tipo_ato(atkn['lower']) and is_tipo_ato(btkn['lower']) and ctkn['lower'] == 'n.º' and dtkn['numero'] == 'item':
					idxs_lists.append([j+idx for j in range(4)])

		for idxs_list_0 in reversed(idxs_lists):
			p_list.buildConstruct(idxs_list_0, "ato_normativo")

		del idxs_lists[:]

		for idx, grp_tokens in p_list.iterateGroups(group_size=3, prev_is_null=False):	
			if len(grp_tokens) < 3:
				continue
			atkn, btkn, ctkn = grp_tokens	
			if 'lower' in atkn.keys() and 'lower' in btkn.keys() and 'numero' in ctkn.keys():
				if is_tipo_ato(atkn['lower']) and btkn['lower'] == 'n.º' and ctkn['numero'] == 'item':
					idxs_lists.append([j+idx for j in range(3)])

		for idxs_list_1 in reversed(idxs_lists):
			p_list.buildConstruct(idxs_list_1, "ato_normativo")

		del idxs_lists [:]

		for idx, grp_tokens in p_list.iterateGroups(group_size=2, prev_is_null=False):	
			if len(grp_tokens) < 2:
				continue
			atkn, ctkn = grp_tokens	
			if 'repr' in atkn.keys() and 'numero' in ctkn.keys():
				if is_tipo_ato(atkn['repr']) and ctkn['numero'] == 'item':
					idxs_lists.append([j+idx for j in range(2)])

		for idxs_list_2 in reversed(idxs_lists):
			p_list.buildConstruct(idxs_list_2, "ato_normativo")

	def reconhecerArtigosAlineas(self, p_list: 'DictListManager') -> None:

		idxs_lists = []

		for idx, grp_tokens in p_list.iterateGroups(group_size=2, prev_is_null=False):	
			if len(grp_tokens) < 2:
				continue
			atkn, btkn = grp_tokens	
			if 'lower' in atkn.keys() and 'numero' in btkn.keys():
				if atkn['lower'] == 'artigo' and btkn['numero'] == 'ord':
					idxs_lists.append([j+idx for j in range(2)])

		for idxs_list_0 in reversed(idxs_lists):
			p_list.buildConstruct(idxs_list_0, "artigo")

		del idxs_lists [:]

		for idx, grp_tokens in p_list.iterateGroups(group_size=2, prev_is_null=False):	
			if len(grp_tokens) < 2:
				continue
			atkn, btkn = grp_tokens	
			if 'lower' in atkn.keys() and 'numero' in btkn.keys():
				if atkn['lower'] == 'alínea' and btkn['numero'] == 'alinea':
					idxs_lists.append([j+idx for j in range(2)])

		for idxs_list_0 in reversed(idxs_lists):
			p_list.buildConstruct(idxs_list_0, "alinea")

	def genAdicTokensOverSeps(self, p_list: 'DictListManager', break_on_hyphens=False):

		found_items = []
		p_list.walk(
			lambda idx, item: found_items.append((idx, item)),
			predicate=lambda item: 'repr' in item.keys() and not 'construct' in item.keys() and not 'numero' in item.keys() and '/' in item['repr'],
			include_idx_as_func_param=True
		)

		if len(found_items) > 0:

			for idx, _item in reversed(found_items):
				old_item = p_list.remove_at(idx)
				#print("::", old_item, _item)
				if break_on_hyphens:
					new_items = genTokensList(old_item['repr'], sep_chars=r"([\-/])")
				else:
					new_items = genTokensList(old_item['repr'], sep_chars=r"(/)")
				for ni, new_item in enumerate(new_items):
					p_list.insert(new_item, index=idx + ni)

	def reconhecerReferentes(self, p_list: 'DictListManager'):

		def validar_construct(p_children: List[Dict[str, Any]]) -> bool:

			found = False
			ret = False
			for child in p_children:
				if 'nome' in child['pos']:
					found = True
					break

			if found:
				if len(p_children) > 0:
					if len(p_children) > 1 or ('ok' in p_children[0].keys() and p_children[0]["ok"][0].isupper()):
						ret = True

			return ret

		def right_trim(p_tkn: Dict[str, Any]) -> bool:		
			ret = True
			if 'pos' in p_tkn.keys():
				ret = not bool(self.pos_admissiveis_final.intersection(p_tkn['pos']))
			return ret

		idxs_lists = []
		ant_admiss = self.pos_admissiveis['antecedentes_admissiveis']

		idx_list = []
		for idx, grp_tokens in p_list.iterateGroups(group_size=2, prev_is_null=True):
			
			# último grupo, com apenas um elemento, é para desprezar
			if len(grp_tokens) < 2:
				continue

			prev_tkn, tkn = grp_tokens

			if not 'pos' in tkn.keys():

				if len(idx_list) > 0:
					if len(idx_list) > 1 or ('ok' in p_list[idx_list[0]].keys() and p_list[idx_list[0]]["ok"][0].isupper()): # usar apenas listas com mais de um elemento ou se o o elemento único estiver 'capitalizado'
						idxs_lists.append(copy(idx_list))
					else:
						p_list[idx_list[0]]['ref_skipped'] = f"elem_unico A"
					del idx_list[:]

				continue

			if prev_tkn is None or not 'pos' in prev_tkn.keys() or 'ref_skipped' in prev_tkn.keys():

				if set(tkn['pos']).issubset(self.inicios_admissiveis):
					assert 'repr' in tkn.keys()
					idx_list.append(idx)
				else:
					tkn['ref_skipped'] = "skip A"

			else:

				ant_compat = antecedente_compatível(prev_tkn, tkn, ant_admiss)
				#print(f"ant_compat:{ant_compat} prev:'{prev_tkn}' este:'{tkn}' adm:{bool(set(tkn['pos']).intersection(self.inicios_admissiveis))}")
				if ant_compat is None or not ant_compat: # incompatibilidade do antecedente é inconclusiva ou é verdade

					# Começamos nova lista de índices
					#print(f"ant_compat:{ant_compat} prev:'{prev_tkn}' este:'{tkn}' adm:{bool(set(tkn['pos']).intersection(self.inicios_admissiveis))}")
					
					if len(idx_list) > 0:
						if len(idx_list) > 1 or ('ok' in p_list[idx_list[0]].keys() and p_list[idx_list[0]]["ok"][0].isupper()):  # usar apenas listas com mais de um elemento ou se o o elemento único estiver 'capitalizado'
							idxs_lists.append(copy(idx_list))
						else:
							p_list[idx_list[0]]['ref_skipped'] = "elem_unico B"
						del idx_list[:]

					tkn['ref_skipped'] = "skip B"
				
				else:
					# compatibilidade do antecedente é clara
					idx_list.append(idx)


		if len(idx_list) > 0:
			if len(idx_list) > 1: # usar apenas listas com mais de um elemento
				idxs_lists.append(copy(idx_list))
			else:
				p_list[idx_list[0]]['ref_skipped'] = "elem_unico C"
			del idx_list[:]

		const_valid_errorcnt = 0
		const_empty_errorcnt = 0
		for idxs_list_1 in reversed(idxs_lists):
			try:
				p_list.buildConstruct(idxs_list_1, "referente", right_trimming_func=right_trim, validation_func=validar_construct, include_number="BOTH") #, context_data={'paf': self.pos_admissiveis_final})
			except ConstructValidationError as ce:
				const_valid_errorcnt += 1
			except EmptyConstructError as ece:
				const_empty_errorcnt += 1

	def reconhecerEmJanela(self, p_janela: str, out_dict: Dict[str, Type]) -> None:

		out_dict.clear()

		# Limpeza de artefactos prejudiciais ##################################

		# print(in_window_text)

		in_window_text = p_janela.replace(" e/ou ", " ou ").replace(" e / ou ", " ou ")

		# in_window_text = re.sub(fr"({PT_ALPHA_CHAR_PATT})/({PT_ALPHA_CHAR_PATT})", r"\1 / \2", in_window_text)   ## tornar barras separadoras contíguas a texto em barras isoladas
		# in_window_text = re.sub(fr"({PT_ALPHA_CHAR_PATT})-({PT_ALPHA_CHAR_PATT})", r"\1 - \2", in_window_text)   ## tornar barras separadoras contíguas a texto em barras isoladas

		cleantext = in_window_text

		# if " " in cleantext and "EM" in cleantext:
		# 	print("--473:", cleantext)

		# Primeira lista de tokens
		
		out_dict['tokens_list'] = genTokensList(cleantext)

		# Reconhecer unidades: db(A), m2, ha, etc.

		self.reconhecerUnidades(out_dict['tokens_list'])

		# Associar identificadores 'numero' que tenham ficado separados por existirem espaços entre os elementos componentes

		assocNumParts(out_dict['tokens_list'])

		assocVariosTripletos(out_dict['tokens_list'])
		assocVariosPares(out_dict['tokens_list'])

		# Definir 'repr' onde possível ########################################

		buildRepr(out_dict['tokens_list'])

		# Reconhecer construções (q precisam de 'repr' mas não de 'pos') ######

		reconhecerURLs(out_dict['tokens_list'])
		self.reconhecerDatas(out_dict['tokens_list'])
		self.reconhecerArtigosAlineas(out_dict['tokens_list'])
		self.reconhecerAtosNormativos(out_dict['tokens_list'])

		# Dividir em tokens palavras que incluem '/' ###########################
		self.genAdicTokensOverSeps(out_dict['tokens_list'], break_on_hyphens=False)

		# Reconhecer construções nome ou designação ###########################

		self.reconhecerDenominacoes(out_dict['tokens_list'])

		# Marcasr siglas e nomes ou designações de expansão de sigla  #########

		out_siglas = []
		self.marcarSiglas(out_dict['tokens_list'], out_siglas)	
		self.reconhecerExpansaoSiglas(out_dict['tokens_list'], out_siglas)

		# Obter POS ###########################################################

		# pos=['sigla'] já se encontram preenchidos

		self.buildPOS(out_dict, out_siglas)

		# Marcar REFERENTES ####################################################
		
		self.reconhecerReferentes(out_dict['tokens_list'])

		atos = []
		for tkn in out_dict['tokens_list']:
			if 'construct' in tkn.keys() and tkn['construct'] == 'ato_normativo':
				atos.append(tkn['repr'])
		if len(atos) > 0:
			out_dict['atos'] = atos

		denominacoes = []
		for tkn in out_dict['tokens_list']:
			if 'construct' in tkn.keys() and tkn['construct'] == 'denominacao':
				denominacoes.append(tkn['repr'])
		if len(denominacoes) > 0:
			out_dict['denominacoes'] = denominacoes

		referentes = []
		for tkn in out_dict['tokens_list']:
			if 'construct' in tkn.keys() and tkn['construct'] == 'referente':
				if not tkn['repr'] in referentes:
					referentes.append(tkn['repr'])
		if len(referentes) > 0:
			out_dict['referentes'] = referentes

		URLs = []
		for tkn in out_dict['tokens_list']:
			if 'construct' in tkn.keys() and tkn['construct'] == 'URL':
				URLs.append(tkn['repr'])
		if len(URLs) > 0:
			out_dict['urls'] = URLs

		# print("X", out_dict['tokens_list'].to_json())

