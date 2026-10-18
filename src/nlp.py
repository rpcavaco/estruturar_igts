
import os
import json
import requests
import time
import re
import warnings

from copy import copy, deepcopy
from unidecode import unidecode
from time import sleep
from tqdm import tqdm

from .json_helpers import find_unserializable

from typing import List, Dict, Type, Any #, Callable, Dict, Iterable, Iterator, List, Optional, Type


from .dict_list_manager import DictListManager

# ATENÇÃO - no PROCESSAMENTO DE blocos_analise

# É preciso remover ([a-z])/([a-z]) por $1 ou $2 mas, PRIMEIRO, substituir e/ou por apenas ou

WIKTIONARY_URL = "https://en.wiktionary.org/api/rest_v1/page/definition/{}?redirect=false"

WIKTIONARY_SLEEP = 3

# SEP_PRIMARIOS = ['de', 'e', 'a', 'da', 'do', 'ou', 'que', 'o', 'em', 'Em', 'com', 'as', 'no', 'à', 'À', 'das', 'dos', 'para', 'os', 'A', 'se', 'não', 'na', 'ao', 'como', 'por', 'é', 'uma', 'ser', 'nos', 'nas', 'seguintes', 'um', 'As', 'O', 'caso', 'são', 'sua', 'Os', 'No', 'entre', 'às','sem', 'quando', 'desde', 'pela', 'seja', 'pelo', 'aos', 'Nas', 'neste', 'nestes', 'nesta', 'nestas', 'cada',  'mais', 'menos']

# NOT_WORD_CHARS_RELAXED = ['%', '*', '+']
NOT_WORD_CHARS = ['%', '*', '+']

# CONTINUIDADE_CHARS = [':']

# ARTIGO_DEFINIDO = ['o', 'a', 'os', 'as', 'um', 'uma']
PREPOSICAO = ['de', 'do', 'da', 'dos', 'das', 'para', 'em', 'no', 'na', 'nas', 'nos', 'num', 'numa', 'deste', 'desta', 'nuns', 'numas', 'destes', 'destas', 'entre', 'ao', 'aos', 'à',  'por', 'sobre', 'sob']
# CONTRACOES = ['pela', 'pelo', 'pelos']
# CONJUNCOES_DESIGNACOES = ['e', 'ou', 'não', 'se', 'com', 'sem']
# CONJUNCOES_DISCURSIVAS = ['nem', 'mas', 'que', 'como']
# PRONOMES = ['este', 'esta', 'estes', 'estas', 'seu', 'sua', 'outro', 'outros', 'outra', 'outras']
# MISTO = ['só', 'tal']
# ADVERBIOS = ['onde', 'por', 'onde', 'além', 'mais']
# QUANTIFICADOR = ['cada']

FORMAS_VERBAIS_AUXILIARES = {
	"ter": ["ter", "tenho", "tens", "tem", "temos", "tendes", "têm", "tinha", "tinhas",
			"tinha", "tínhamos", "tínheis", "tinham", "tive", "tiveste", "teve", "tivemos",
			"tivestes", "tiveram", "tivera", "tiveras", "tivéramos", "tivéreis", "tiveram",
			"terei", "terás", "terá", "teremos", "tereis", "terão", "teria", "terias",
			"teríamos", "teríeis", "teriam", "tenha", "tenhas", "tenha", "tenhamos",
			"tenhais", "tenham", "tivesses",
			"tivesse", "tivéssemos", "tivésseis", "tivessem",
			"tiver", "tiveres", "tiver", "tivermos",
			"tiverdes", "tiverem"
		],
	"ser": [
		"ser", "sou", "és", "é", "somos", "sois", "são", "sido", "serei", "sereis", "será", "serás", "seremos", "serão",
		"sermos", "serdes", "serem", "sede", "sê", "sendo", 
		"seria", "serias", "seríeis", "seríamos", "seja", "sejam", "sejais", "sejamos", "for", "fores", "formos", 
		"fordes", "forem", "foram", "fosse", "fosses", "fossem", "fôsseis"
	],
	"estar": [
		"estar", "estou", "está", "estamos", "estais", "estão", "estava", "estavam", "estiveram", "estivera", "estará",
		"estaremos", "estarão", "estaria", "estaríamos", "estariam", "esteja", "estejam", "estivesse", "estivessem",
		"estiver", "estiverem", "esteja", "estejam", "estarem"
	],
	"haver": [
		"haver", "há", "havido", "houve"
	]
}

