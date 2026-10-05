
import re
import json
import traceback

from uuid import uuid4
from typing import Optional, Union, List
from copy import copy
from datetime import datetime

from nlp import NumeracaoRomana

VERSION = 0.2

COMPRIM_MAX_TITULO_INTRO = 60

ALFACHARS = "abcdefghijklmnopqrstuvwxyz"

class DocTextParser(object):

	def __init__(self):
		self.patt = {
			"aviso": (r"^aviso[\s]+n[\.]?º[\s]+(\S+)", re.I),
			"titulo": (r"^título[\s]+([cilmvx]+)", re.I),
			"capitulo": (r"^capítulo[\s]+([cilmvx]+)", re.I),
			"anexo": (r"^anexo[\s]+.*", re.I),
			"artigo_com_tit": (r"^artigo[\s]+([\d]+)[\.]?º[\s]+[\-]?[\s]?(.*)$", re.I),
			"artigo": (r"^artigo[\s]+([\d]+)[\.]?º?", re.I),
			"numdentroartigo": (r"^([\d]+)[\s]?\-[\s]?(.*)",),
			"alinea": (r"^([a-b]?[a-z])\)[\s]+(.*)",),
			"alinea_romana": (r"^([cilmvx]+)\)[\s]+(.*)",)  # Atenção: confunde-se com a 'alínea' no caso 'i)'
		}

	def parseString(self, p_text: str, out_mos_dict: dict):

		out_mos_dict.clear()

		for k, v in self.patt.items():

			if len(v) == 2:				
				patt, flag = v
			else:
				patt = v[0]
				flag = None
			if flag is None:
				mo = re.match(patt, p_text)
			else:
				mo = re.match(patt, p_text, flag)

			if not mo is None:
				out_mos_dict[k] = [mo.group(0)]
				out_mos_dict[k].extend(copy(mo.groups()))

		if 'artigo' in out_mos_dict.keys():
			if 'artigo_com_tit' in out_mos_dict.keys():
				del out_mos_dict['artigo']

		if not out_mos_dict:
			out_mos_dict['_raw'] = [p_text]

class DocNode(object):
	"""Nó de Documento Regulamentar.
		Um nó raiz contém a totalidade de um documento.
	"""

	class Encoder(json.JSONEncoder):
		def default(self, o):
			return o.__dict__

	@classmethod
	def backToCompatibleAlineaSubalinea(cls, p_this: 'DocNode', p_ordval: int, p_roman_val: int) -> Union['DocNode', None]:

		ret = { "node": None, "tipo_numeracao": None }

		current = p_this

		# print(" ")
		# print(":: p_ordval, p_roman_val:", p_ordval, p_roman_val, "current:", current.id, current._typestr)

		while not current.prevnode is None:

			current = current.prevnode

			prevord = 0
			if len(current.children) > 0:
				prevord = max([c._ordem for c in current.children])

			# print("      > prev:", current.id, current._typestr, "prevord:", prevord, "len.ch:", len(current.children))

			# if p_ordval == 9 and p_roman_val == 1:
			# 	print("     9 1:", prevord, json.dumps(current.toJSON(), indent=4), json.dumps(p_this.toJSON(), indent=4), "prev is none:", (not current.prevnode is None))

			# print("::::", p_ordval > 0 and p_ordval == prevord + 1, p_roman_val > 0 and p_roman_val == prevord + 1, prevord, p_ordval, p_roman_val, json.dumps(current.toJSON(), indent=4))
			# print(":::: > ", json.dumps(p_this.toJSON(), indent=4))

			if p_ordval > 0 and p_ordval == prevord + 1:
				ret = { "node": current, "tipo_numeracao": "normal" }
				break
			elif p_roman_val > 0 and p_roman_val == prevord + 1:
