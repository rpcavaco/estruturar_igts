
import re
import json

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
			"titulo": (r"^título[\s]+([LCIVX]+)", re.I),
			"anexo": (r"^ANEXO[\s]+.*",),
			"artigo_com_tit": (r"^artigo[\s]+([\d]+)[\.]?º[\s]+[\-]?[\s]?(.*)$", re.I),
			"artigo": (r"^artigo[\s]+([\d]+)[\.]?º", re.I),
			"numdentroartigo": (r"^([\d]+)[\s]?\-[\s]?(.*)",),
			"alinea": (r"^([a-b]?[a-z])\)[\s]+(.*)",),
			"subalinea": (r"^([ivx]+)\)[\s]+(.*)",)  # Atenção: confunde-se com a 'alínea' no caso 'i)'
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
		self.designacao = None
		self.textlines = []
		self.children = []
		self.prevnode = None
		
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

		# print("match_dict:", match_dict)

		if self.start < 0:
			self.start = p_line_index


		for mk, mvalues in match_dict.items():

			if mk == '_raw':

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

			elif mk == 'aviso':

				text_line, ato_num_str = mvalues
				self._tipoato = "Aviso"
				self._numeroato = ato_num_str

				self.stop = p_line_index

			elif mk == 'titulo':

				text_line, titulo_num_str = mvalues
				assert self.roman_nr.checkIsRoman(titulo_num_str), text_line

				if self._typestr != 'ROOT':
					anc = self.backToAncestorOfTypes(self, ['ROOT'])
					assert not anc is None
					anc.children.append(DocNode('TITULO'))
					ret = anc.children[-1]
					ret.prevnode = anc
				else:
					self.children.append(DocNode('TITULO'))
					ret = self.children[-1]
					ret.prevnode = self

				ret.start = p_line_index
				ret.stop = p_line_index
				ret._numerostr = titulo_num_str
				ret._titlestr = text_line

			elif mk == 'artigo' or mk == 'artigo_com_tit':

				if mk == 'artigo_com_tit':
					text_line, art_num_str, art_tit = mvalues
				else:
					text_line, art_num_str = mvalues

				if self._typestr != 'TITULO':
					anc = self.backToAncestorOfTypes(self, ['TITULO'])
					assert not anc is None
					anc.children.append(DocNode('ARTIGO'))
					ret = anc.children[-1]
					ret.prevnode = anc
				else:
					self.children.append(DocNode('ARTIGO'))
					ret = self.children[-1]
					ret.prevnode = self

				ret.start = p_line_index
				ret.stop = p_line_index
				ret._numerostr = art_num_str
				ret._titlestr = f"Artigo {art_num_str}.º"

				if mk == 'artigo_com_tit':
					ret.designacao = art_tit

			elif mk == 'numdentroartigo':

				text_line, num_str, num_txt = mvalues

				if self._typestr != 'ARTIGO':
					anc = self.backToAncestorOfTypes(self, ['ARTIGO'])
					assert not anc is None
					anc.children.append(DocNode('NUMERO'))
					ret = anc.children[-1]
					ret.prevnode = anc
				else:
					self.children.append(DocNode('NUMERO'))
					ret = self.children[-1]
					ret.prevnode = self
				
				ret.start = p_line_index
				ret.stop = p_line_index
				ret._numerostr = num_str

				ret.textlines.append(num_txt)

			elif mk == 'alinea':

				text_line, num_str, num_txt = mvalues

				ordval = p_alinea_itens.index(num_str) + 1

				if not self._typestr in ['ARTIGO', 'NUMERO']:
					anc = self.backToAncestorOfTypes(self, ['ARTIGO', 'NUMERO'])
					assert not anc is None
					anc.children.append(DocNode('ALINEA'))
					ret = anc.children[-1]
					ret.prevnode = anc
				else:
					self.children.append(DocNode('ALINEA'))
					ret = self.children[-1]
					ret.prevnode = self
				
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

		if self._ordem > 0:
			ret["ordem"] = self._ordem

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

			curr_node = curr_node.addTextString(alinea_itens, strp_line, lnidx)

	if not p_root_node is None:

		# ajustar os valores de stop
		walkSetAncestorStop(p_root_node)

		with open(p_out_path, 'w', encoding='utf-8') as fp:
			json.dump(p_root_node.toJSON(), fp, indent=4, ensure_ascii=False, cls=DocNode.Encoder)



