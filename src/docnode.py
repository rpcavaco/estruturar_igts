from uuid import uuid4
from json import dumps
from datetime import datetime

VERSION = 0.1

class NoAttrsError(Exception):
    pass


class DocNode(object):
	"""Nó de Documento Regulamentar.
		Um nó raiz contém a totalidade de um documento.
	"""

	def fromJSON(p_json_obj):
		if p_json_obj['typestr'] == 'ROOT':
			current_node = DocNode()
		else:
			current_node = DocNode(typestr=p_json_obj['typestr'])
		if 'id' in p_json_obj.keys():
			current_node.setID(p_json_obj['id'])
		if 'attrs' in p_json_obj.keys():
			current_node.attrs = p_json_obj['attrs']
		if 'children' in p_json_obj.keys():
			for chld in p_json_obj['children']:
				current_node.addSiblingFromJSON(chld)
		return current_node
	
	def artigoToStrBuf(p_artigo):
		buf = [
			f"Artigo {p_artigo['num']}.º",
			f"{p_artigo['tit']}"
		]
		if 'cont' in p_artigo.keys():
			if 'txt' in p_artigo['cont'].keys():
				buf.append(p_artigo['cont']['txt'].replace('\\n', '\n').replace('\\t', '\t'))
			for k in p_artigo['cont'].keys():
				if k[0].isdigit():
					if 'txt' in p_artigo['cont'][k].keys():
						buf.append(f"{k} - {p_artigo['cont'][k]['txt'].replace('\\n', '\n').replace('\\t', '\t')}")
				else:

					if k != 'txt':
						try:
							if 'txt' in p_artigo['cont'][k].keys():
								buf.append(f"{k}) {p_artigo['cont'][k]['txt'].replace('\\n', '\n').replace('\\t', '\t')}")
						except:
							print(f"{p_artigo['num']} {k} {p_artigo['cont'][k]}")
							raise

				if k !='txt' and 'children' in p_artigo['cont'][k].keys():

					for chldk in p_artigo['cont'][k]['children'].keys():
						
						chld = p_artigo['cont'][k]['children'][chldk]
						buf.append(f"{chldk}) {chld['txt'].replace('\\n', '\n').replace('\\t', '\t')}")

						if 'children' in chld.keys():
							for chldkk in chld['children'].keys():
								chldd = chld['children'][chldkk]
								if 'txt' in chldd.keys():
									if chldkk[0].isdigit():
										buf.append(f"({chldkk}) {chldd['txt'].replace('\\n', '\n').replace('\\t', '\t')}")
									else:
										buf.append(f"{chldkk}) {chldd['txt'].replace('\\n', '\n').replace('\\t', '\t')}")

		return buf

	def __init__(self, parent=None, typestr=None, id=None):
		self.parent = parent
		self.attrs = None
		if typestr is None:
			assert id is None
			self.typestr = 'ROOT'
			self.id = None
			self.ident_ato = None
		else:
			self.typestr = typestr
			if id is None:
				self.id = uuid4()
		self.children = []
	def setID(self, p_id):
		self.id = p_id
	def setIdentAto(self, p_ident: str):
		self.ident_ato = p_ident
	def setParent(self, p_parent_node):
		self.parent = p_parent_node
	def addSiblingFromJSON(self, p_json_node):
		self.children.append(DocNode.fromJSON(p_json_node))
		newnode = self.children[-1]
		newnode.setParent(self)
	def addEmptySibling(self, p_typestr):
		if len(self.children) > 0 and self.children[-1].attrs is None:
			raise RuntimeError("já tem último filho vazio")
		self.children.append(DocNode(self, p_typestr))
	def addEmptySibling2LastSibling(self, p_typestr):
		current = self.children[-1]
		if len(current.children) > 0 and current.children[-1].attrs is None:
			raise RuntimeError("já tem último filho vazio")
		current.children.append(DocNode(self, p_typestr))
		return current
	def setLastSiblingAttrs(self, p_dict):
		if self.children[-1].attrs is None:
			self.children[-1].attrs = {}
		self.children[-1].attrs.update(p_dict)
	def toJSON(self, partial=False):
		ret = {
			"typestr": self.typestr
		}

		if self.typestr == "ROOT":
			ret.setdefault('metadados', {})
			ret["metadados"]["assinatura"] = f"Documento DocNode, versão {VERSION}"
			if not self.ident_ato is None:
				ret["metadados"]["ato_normativo"] = self.ident_ato

			ret["metadados"]["timestamp_geracao"] = datetime.now().isoformat()

		if not self.attrs is None:
			if partial:
				ret["attrs"] = {key: self.attrs[key] for key in self.attrs if key in ('tit', 'design')}
			else:
				ret["attrs"] = self.attrs

		if not self.id is None:
			ret["id"] = str(self.id)

		if not partial and len(self.children) > 0:
			ret["children"] = [c.toJSON() for c in self.children]

		return ret
	
	def __repr__(self):
		return dumps(self.toJSON(partial=True))
	
	# def __iter__(self):
	# 	return self
	
	# def __next__(self):

	
	def nextChild(self):
		for ch in self.children:
			yield ch

	def nextArtigo(self):
		if not 'artigos' in self.attrs.keys():
			raise NoAttrsError()
		for art in self.attrs['artigos']:
			yield art

	def typeHierarchy(self):
		curr_node = self
		ret = [curr_node.typestr]
		while not curr_node.parent is None:
			curr_node = curr_node.parent
			ret.append(curr_node.typestr)
		return list(reversed(ret))
	def siblingTypes(self):
		ret = []
		for c in self.children:
			if not c.typestr in ret:
				ret.append(c.typestr)
		return ret