#				print("ret:", json.dumps(current.toJSON(), indent=4))
				ret = { "node": current, "tipo_numeracao": "romana" }
				break

		# if not ret["node"] is None:
		# 	print("    ret >", ret["node"].id, ret["node"]._typestr, "tipo_numeracao:", ret["tipo_numeracao"])
		# else:
		# 	print("    ret > NULL")			

		return ret

	def __init__(self, typestr: Optional[str] = None):

		self.id = uuid4()
		if typestr is None:
			self._typestr = 'ROOT'
		else:
			self._typestr = typestr
		self._titlestr = None
		self._numerostr = None
		self._tipoato = None
		self._numeroato = None
		self._ordem = -1

		self.start = -1
		self.stop = -1
		self.tipo_numeracao = None
		self.designacao = None
		self.textlines = []
		self.children = []
		self.prevnode = None
		self.subalinea_level = -1
		
		self.dtp = DocTextParser()
		self.roman_nr = NumeracaoRomana()

		@property
		def tipo(self) -> str:
			return self._typestr

		@tipo.setter
		def tipo(self, value: str):
			self._typestr = value

		@property
		def titulo(self) -> str:
			return self._titlestr

		@titulo.setter
		def titulo(self, value: str):
			self._titlestr = value

		@property
		def tipo_ato_normativo(self) -> str:
			return self._tipoato

		@tipo_ato_normativo.setter
		def tipo_ato_normativo(self, value: str):
			self._tipoato = value

		@property
		def numero_ato_normativo(self) -> str:
			return self._numeroato

		@numero_ato_normativo.setter
		def numero_ato_normativo(self, value: str):
			self._numeroato = value

		@property
		def numero(self) -> str:
			return self._numerostr

		@numero.setter
		def numero(self, value: str):
			self._numerostr = value

		@property
		def ordem(self) -> int:
			return self._ordem

		@ordem.setter
		def ordem(self, value: int):
			self._ordem = value

	def backToAncestorOfTypes(self, p_this: 'DocNode', p_types: List[str]) -> Union['DocNode', None]:

		ret = None

		current = p_this

		while not current.prevnode is None:
			current = current.prevnode
			if current._typestr in p_types:
				ret = current
				break

		return ret

	def addTextString(self, p_alinea_itens: List[str], p_text: str, p_line_index: int) -> 'DocNode':

		ret = None
		strip_text = p_text.strip()

		match_dict = {}
		self.dtp.parseString(strip_text, match_dict)

		# if len(match_dict.keys()) > 1:
		# 	print("match_dict:", match_dict.keys())

		if self.start < 0:
			self.start = p_line_index

		#for mk, mvalues in match_dict.items():

		mkeys = tuple(match_dict.keys())

		# print("\n", mkeys, strip_text)

		if mkeys == ('_raw',):

			if self._typestr == "ROOT":

				self._titlestr = strip_text
				self.children.append(DocNode('INTRO'))
				self.stop = p_line_index

				ret = self.children[-1]
				ret.prevnode = self

			elif self._typestr == "INTRO":

				if self._titlestr is None and len(self.textlines) == 0 and len(strip_text) < COMPRIM_MAX_TITULO_INTRO:
					self._titlestr = strip_text
				else:
					self.textlines.append(strip_text)

				self.stop = p_line_index

			elif self._typestr in ("ARTIGO", "TITULO"):

				if self.designacao is None:
					self.designacao = strip_text
				else:
					self.textlines.append(strip_text)

				self.stop = p_line_index

		elif mkeys == ('aviso',):

			mvalues = match_dict[mkeys[0]]

			text_line, ato_num_str = mvalues
			self._tipoato = "Aviso"
			self._numeroato = ato_num_str

			self.stop = p_line_index

		elif mkeys == ('titulo',):

			mvalues = match_dict[mkeys[0]]

			text_line, titulo_num_str = mvalues
			assert self.roman_nr.checkIsRoman(titulo_num_str), text_line

			if self._typestr != 'ROOT':
				anc = self.backToAncestorOfTypes(self, ['ROOT'])
				assert not anc is None
			else:
				anc = self

			anc.children.append(DocNode('TITULO'))
			ret = anc.children[-1]
			ret.prevnode = anc

			ret.start = p_line_index
			ret.stop = p_line_index
			ret._numerostr = titulo_num_str
			ret._titlestr = text_line

		elif mkeys == ('capitulo',):

			mvalues = match_dict[mkeys[0]]

			text_line, titulo_num_str = mvalues
			assert self.roman_nr.checkIsRoman(titulo_num_str), text_line

			if self._typestr not in ['ROOT', 'TITULO']:
				anc = self.backToAncestorOfTypes(self, ['ROOT', 'TITULO'])
				assert not anc is None
			else:
				anc = self

			anc.children.append(DocNode('CAPITULO'))
			ret = anc.children[-1]
			ret.prevnode = anc

			ret.start = p_line_index
			ret.stop = p_line_index
			ret._numerostr = titulo_num_str
			ret._titlestr = text_line

		elif 'artigo' in mkeys or 'artigo_com_tit' in mkeys:

			if 'artigo_com_tit' in mkeys:
				text_line, art_num_str, art_tit = match_dict['artigo_com_tit']
			else:
				text_line, art_num_str = match_dict['artigo']

			if self._typestr not in ('TITULO', 'CAPITULO'):
				anc = self.backToAncestorOfTypes(self, ['TITULO', 'CAPITULO'])
				assert not anc is None, f"Ascendente nulo em 'artigo', tipo '{self._typestr}', chaves parsing: {mkeys}, linha de texto: {text_line}"
			else:
				anc = self

			anc.children.append(DocNode('ARTIGO'))
			ret = anc.children[-1]
			ret.prevnode = anc

			ret.start = p_line_index
			ret.stop = p_line_index
			ret._numerostr = art_num_str
			ret._titlestr = f"Artigo {art_num_str}.º"

			if 'artigo_com_tit' in mkeys:
				ret.designacao = art_tit

		elif mkeys == ('numdentroartigo',):

			mvalues = match_dict[mkeys[0]]

			text_line, num_str, num_txt = mvalues

			if self._typestr != 'ARTIGO':
				anc = self.backToAncestorOfTypes(self, ['ARTIGO'])
				assert not anc is None
			else:
				anc = self

			anc.children.append(DocNode('NUMERO'))
			ret = anc.children[-1]
			ret.prevnode = anc
			
			ret.start = p_line_index
			ret.stop = p_line_index
			ret._numerostr = num_str

			ret.textlines.append(num_txt)

		elif 'alinea_romana' in mkeys or 'alinea' in mkeys:

			assert self._typestr in ('ARTIGO', 'NUMERO', 'ALINEA', 'SUBALINEA'), json.dumps(self.toJSON(), indent=4)

			if 'alinea' in mkeys:
				text_line, num_str, num_txt = match_dict['alinea']
			else:
				text_line, num_str, num_txt = match_dict['alinea_romana']

			roman_val = -1
			ord_val = -1
			if self.roman_nr.checkIsRoman(num_str):
				roman_val = self.roman_nr.fromRomanStr(num_str)
			if len(num_str) == 1:
				ord_val = p_alinea_itens.index(num_str) + 1


			if self._typestr in ('ARTIGO', 'NUMERO'):

				self.children.append(DocNode('ALINEA'))
				ret = self.children[-1]
				ret.prevnode = self
				# A iniciar nova numeração
				assert ord_val == 1 or roman_val == 1
				if ord_val == 1:
					ret.tipo_numeracao = "normal"
				else:
					ret.tipo_numeracao = "romana"
				ret._ordem = 1

			else:

				# Apenas self._typestr 'ALINEA' ou 'SUBALINEA'




				# if roman_val == 1: # potencialmente, a iniciar nova série de subalíneas i), ii), iii) ...

				# 	if ord_val > 0:
				# 		get_prev_ord(self)


				# print("372: ", ord_val, roman_val, json.dumps(self.prevnode.toJSON(), indent=4), json.dumps(self.toJSON(), indent=4), text_line)

				# raise RuntimeError("##")
			
				anc_ret = DocNode.backToCompatibleAlineaSubalinea(self, ord_val, roman_val)
				if not anc_ret["node"] is None:
					anc = anc_ret["node"]
				else:
					# A iniciar nova numeração
					assert ord_val == 1 or roman_val == 1, f"ord_val:{ord_val} roman_val:{roman_val} this:{json.dumps(self.toJSON(), indent=4)} text_line:{text_line}"
					anc = self

				if anc._typestr == 'NUMERO':
					anc.children.append(DocNode('ALINEA'))
				else: 
					anc.children.append(DocNode('SUBALINEA'))

				ret = anc.children[-1]
				ret.prevnode = anc
				
				if not anc_ret["node"] is None:
					if anc_ret["tipo_numeracao"] == "normal":
						ret._ordem = ord_val
					else:
						ret._ordem = roman_val
					ret.tipo_numeracao = anc_ret["tipo_numeracao"]
				else:
					ret._ordem = 1
					if ord_val == 1:
						ret.tipo_numeracao = "normal"
					else:
						ret.tipo_numeracao = "romana"					



			ret.start = p_line_index
			ret.stop = p_line_index
			ret._numerostr = num_str

			ret.textlines.append(num_txt)				


		elif mkeys == ('alineaZZ',):

			# Necessário distinguir entre alínea a subalinea, ou qualquer nível de sub-subalínea

			real_alinea = False
			if not 'subalinea' in mkeys:

				real_alinea = True

			elif 'alinea' in mkeys: 

				# 'subalinea' e 'alinea': letras isoladas comuns à numeração romana: i) l) c) x) v)
				# podem ser alinea ou subalínea, dependentemente do número de ordem anterior em sequência, se existir
				# Atenção: Por erro, há textos com subalíneas 'numeradas' com letras de 'a' a 'x'

				text_line, num_str, num_txt = match_dict['alinea']
				
				if self._typestr in ('NUMERO', 'ALINEA', 'SUBALINEA'):
					
					tmp_ordval = p_alinea_itens.index(num_str) + 1

					if self._typestr == 'NUMERO':
						real_alinea = (tmp_ordval == 1)	
					elif self._typestr == 'ALINEA':
						prevord = 0
						if len(self.prevnode.children) > 0:
							prevord = max([c._ordem for c in self.prevnode.children])
						print("A >> p t num_str:", prevord, tmp_ordval, num_str)
						real_alinea = (prevord == tmp_ordval - 1)	
					else:  # self._typestr == 'SUBALINEA'
						anc = self.backToAncestorOfTypes(self, ['ALINEA'])
						assert not anc is None
						prevord = 0
						if len(anc.prevnode.children) > 0:
							prevord = max([c._ordem for c in anc.prevnode.children])
						print("B >> p t num_str:", prevord, tmp_ordval, num_str)
						real_alinea = (prevord == tmp_ordval - 1)

				if num_str == 'c':
					print(">>", real_alinea, self._typestr, text_line, json.dumps(self.prevnode.toJSON(), indent=4))

			if real_alinea:

				text_line, num_str, num_txt = match_dict['alinea']
				ordval = p_alinea_itens.index(num_str) + 1

				if not self._typestr in ['ARTIGO', 'NUMERO']:
					anc = self.backToAncestorOfTypes(self, ['ARTIGO', 'NUMERO'])
					assert not anc is None
				else:
					anc = self

				anc.children.append(DocNode('ALINEA'))

			else:

				text_line, num_str, num_txt = match_dict['subalinea']
				assert self.roman_nr.checkIsRoman(num_str), text_line
				ordval = self.roman_nr.fromRomanStr(num_str)

				level = 0
				if self._typestr in ('ALINEA', 'NUMERO'):  # Subalinea pode aparecer como descendente de NUMERO
					level = 1
					anc = self
				elif self._typestr == 'SUBALINEA':
					if ordval == 1:
						anc = self
					else:
						anc = self.backToCompatibleSubalinea(self, ordval)
					assert not anc is None, f"Ascendente nulo, tipo '{self._typestr}', chaves parsing: {mkeys}, linha de texto: {text_line}"
					if anc.subalinea_level < 1:
						level = 1
					else:
						level = anc.subalinea_level + 1
				else:
					raise RuntimeError(f"Tipo corrente '{self._typestr}' inesperado, chaves parsing: {mkeys}, linha de texto: {text_line}")

				anc.children.append(DocNode('SUBALINEA'))
				anc.children[-1].subalinea_level = level

			ret = anc.children[-1]
			ret.prevnode = anc

			ret.start = p_line_index
			ret.stop = p_line_index
			ret._numerostr = num_str
			if ordval > 0:
				ret._ordem = ordval

			ret.textlines.append(num_txt)

		if not ret:
			ret = self

		return ret


	def toJSON(self):

		assert not self._typestr is None

		ret = {
			"id": str(self.id),
			"tipo": self._typestr
		}

		if not self._typestr in ["NUMERO", "ALINEA", "SUBALINEA"]:
			ret["start"] = self.start
			ret["stop"] = self.stop

		if not self._numerostr is None:
			ret["numero"] = self._numerostr

		if not self.tipo_numeracao is None:
			ret["tipo_numeracao"] = self.tipo_numeracao

		if self._ordem > 0:
			ret["ordem"] = self._ordem

		if self.subalinea_level > 0:
			ret["subalinea_level"] = self.subalinea_level

		if self._typestr == "ROOT":
			ret.setdefault('metadados', {})
			ret["metadados"]["assinatura"] = f"Documento DocNode, versão {VERSION}"
			ret["metadados"]["timestamp_geracao"] = datetime.now().isoformat()

		if not self._tipoato is None:
			ret.setdefault('attrs', {})
			ret['attrs']['tipo_ato_normativo'] = self._tipoato
			ret['attrs']['numero_ato_normativo'] = self._numeroato

		if not self._titlestr is None:
			ret.setdefault('attrs', {})
			ret['attrs']['titulo'] = self._titlestr

		if not self.designacao is None:
			ret.setdefault('attrs', {})
			ret['attrs']['designacao'] = self.designacao

		if len(self.textlines) > 0:
			ret['texto'] = copy(self.textlines)

		if len(self.children) > 0:
			ret.setdefault('children', [])
			for chld in self.children:
				ret['children'].append(chld.toJSON())

		return ret

