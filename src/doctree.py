
import re
import json
import traceback

from uuid import uuid4
from typing import Optional, Union, List, Literal
from copy import copy, deepcopy
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
			"anexo": (r"^anexo[\s]+([cilmvx]+)", re.I),
			"artigo_com_tit": (r"^artigo[\s]+([\d]+)[\.]?º[\s]+[\-]?[\s]?(.*)$", re.I),
			"artigo": (r"^artigo[\s]+([\d]+)[\.]?º?", re.I),
			"numero": (r"^([\d]+)[\s]?\-[\s]?(.*)",),
			"uopg_numero": (r"^([S]?UOPG[\s]+[\d]+)[\s]?\-[\s]?(.*)",),
			"alinea": (r"^([a-z]?[a-z])\)[\s]+(.*)",),
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

		while not current.prevnode is None:

			current = current.prevnode

			prevord = 0
			if len(current.children) > 0:
				prevord = max([c._ordem for c in current.children])

			if p_ordval > 0 and p_ordval == prevord + 1:
				ret = { "node": current, "tipo_numeracao": "normal" }
				break
			else:
				if p_roman_val > 0 and p_roman_val == prevord + 1:
					ret = { "node": current, "tipo_numeracao": "romana" }
					break

		return ret

	@classmethod
	def backToAncestorOfTypes(cls, p_this: 'DocNode', p_types: List[str]) -> Union['DocNode', None]:

		ret = None

		current = p_this

		while not current.prevnode is None:
			current = current.prevnode
			if current._typestr in p_types:
				ret = current
				break

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

	def addTextString(self, p_alinea_itens: List[str], p_text: str, p_line_index: int) -> 'DocNode':

		ret = None
		strip_text = p_text.strip()

		match_dict = {}
		self.dtp.parseString(strip_text, match_dict)

		if self.start < 0:
			self.start = p_line_index

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
				anc = DocNode.backToAncestorOfTypes(self, ['ROOT'])
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
				anc = DocNode.backToAncestorOfTypes(self, ['ROOT', 'TITULO'])
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

		elif mkeys == ('anexo',):

			mvalues = match_dict[mkeys[0]]

			text_line, num_str = mvalues
			assert self.roman_nr.checkIsRoman(num_str), text_line

			if self._typestr != 'ROOT':
				anc = DocNode.backToAncestorOfTypes(self, ['ROOT'])
				assert not anc is None
			else:
				anc = self

			anc.children.append(DocNode('ANEXO'))
			ret = anc.children[-1]
			ret.prevnode = anc

			ret.start = p_line_index
			ret.stop = p_line_index
			ret._numerostr = num_str
			ret._titlestr = text_line

		elif 'artigo' in mkeys or 'artigo_com_tit' in mkeys:

			if 'artigo_com_tit' in mkeys:
				text_line, art_num_str, art_tit = match_dict['artigo_com_tit']
			else:
				text_line, art_num_str = match_dict['artigo']

			if self._typestr not in ('TITULO', 'CAPITULO'):
				anc = DocNode.backToAncestorOfTypes(self, ['TITULO', 'CAPITULO'])
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

		elif mkeys == ('numero',) or mkeys == ('uopg_numero',):

			mvalues = match_dict[mkeys[0]]

			text_line, num_str, num_txt = mvalues

			if self._typestr not in ('ANEXO', 'ARTIGO'):
				anc = DocNode.backToAncestorOfTypes(self, ['ANEXO', 'ARTIGO'])
				assert not anc is None, f"numero: {self.id} {text_line}"
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


			alinea_itens = p_alinea_itens


			if 'alinea' in mkeys:
				text_line, num_str, num_txt = match_dict['alinea']
			else:
				text_line, num_str, num_txt = match_dict['alinea_romana']

			assert self._typestr in ('ANEXO', 'ARTIGO', 'NUMERO', 'ALINEA', 'SUBALINEA'), f"{json.dumps(self.toJSON(), indent=4)}, {text_line}"

			# print(mkeys, num_str, text_line)

			roman_val = -1
			ord_val = -1
			if self.roman_nr.checkIsRoman(num_str):
				roman_val = self.roman_nr.fromRomanStr(num_str)
			if len(num_str) <= 2:
				if num_str in alinea_itens:
					ord_val = alinea_itens.index(num_str) + 1


			if self._typestr in ('ANEXO', 'ARTIGO', 'NUMERO'):

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

				anc_ret = DocNode.backToCompatibleAlineaSubalinea(self, ord_val, roman_val)
				
				if not anc_ret["node"] is None:
					anc = anc_ret["node"]
				else:
					# DEveria estar a iniciar nova numeração
					if ord_val != 1 and roman_val != 1:

						# Pode ser, por exemplo, um ii) a seguir a um i) romano que foi interpretado como sendo numeração 'normal', um i) a seguir a um h)

						if (ord_val == 2 or roman_val == 2):

							assert len(self.prevnode.children) >= 2
							anc = self.prevnode.children[-2]
							assert len(anc.children) == 0, f"anc.id:{anc.id}, len.ch:{len(anc.children)}, {json.dumps(self.toJSON(), indent=4)}"

							print("id a mover:", self.prevnode.children[-1].id, num_str)
							print("id anc:", self.prevnode.children[-2].id)

							to_move = self.prevnode.children[-1]
							to_move._ordem = 1
							to_move.tipo_numeracao = "romana"
							anc = self.prevnode.children[-2]
							anc.children.append(deepcopy(to_move))
							del self.prevnode.children[-1]

						else:

							raise RuntimeError(f"Esperado inicio numeracao.\n ord_val:{ord_val} roman_val:{roman_val} this:{json.dumps(self.toJSON(), indent=4)} text_line:{text_line}")
					else:
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
					if len(anc.children) > 1:
						ret._ordem = anc.children[-2]._ordem + 1
						ret.tipo_numeracao = anc.children[-2].tipo_numeracao
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

		if not ret:
			ret = self

		return ret


	@classmethod
	def fromJSON(cls, p_json_obj):

		if p_json_obj['tipo'] == 'ROOT':
			current_node = DocNode()
		else:
			current_node = DocNode(typestr=p_json_obj['tipo'])

		for item in [
			   "id", "start", "stop", "numero"
			   # "subalinea_level"
			 ]:
			if item in p_json_obj.keys():
				setattr(current_node, item, p_json_obj[item])

		if "numero" in p_json_obj.keys():
			current_node._numerostr = p_json_obj["numero"]

		if "ordem" in p_json_obj.keys():
			current_node._ordem = p_json_obj["ordem"]

		if "tipo_numeracao" in p_json_obj.keys():
			current_node.tipo_numeracao = p_json_obj["tipo_numeracao"]

		if 'attrs' in p_json_obj.keys():

			if "tipo_ato_normativo" in p_json_obj['attrs'].keys():
				current_node._tipoato = p_json_obj['attrs']["tipo_ato_normativo"]

			if "numero_ato_normativo" in p_json_obj['attrs'].keys():
				current_node._numeroato = p_json_obj['attrs']["numero_ato_normativo"]

			if "titulo" in p_json_obj['attrs'].keys():
				current_node._titlestr = p_json_obj['attrs']["titulo"]

			if "designacao" in p_json_obj['attrs'].keys():
				current_node.designacao = p_json_obj['attrs']["designacao"]

		if 'children' in p_json_obj.keys():
			for chld in p_json_obj['children']:
				chld_node = DocNode.fromJSON(chld)
				chld_node.prevnode = current_node
				current_node.children.append(chld_node)
		if "texto" in p_json_obj.keys():
			for ln in p_json_obj["texto"]:
				current_node.textlines.append(ln)

		return current_node

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

		try:
			if self.subalinea_level > 0:
				ret["subalinea_level"] = self.subalinea_level
		except: 
			print("subalinea_level:", self.subalinea_level)
			raise

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