PATT_NUMERO = {
	"int": r"^([0-9]+)$",	
	"area": (r"^([0-9]+)[\s]?m2$", r"^([0-9]+)[\s]?ha$", r"^([0-9]+)[\s]?km2$"),
	"comprimento": (r"^([0-9]+)[\s]?m$", r"^([0-9]+)[\s]?km$"),
	"perc": r"^([0-9]+)[\s]?%$",
	"item": (r"^[0-9]+[\.\-/]+[0-9]+[\./]+[0-9]+$", r"^[0-9]+[\.\-/]+[0-9]+$"),
	"float": r"^([0-9]+[\,]+[0-9]+)$",
	"ord": r'^([0-9]+)[\. ]?[ºª]$',
	"alinea": r'^[a-cA-C]?[a-zA-Z]\)$',
	"estrada": (r"[eE][nNmM][\s]?[\d]+[\-]?[\d]+$", r"[eE][nNmM][\s]?[\d]$")
} 

# POS_ANTECEDENTES_INADMISSIVEIS = {
# 	"adjetivo": [
# 		"adjetivo"
# 	]
# }

# POS_INADMISSIVEIS_EXTREMOS_JANELAS = set([
# 	"preposicao", "conjuncao", "artigo", "contracao"
# ])

# POS_INADMISSIVEIS_PREFIXO_JANELAS = set([
# 	"adjetivo"
# ])

# POS_INADMISSIVEIS_PREFIXO_JANELAS_UNICO = set([
# 	"participio",
# 	"adverbio",
# 	"preposicao"
# ])

# POS_TESTE_SUFIXO_JANELAS = [
# 	{
# 		'cont': 'verbo',
# 		'cardinality': 'single',
# 		'testeprev': {
# 			'op': 'temdeincluir',
# 			'valores': ['pronome']
# 		}
# 	}
# ]

# PREFIXOS_A_ELIMINAR = [  ## pASAR A LISTA
# 	[
# 		"bem", "como"
# 	]
# ]