def walkSetAncestorStop(p_node):

	if len(p_node.children) > 0:
		for pt in p_node.children:
			walkSetAncestorStop(pt)

	if not p_node.prevnode is None:
		p_node.prevnode.stop = max(p_node.stop, p_node.prevnode.stop)


def parseFromText(p_in_path: str, p_out_path: str, p_root_node: 'DocNode', limit: Optional[int] = 0):

	assert not p_root_node is None

	curr_node = p_root_node

	alinea_itens = [c for c in ALFACHARS]
	for c in ALFACHARS:
		for d in ALFACHARS:
			alinea_itens.append(c+d)

	with open(p_in_path, 'r', encoding='utf-8') as fp:
		
		for _lnidx, ln in enumerate(fp):

			lnidx = _lnidx + 1

			strp_line = ln.strip()
			if len(strp_line) == 0:
				continue

			# print('>', lnidx, '--', ln.strip())
			# print('>')

			if limit > 0 and lnidx > limit:
				break

			try:
				curr_node = curr_node.addTextString(alinea_itens, strp_line, lnidx)
			except:
				traceback.print_exc()
				break

	if not p_root_node is None:

		# ajustar os valores de stop
		walkSetAncestorStop(p_root_node)

		with open(p_out_path, 'w', encoding='utf-8') as fp:
			json.dump(p_root_node.toJSON(), fp, indent=4, ensure_ascii=False, cls=DocNode.Encoder)