def parseFromText(p_in_path: str, p_out_path: str, p_root_node: 'DocNode', tipo_numeracao_alineas: Literal["TIPO1", "TIPO2"], limit: Optional[int] = 0):

	assert not p_root_node is None

	curr_node = p_root_node

	alinea_itens = [c for c in ALFACHARS]
	if tipo_numeracao_alineas == 'TIPO1':
		for c in ALFACHARS:
			for d in ALFACHARS:
				alinea_itens.append(c+d)
	else:
		for c in ALFACHARS:
			alinea_itens.append(c+c)

	with open(p_in_path, 'r', encoding='utf-8') as fp:
		
		for _lnidx, ln in enumerate(fp):

			lnidx = _lnidx + 1

			strp_line = ln.strip()
			if len(strp_line) == 0:
				continue

			if limit > 0 and lnidx > limit:
				break

			try:
				ret_curr_node = curr_node.addTextString(alinea_itens, strp_line, lnidx)
				if not ret_curr_node is None:
					curr_node = ret_curr_node
			except:
				traceback.print_exc()
				break

	if not p_root_node is None:

		# ajustar os valores de stop
		walkSetAncestorStop(p_root_node)

		with open(p_out_path, 'w', encoding='utf-8') as fp:
			json.dump(p_root_node.toJSON(), fp, indent=4, ensure_ascii=False, cls=DocNode.Encoder)


def traverseNodes(p_node, p_out_dict, the_path=None, level=0):

	nextkey = len(p_out_dict.keys()) + 1

	p_out_dict[nextkey] = { "p": [], "c": []}

	if not the_path is None:
		p_out_dict[nextkey]["p"].extend(the_path)

	p_out_dict[nextkey]["p"].append(p_node["id"])

	if "attrs" in p_node.keys():
		if "titulo" in p_node["attrs"].keys():
			p_out_dict[nextkey]["c"].append(p_node["attrs"]["titulo"])
		if "designacao" in p_node["attrs"].keys():
			p_out_dict[nextkey]["c"].append(p_node["attrs"]["designacao"])

	if "texto" in p_node.keys():
		for ln in p_node["texto"]:
			p_out_dict[nextkey]["c"].append(ln)

	if "children" in p_node.keys():
		for ci, chld_node in enumerate(p_node["children"]):
			traverseNodes(chld_node, p_out_dict, the_path=p_out_dict[nextkey]["p"], level=level+1)