class NumeracaoRomana(object):
	"""Classe para leitura e verificação de números em notação romana
	"""

	@classmethod
	def to_roman(cls, n: int) -> str:
		vals = [(100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
				(10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
		out = []
		for value, symbol in vals:
			count, n = divmod(n, value)
			out.append(symbol * count)
		return "".join(out)

	def __init__(self):
		self.nr = [NumeracaoRomana.to_roman(i) for i in range(1, 101)]
		
	def fromRomanStr(self, p_in_str) -> int | None:
		try:
			idx = self.nr.index(p_in_str.upper())
			ret = idx + 1
		except ValueError:
			ret = None

		return ret
	
	def checkIsRoman(self, p_str) -> bool:
		return p_str.strip().upper() in self.nr

def getNumPattern(p_raw, full=False):

	num_patt = None
	string = None
	val = None

	def do_eval(p_patt, pp_raw):
		mo = re.match(p_patt, pp_raw)
		if mo is None:
			return None
		else:
			return mo.group(0), mo.groups()

	for k, patts in PATT_NUMERO.items():

		if isinstance(patts, list) or isinstance(patts, tuple):
			for patt in patts:
				if full:
					real_patt = f"^{patt}"
				else:
					real_patt = patt
				eval_result = do_eval(real_patt, p_raw)
				if not eval_result is None:
					num_patt = k
					string = eval_result[0]
					if len(eval_result[1]) > 0:
						val = eval_result[1][0]
		else:
			if full:
				real_patts = f"^{patts}"
			else:
				real_patts = patts
			eval_result = do_eval(real_patts, p_raw)
			if not eval_result is None:
				num_patt = k
				string = eval_result[0]
				if len(eval_result[1]) > 0:
					val = eval_result[1][0]		

	if not num_patt is None:
		if num_patt == 'int':
			val = int(val) 
		elif num_patt == 'float':
			val = float(val.replace(',', '.')) 
		elif not val is None:
			val = float(val)

	return num_patt, val, string

class POSNotFound(Exception):
	def __init__(self, p_token):	
		self.token = p_token			
		super().__init__(self.token['repr'])

def verificar(value, checks, bus=None, path_exec_key='execpath'):
	broke = False
	for i, check in enumerate(checks):
		prevfunc, condition, action, stops = check
		if not prevfunc is None:
			prevval = prevfunc(value, bus)
		else:
			prevval = None
		if condition(prevval, value, bus):
			action(prevval, value, bus)
			if stops:
				bus.setdefault(path_exec_key, [])
				bus[path_exec_key].append(f"{i+1}_Norm")
				broke = True
				break

	if not broke:
		bus.setdefault(path_exec_key, [])
		bus[path_exec_key].append('Final')

def sep_type(p_sep_char: str):

	type_str = None
	divseps = [':', ';','/', '-', chr(int('2013', 16))]

	if p_sep_char in ('“', '”',  '"', "'", '(', '«', '.'):
		if p_sep_char in ('“', '”',  '"', "'"):
			type_str = "quote"
		elif p_sep_char == '«':
			type_str = "angle_quote"
		else:
			type_str = "parentesis"

	if type_str is None:
		if p_sep_char in ('”', '“', '"', "'"):
			type_str = "quote"
		elif p_sep_char == '»':
			type_str = "angle_quote"
		elif p_sep_char == ')':
			type_str = "parentesis"
		elif p_sep_char == ',':
			type_str = "soft"
		elif p_sep_char in ('.', ';'):
			type_str = "hard"
		elif p_sep_char == ':':
			type_str = "continuity"

	if type_str is None:
		if p_sep_char in divseps:
			type_str = "div"

	return type_str

def genSepararSeparadoresColados(p_the_string: str):

	sep_content = ""
	the_string = str(p_the_string)

	prevlist = []
	postlist = []

	# remover inicios estranhos a uma palavra
	while len(the_string) > 0 and the_string[0] in ('“', '”',  '"', "'", '(', '«', '.'):
		the_char = the_string[0]
		the_string = the_string[1:]
		if the_char in ('“', '”',  '"', "'"):
			type_str = "quote"
		elif the_char == '«':
			type_str = "angle_quote"
		else:
			type_str = "parentesis"
		prevlist.append({"sep": "containment_start", "type": type_str, "ok": the_char} )

	sep_content = ""

	# remover terminações estranhas a uma palavra
	sep_chars = []
	while len(the_string) > 0 and the_string[-1] in ('.', ',', ':', ';', '”', '“', '"', "'", ')', '»', '-'):
		the_char = the_string[-1]
		the_string = the_string[:-1]
		sep_chars.append(the_char)

	if len(sep_chars) > 0:
		rev_chars = reversed(sep_chars)
		for ch in rev_chars:
			type_str = None
			if ch in ('”', '“', '"', "'"):
				type_str = "quote"
			elif ch == '»':
				type_str = "angle_quote"
			elif ch == ')':
				type_str = "parentesis"
			if not type_str is None:
				if not "(" in the_string:
					postlist.append({"sep": "containment_end", "type": type_str, "ok": ch})
				else:
					the_string = the_string + ch
			else:
				if ch == ',':
					postlist.append({"sep": "soft", "ok": ch})
				elif ch in ('.', ';'):
					postlist.append({"sep": "hard", "ok": ch})
				elif ch == ':':
					postlist.append({"sep": "continuity", "ok": ch})

	return prevlist, the_string, postlist


def genTokens(p_ret: "DictListManager", p_dirty: str) -> None:

	# print("## p_dirty:", p_dirty)

	if len(p_dirty) == 0:
		return

	the_string = p_dirty.strip() # Sem transformação de case, está como o original
	# lower_string = the_string.lower()

	num_patt, val, string = getNumPattern(the_string)
	postlist = []

	if len(p_dirty) >= 2:
		if num_patt is None:
			prevlist, the_string, postlist = genSepararSeparadoresColados(the_string)
			for el in prevlist:
				p_ret.insert(**el)
		else:
			assert not string is None
			if len(string.strip()) < len(the_string.strip()):
				prevlist, the_string, postlist = genSepararSeparadoresColados(the_string)
				for el in prevlist:
					p_ret.insert(**el)				

	if len(the_string) > 0:

		the_string = the_string.replace('―', '-')

		ALL_SEPS = ('.', ',', ':', ';', '”', '“', ')', '»', '“', '(', '«', '/', '-', chr(int('2013', 16)), '+', '*', '=', '<', '>')
		aseps = set(ALL_SEPS)

		# separadores DIVISORES
		divseps = set([':', ';','/', '-', chr(int('2013', 16))])

		rom_num = NumeracaoRomana()

		init_len = len(p_ret)

		checks = [

			(None, 
				lambda _pv, v, _bus: v in NOT_WORD_CHARS, 
				lambda _pv, v, bus: bus['ret'].insert(raw=bus['dirty']), 
					True ),

			(None, 
				lambda _pv, _v, bus: not bus['numpatt'][0] is None and not bus['numpatt'][1] is None, 
				lambda _pv, v, bus: bus['ret'].insert(ok=v, numero=bus['numpatt'][0], valor=bus['numpatt'][1], string=str(v)), 
					True ),

			(None, 
				lambda _pv, _v, bus: not bus['numpatt'][0] is None and bus['numpatt'][1] is None, 
				lambda _pv, v, bus: bus['ret'].insert(ok=v, numero=bus['numpatt'][0], string=str(v)), 
					True ),

			(lambda v, _bus: rom_num.fromRomanStr(v), 
				lambda pv, _v, _bus: not pv is None, 
				lambda pv, v, bus: bus['ret'].insert(ok=v, numero="romano", valor=pv, string=str(v)), 
					True ),

		]

		verificar(the_string, checks, bus={'ret': p_ret, 'dirty': p_dirty, 'numpatt': getNumPattern(the_string)})

		if len(p_ret) == init_len:

			checks2 = [

				(lambda v, _bus: set(v), 
					lambda pv, _v, bus: pv.issubset(bus['divseps']), 
					lambda _pv, v, bus: bus['ret'].insert(sep="div", ok=v ), 
						True ),

				(lambda v, _bus: set(v), 
					lambda pv, _v, bus: pv.issubset(bus['aseps']), 
					lambda _pv, v, bus: bus['ret'].insert(sep="simple", ok=v ), 
						True )
			]

			verificar(the_string, checks2, bus={'ret': p_ret, 'aseps': aseps, 'divseps': divseps })

		if len(p_ret) == init_len:
			p_ret.insert(ok=the_string, lower=the_string.lower())

	for el in postlist:
		p_ret.insert(**el)

	assert len(p_ret) > init_len, f"{len(p_ret)} > {init_len},  '{p_dirty}', {prevlist}, {postlist}, '{the_string}' {p_ret}"

	#print("## ret:", p_ret)

	return

def genTokensList(p_in_window_text: str, sep_chars: str = r"(\n)") -> list[Any]:

	#print("genTokensList:", p_in_window_text[:40])

	# Texto de p_in_window_text deve estar todo em minúsculas e com palavras e separadores intervalados apenas por um único espaço em branco
	# cleantext = ' '.join(p_in_window_text.split()).lower()
	cleantext = p_in_window_text

	# Tokens são dicionários, cada um para uma palavra

	schemas = [{
		"type" : "object",
		"properties" : {
			"raw" : {"type" : "string"}
		},
		"required": ["raw"]
	},
	{
		"type" : "object",
		"properties" : {
			"ok" : {"type" : "string"},
			"numero" : {"type" : "string"},
			"valor" : {"type" : "number"},
			"string" : {"type" : "string"}
		},
		"required": ["ok", "numero", "string"]
	},
	{
		"type" : "object",
		"properties" : {
			"sep" : {"type" : "string"},
			"ok" : {"type" : "string"}
		},
		"required": ["sep", "ok"]
	},
	{
		"type" : "object",
		"properties" : {
			"ok" : {"type" : "string"},
			"lower" : {"type" : "string"}
		},
		"required": ["ok", "lower"]
	}]

	first_tokens = DictListManager(schemas)

	splits = re.split(sep_chars, cleantext)

	for spl in splits:
		mo = re.match(sep_chars, spl)
		if not mo is None:
			first_tokens.insert({"sep": sep_type(spl), "ok": spl})
		else:
			for wrd in spl.split():
				genTokens(first_tokens, wrd)
			# if len(set(tkn.keys()).intersection(['lower', 'string', 'div'])) > 0:
			# 	first_tokens.append(tkn)

	# ret = []	

	# # Dividir em listas	
	# curr_list = []
	# for ti, tkn in enumerate(first_tokens):
	# 	if 'div' in tkn.keys() and tkn['div']:
	# 		assert ti > 0 and ti < (len(first_tokens) - 1)
	# 		ret.append(copy(curr_list))
	# 		del curr_list[:]
	# 	else:
	# 		curr_list.append(tkn)

	# if len(curr_list) > 0:
	# 	ret.append(copy(curr_list))

	return first_tokens

def setTokenRepr(p_tkn: dict[str,Any]) -> bool:

	ret = False

	assert len(set(['lower', 'string']).intersection(p_tkn.keys())) > 0

	if 'lower' in p_tkn.keys():
		p_tkn['repr'] = p_tkn['lower']
		ret = True
	elif 'string' in p_tkn.keys():
		p_tkn['repr'] = p_tkn['string']
		ret = True

	return ret

def genPOS(
		p_part_of_speech_dict: Dict[str, Dict[str, Any]], 
		p_nomes_list: List[str], 
		p_siglas_list: List[str], 
		p_this_token: Dict[str,Any], 
		prev_tkn: Dict[str,Any] | None = None
	) -> None:

	def is_nome_equiv(p_attribs):
		ret = False
		for attr in ['nome', 'sigla', 'nome_proprio', 'construct']:
			if attr in p_attribs:
				ret = True
				break
		return ret

	def is_verbo_equiv(p_attribs):
		ret = False
		for attr in ['verbo', 'participio']:
			if attr in p_attribs:
				ret = True
				break
		return ret

	# assert len(p_allowed_init_pos) > 0, "genPOS: 'p_allowed_init_pos' parameter requires non-empty list"
	if not 'repr' in p_this_token.keys():
		return

	# Não tocar nas siglas
	if 'pos' in p_this_token.keys() and p_this_token['pos'] == ['sigla']:
		return

	if p_this_token['repr'] in p_nomes_list:
		p_this_token.update(pos=['nome_proprio'])
		return 

	if not p_this_token['repr'] in p_part_of_speech_dict.keys():
		raise POSNotFound(p_this_token)

	if prev_tkn is None or not 'pos' in prev_tkn.keys():	# prev_tkn['repr'] in p_part_of_speech_dict.keys():
		real_prev_tkn = None
	else:
		real_prev_tkn = prev_tkn

	def_pos = set(p_part_of_speech_dict[p_this_token['repr']])

	prev_attribs = None # Attribs, podem conter POSs + 'construct'
	if not real_prev_tkn is None:
		prev_attribs = list(set(real_prev_tkn['pos']))

	if prev_attribs is None and not prev_tkn is None and 'construct' in prev_tkn.keys():
		prev_attribs = ['construct']

	# if p_this_token['repr'] == 'público':
	# 	raise RuntimeError("caca")
	# 	print("--453--", prev_tkn, real_prev_tkn, p_this_token, prev_attribs, def_pos)

	nomadj_set = set(["nome", "adjetivo"])
	nomverb_set = set(["nome", "verbo"])
	nomadverb_set = set(["nome", "adverbio"])
	verbadj_set = set(["verbo", "adjetivo"])
	nompart_set = set(["nome", "participio"])
	partadj_set = set(["participio", "adjetivo"])

	ret = None

	fluxo = []
	pronto = False
	count = 0

	while not pronto and count < 5:

		count += 1
	
		if nomadj_set.issubset(def_pos):
			if real_prev_tkn is None:
				fluxo.append("A1")
				def_pos.remove("adjetivo")
				# ret = ['nome']
				# pronto = True
			else:
				if is_nome_equiv(prev_attribs) or is_verbo_equiv(prev_attribs):
					fluxo.append("A2")
					# ret = ['adjetivo']
					def_pos.remove("nome")
				# elif 'adjetivo' in prev_pos:
				# 	fluxo.append("A3")
				# 	# ret = ['adjetivo']
				# 	def_pos.remove("adjetivo")
				else:
					fluxo.append("A4")
					ret = list(def_pos)
					pronto = True
		elif nomverb_set.issubset(def_pos):
			if real_prev_tkn is None or bool(set(['preposicao', 'artigo', 'conjuncao', 'contracao']).intersection(prev_attribs)):
				fluxo.append("B1")
				#ret = ['nome']
				def_pos.remove("verbo")
			else:
				if is_nome_equiv(prev_attribs):
					fluxo.append("B2")
					# ret = ['verbo']
					def_pos.remove("nome")
				else:
					fluxo.append("B3")
					ret = list(def_pos)
					pronto = True
		elif nompart_set.issubset(def_pos):
			if real_prev_tkn is None or len(set(['preposicao', 'artigo', 'conjuncao']).intersection(prev_attribs)) > 0:
				fluxo.append("C1")
				#ret = ['nome']
				def_pos.remove("participio")
			else:
				if is_nome_equiv(prev_attribs):
					fluxo.append("C2")
					# ret = ['verbo']
					def_pos.remove("nome")
				else:
					fluxo.append("C3")
					ret = list(def_pos)
					pronto = True
		elif verbadj_set.issubset(def_pos):
			if real_prev_tkn is None:
				fluxo.append("D1")
				def_pos.remove("adjetivo")
			else:
				if is_nome_equiv(prev_attribs):
					fluxo.append("D2")
					def_pos.remove("verbo")
					# ret = ['adjetivo']
				else:
					fluxo.append("D3")
					ret = list(def_pos)
					pronto = True
		elif partadj_set.issubset(def_pos):
			if real_prev_tkn is None:
				fluxo.append("E1")
				def_pos.remove("adjetivo")
			else:
				if is_nome_equiv(prev_attribs):
					fluxo.append("E2")
					def_pos.remove("participio")
					# ret = ['adjetivo']
				elif bool(set(['adjetivo', 'preposicao']).intersection(prev_attribs)):
					fluxo.append("E3")
					def_pos.remove("adjetivo")
					# ret = ['adjetivo']
				else:
					fluxo.append("E4")
					ret = list(def_pos)
					pronto = True
		else:
			pronto = True
			# if real_prev_tkn is None:
			# 	fluxo.append("F1")
			# 	ret = list(def_pos.intersection(p_allowed_init_pos))
			# else:
			# 	fluxo.append("F2")
			ret = list(def_pos)

	assert not ret is None and len(ret) > 0, f"prev_tkn:{prev_tkn} this_token:{p_this_token}, def:{def_pos}"

	# if p_this_token['repr'] == "ocorrido":
	# 	print(fluxo, p_this_token, partadj_set, ret, partadj_set.issubset(set(ret)))
	
	p_this_token['pos'] = ret

	# # Caminho F2 é default, POS inicial é transcrito sem transformação; se for único não precisa de ser referenciado
	# if fluxo == ['F2']:
	# 	del fluxo[-1]

	if len(fluxo) > 0:
		p_this_token['fluxo_pos'] = fluxo

def injetarTemposVerbais(p_dict):

	for k in FORMAS_VERBAIS_AUXILIARES.keys():

		for forma in FORMAS_VERBAIS_AUXILIARES[k]:
			if forma in p_dict.keys():
				if not 'verbo' in p_dict[forma]:
					raise RuntimeError(f"... ja existe '{forma}' em parts_of_speech.json e nao esta marcado como verbo")		
			else:
				p_dict[forma] = ['verbo']

def query_wiktionary(p_word):

	url = WIKTIONARY_URL
	qurl = url.format(p_word)

	ret = []

	sleep(WIKTIONARY_SLEEP)

	r = requests.get(qurl, headers={
		'content-type': 'application/json; charset=utf-8; profile="https://www.mediawiki.org/wiki/Specs/definition/0.8.1"',
		"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:153.0) Gecko/20100101 Firefox/153.0"
		})

	if r.status_code == 200:
		resp = r.json()
		if 'pt' in resp.keys():
			for el in resp['pt']:
				if 'partOfSpeech' in el.keys():
					ret.append(el['partOfSpeech'])

	return ret
 
def update_parts_of_speech_dict(p_pos_dict, p_word_list: list[str], opt_out_path: str = None):
	
	# pos_dict = None
	# with open(os.path.join('setup', 'part_of_speech.json'), 'r', encoding='utf-8') as fp: 
	# 	pos_dict = json.load(fp)	

	ret = {}
	newposs = []

	for w in tqdm(p_word_list):

		if not w in p_pos_dict.keys() or len(p_pos_dict[w]) == 0:

			del newposs[:]
			poss = query_wiktionary(w)

			for p in poss:
				if p == 'Noun':
					r = 'nome'
				elif p == 'Verb':
					r = 'verbo'
				elif p == 'Participle':
					r = 'participio'
				elif p == 'Adjective':
					r = 'adjetivo'
				elif p == 'Pronoun':
					r = 'pronome'
				elif p == 'Determiner':
					r = 'determinante'
				elif p == 'Conjunction':
					r = 'conjuncao'
				elif p == 'Preposition':
					r = 'preposicao'
				elif p == 'Adverb':
					r = 'adverbio'
				elif p == 'Interjection':
					r = 'interjeicao'
				elif p == 'Conjunction':
					r = 'conjuncao'
				elif p == 'Contraction':
					r = 'contracao'
				elif p == 'Particle':
					r = 'particula'					
				elif p == 'Numeral':
					r = 'numeral'	
				elif p == 'Letter':
					r = 'letra'				
				else:
					r = 'INDEF'
				if not r in newposs:
					newposs.append(r)
			# print(">>", w, poss, newposs)

			if len(newposs) > 0:
				ret[w] = copy(newposs)

			if not opt_out_path is None:

				find_unserializable(ret)

				with open(opt_out_path, 'w', encoding='utf-8') as fp:
					json.dump(ret, fp, indent=4, ensure_ascii=False)

		# time.sleep(1)

	find_unserializable(ret)

	if opt_out_path is None:
		p_pos_dict.update(ret)
	else:
		with open(opt_out_path, 'w', encoding='utf-8') as fp:
			json.dump(ret, fp, indent=4, ensure_ascii=False)

def presenca_nomes_proprios(p_part_of_speech_dict: dict, p_token_list: list[str]) -> list[int]:

	ret = []

	nomes = None
	with open(os.path.join('setup', 'nomes_proprios.json'), 'r', encoding='utf-8') as fp: 
		nomes = json.load(fp)

	seps = ['da', 'do', 'de', 'e']

	collected_token_indexes = []

	pairs_list = [None] + p_token_list
	for i, tkns in [(i, pairs_list[i:i+2]) for i in range(len(p_token_list))]:
		prevt, tkn = tkns
		if 'repr' in tkn.keys() and tkn['repr'] in nomes:
			collected_token_indexes.append(i)
		else:
			if 'repr' in tkn.keys() and tkn['repr'] in seps and 'repr' in prevt.keys() and prevt['repr'] in nomes:
				collected_token_indexes.append(i)
			else:
				if len(collected_token_indexes) > 0:
					ret.append(deepcopy(collected_token_indexes))
					del collected_token_indexes[:]

	if len(collected_token_indexes) > 0:
		ret.append(deepcopy(collected_token_indexes))

	return ret

def presenca_nomes_proprios_old(p_part_of_speech_dict: dict, p_words_to_check: list[str]) -> list[int]:
	"""Numa lista de palavras, obter índices das ocorrências de nomes próprios: palavras na lista nomes_proprios.json,
		possívelmente misturadas com artigos, preposições, conjunções, etc.

		Como nomes_proprios,json contém expressões além de palavras indiividualizadas, 
		esta análise é executada a partir da separação prévia das palavras constituntes das expressões.

		Retorna lista de índices numéricos.

		p_words_to_check -- lista de palavras, janela de texto fornecida
	"""

	ret = None

	nomes = None
	with open(os.path.join('setup', 'nomes_proprios.json'), 'r', encoding='utf-8') as fp: 
		nomes = json.load(fp)	

	assert not nomes is None

	pos_dict = p_part_of_speech_dict
	# with open(os.path.join('setup', 'part_of_speech.json'), 'r', encoding='utf-8') as fp: 
	# 	pos_dict = json.load(fp)

	assert not pos_dict is None

	interm_palavras = [pal for pal in pos_dict.keys() if 'artigo' in pos_dict[pal] or 'preposicao' in pos_dict[pal]]


	# Colocar todas as palavras em teste em minúscula
	words_to_check = [t.lower() for t in p_words_to_check]

	#print("words_to_check:", words_to_check)

	# Posições de palavras na janela de texto fornecida, conjunto no qual sera entregue o resultado
	found_indexes = set([])

	for nome in nomes:

		nome_splits = [t.lower() for t in nome.split()]
		if len(nome_splits) == 1:
			ns = nome_splits[0]
			fdidxs = [i for i, x in enumerate(words_to_check) if x == ns]
			found_indexes.update(fdidxs)
		elif len(nome_splits) > 1:
			# vamos preparar um resultado parcial em this_found_indexes
			this_found_indexes = set([])
			for ns in nome_splits:
				this_found_indexes.update([i for i, x in enumerate(words_to_check) if x == ns])
			lfidxs = len(this_found_indexes)
			if lfidxs > 0:
				# se indices encontrados agora forem consecutivos, juntar ao resultado global
				if len(nome_splits) == lfidxs and lfidxs == max(this_found_indexes) - min(this_found_indexes) + 1:
					found_indexes.update(this_found_indexes)

	# A esta altura, found_indexes contém os indíces numéricos das posições nas quais ocorre, na janela de texto
	#  fornecida,  uma palavra de nome próprio
	# Ao reconstruir nomes próprios verdadeiros, apenas usando as palavras identificadas nesta lista,
	#  os nomes resultantes podem estar incompletos por carecerem de artigos, preposições, palavras essas
	#  que estão reunidas em interm_palavras.
	# De seguida, vamos tentar encontrar essas palavras ISOLADAS em posiçoes interméidas, deixadas livres
	#  entre dois nomes.
					
	if len(found_indexes) > 0:
		
		prevlen = 0
		while len(found_indexes) > prevlen:

			stridxes_list = [None] + list(sorted(found_indexes)) + [None]
			# Janela tripla contendo: valor anterior (possívelmente nulo), valor corrente, valor seguinte (possivelmente nulo)
			# Vamos iterar essa janela ao longo da lista stridxes_list
			for pv, cv, nv in [stridxes_list[i:i+3] for i in range(len(found_indexes))]:
				idxs_to_test = set([])
				if not pv is None and cv - pv > 1:
					idxs_to_test.add(pv + 1)
				if not nv is None and nv - cv > 1:
					idxs_to_test.add(cv + 1)
				if len(idxs_to_test) > 0:
					for idx_to_test in idxs_to_test:
						if words_to_check[idx_to_test] in interm_palavras:
							found_indexes.add(idx_to_test)

			prevlen = len(found_indexes)

	return list(sorted(found_indexes))

def presenca_datas(p_tokens_to_check: list[str]) -> list[int]:
	"""Numa lista de tokens, obter índices das ocorrências de datas.

		Retorna lista de índices numéricos.

		p_tokens_to_check -- lista de tokens
	"""

	ret = None
	
	meses = [
		"janeiro", "fevereiro", "março", "abril", "maio", "junho",
		"julho", "agosto", "setembro", "outubro", "novembro", "dezembro"
	]

	found_indexes = []

	tokens_to_check = p_tokens_to_check

	all_triplets_list = 2 * [None] + tokens_to_check + 2 * [None]
	for i, tkns in enumerate([all_triplets_list[i:i+5] for i in range(len(tokens_to_check))]):
		atkn, btkn, ctkn, dtkn, etkn = tkns
		if not atkn is None and not btkn is None and not ctkn is None:
			if 'eliminar' in atkn.keys() or 'eliminar' in btkn.keys() or 'eliminar' in ctkn.keys():
				continue
			if 'pos' in atkn.keys() and 'repr' in btkn.keys() and 'repr' in ctkn.keys():
				if 'numero' in atkn['pos'] and btkn['repr'] == 'de' and ctkn['repr'] in meses:
					found = False
					if not dtkn is None and not etkn is None:
						if 'repr' in dtkn.keys() and 'pos' in etkn.keys() and not 'eliminar' in dtkn.keys() and not 'eliminar' in etkn.keys():
							if dtkn['repr'] == 'de' and 'numero' in etkn['pos']:
								found = True
								found_indexes.append([i-2, i-1, i, i+1, i+2])
					if not found:	
						found_indexes.append([i-2, i-1, i])

	return list(sorted(found_indexes))


# if __name__ == "__main__":
# 	read_all_pos()





if __name__ == "__main0__":

	print("ok")

	pos_dict = None
	with open(os.path.join('setup', 'part_of_speech.json'), 'r', encoding='utf-8') as fp: 
		pos_dict = json.load(fp)

	assert not pos_dict is None

	print(sorted([pal for pal in pos_dict.keys() if 'artigo' in pos_dict[pal] ]))
		
