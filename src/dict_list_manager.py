"""
dict_list_manager.py

A small utility class for managing a list of dictionaries that all share
the same structure (same set of keys), with support for:

- Creating new dictionaries that conform to the shared structure
- Inserting them into the managed list
- Serializing / deserializing the list to and from JSON
- Walking the list and applying an in-place transformation to each item

Example
-------
>>> mgr = DictListManager(schema=<json schema>)
>>> mgr.insert(id=1, name="Alice")
>>> mgr.insert(id=2, name="Bob", active=False)
>>> mgr.walk(lambda item: item.update(name=item["name"].upper()))
>>> print(mgr.to_json())
[
  {
	"id": 1,
	"name": "ALICE",
	"active": true
  },
  ...
]
"""

# from __future__ import annotations

import json
import warnings

from copy import copy, deepcopy
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Type, Tuple

from jsonschema import validate
from jsonschema import Validator, Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError
from validation_helpers import extend_with_default


class SchemaValidationError(Exception):
	"""Raised when a dictionary does not conform to the manager's schema."""

class ConstructValidationError(Exception):
	"""Raised when a construct is invalid."""

class EmptyConstructError(Exception):
	"""Raised when a construct is empty after trimming."""

class DictListManager():
	"""
	Manages a list of dictionaries that all share the same structure.

	Parameters
	----------
	schemas:
		Optional mappings of ``{key_name: expected_type}`` describing the
		required or possible keys of every dictionary in the list, and the type each
		value may or should have. 
	"""

	def __init__(
		self,
		schemas: Optional[List[Dict[str, Type]]] = None
	) -> None:
		self.schemas: List[Dict[str, Type]] = list(schemas) if schemas else []
		self._items: List[Dict[str, Any]] = []
		self.validators = []

		validator_class = None
		for schema in self.schemas:
			if validator_class is None:
				validator_class = extend_with_default(Draft202012Validator)
			self.validators.append(validator_class(schema))

	class Encoder(json.JSONEncoder):
		def default(self, o):
			if isinstance(o, DictListManager):
				return o._items
			elif isinstance(o, Validator):
				return None
			else:
				return o.__dict__
			
	# ------------------------------------------------------------------ #
	# Schema handling
	# ------------------------------------------------------------------ #
	def validate(self, item: Dict[str, Any]) -> None:
		"""Se não tiverem sido definidos schemas, esta validação dá sempre resultado positivo,
			não tenta inferir um schema"""
		if len(self.validators) > 0:
			validation_msgs = []
			for validator in self.validators:
				try:		
					validator.validate(item)
				except (SchemaError, ValidationError) as ve:
					validation_msgs.append(str(ve))
			if len(self.validators) == len(validation_msgs): 
				raise SchemaValidationError("\n".join(validation_msgs))
			else:
				# Se, de todos os validadores existente, um e apenas um deles não produzir mensagem de erro, estamos bem
				assert len(self.validators) - len(validation_msgs) == 1


	# ------------------------------------------------------------------ #
	# Creation / insertion
	# ------------------------------------------------------------------ #
	def create(self, **fields: Any) -> Dict[str, Any]:
		"""
		Build a new dictionary that eventually conforms to the schema, 
		if this was previously defined, filling any
		missing keys from defaults in schema, where available. Does NOT
		insert it into the list — use ``insert`` for that, or pass the
		result to it.
		"""
		item = dict(fields)

		self.validate(item)
		return item

	def insert(
		self,
		item: Optional[Dict[str, Any]] = None,
		index: Optional[int] = None,
		**fields: Any,
	) -> Dict[str, Any]:
		"""
		Insert a dictionary into the managed list.

		Either pass an existing ``item`` dict, or pass keyword fields to
		have one built via ``create()`` first. If ``index`` is given, the
		item is inserted at that position; otherwise it's appended.
		"""
		if item is None:
			item = self.create(**fields)
		else:
			item = dict(item)  # defensive copy
			if fields:
				item.update(fields)
			self.validate(item)

		if index is None:
			self._items.append(item)
		else:
			self._items.insert(index, item)
		return item

	def extend(self, items: Iterable[Dict[str, Any]]) -> None:
		"""Insert several dictionaries at once."""
		for item in items:
			self.insert(item)

	def remove_at(self, index: int) -> Dict[str, Any]:
		"""Remove and return the item at the given index."""
		return self._items.pop(index)

	# ------------------------------------------------------------------ #
	# Walking / in-place transformation
	# ------------------------------------------------------------------ #
	def walk(
		self,
		func: Callable[[Dict[str, Any]], Any],
		predicate: Optional[Callable[[Dict[str, Any]], bool]] = None,
		afterfunc: Optional[Callable[[Dict[str, Any]], Any]] = None,
		validate_after: bool = True
	) -> None:
		"""
		Walk the list and apply ``func`` to each dictionary, in place.

		``func`` receives each dict and may mutate it directly (e.g. via
		``item[k] = v`` or ``item.update(...)``); any return value is
		ignored. Optionally restrict which items are visited with
		``predicate(item) -> bool``. By default, each item is
		re-validated against the schema after ``func`` runs, so a bad
		mutation raises immediately instead of corrupting the list.
		"""
		for item in self._items:
			if predicate is not None and not predicate(item):
				continue
			try:
				func(item)
			except AttributeError as e:
				warnings.warn(f"{e} - item:{item}")
				raise
			if validate_after:
				self.validate(item)
			if not afterfunc is None:
				afterfunc(item)


	def iterateMatches(self, p_words_lists: List[List[str]]) -> None:

		for word_list in p_words_lists:
			lw = len(word_list)
			for i, group in self.iterateGroups(group_size=lw, prev_is_null=False):
				filt_group = [t['repr'] for t in group if 'repr' in t.keys()]
				if len(filt_group) != lw:
					continue
				if filt_group == word_list:
					yield i, [j+i for j in range(lw)]

	def iterNextContiguousConstructElements(
		self,
		predicate: Callable[[Dict[str, Any]], bool],
		testlist: Optional[List[str]] = None
	) -> List[int]:
		found_idxs = []
		fluxo = []
		check_fluxo = False
		for i, item in enumerate(self._items):
			if not testlist is None and 'repr' in item.keys() and item['repr'] in testlist:
				check_fluxo = True
			else:
				check_fluxo = False
			#if check_fluxo:
			if 'construct' in item.keys(): # No multilevel constructs
				if len(fluxo) > 0:
					fluxo.append(f"{item} construct {i}")
			else:
				if predicate(item):
					if check_fluxo:
						fluxo.append(f"{item} predicate OK, append {i}")
					found_idxs.append(i)
				else:
					if len(found_idxs) > 0:
						if check_fluxo:
							fluxo.append(f"{item} predicate NOTOK, yield {i}")
							print("\n".join(fluxo))
							del fluxo[:]
						ret = copy(found_idxs)
						del found_idxs[:]
						yield ret

		if len(fluxo) > 0:
			print("Fluxo final:", "\n".join(fluxo))

	def iterateGroups(self, group_size: int = 1, prev_is_null: bool = False):

		seed = 0
		if group_size > 1 and prev_is_null:
			group = [None] + [el for el in self._items[0:group_size-1]]
			if len(group) == 0:
				return
			yield 0, group
			seed = 1

		for i, item in enumerate(self._items):		
			group = [el for el in self._items[i:i+group_size]]
			if len(group) > 0:
				yield i + seed, group
			else:
				break


	def buildConstruct(self, p_indexes: List[int], p_tag: Dict[str, Any], adic_attribs: Optional[List[Tuple]] = None, right_trimming_func: Optional[Any] = None, validation_func: Optional[Any] = None, paf=None):

		# Verificar que indices são consecutivos
		assert len(p_indexes) > 0 and len(p_indexes) == (p_indexes[-1] - p_indexes[0]) + 1, p_indexes

		srt_idxs = sorted(p_indexes)
		children = []

		idxs_efetivamente_usados = []

		if right_trimming_func is None:
			for idx in srt_idxs:
				children.append(deepcopy(self._items[idx]))
				idxs_efetivamente_usados.append(idx)
		else:

			first_found = False
			for rev_idx in reversed(srt_idxs):
				if not first_found:
					if not paf is None and 'pos' in self._items[rev_idx].keys():
						pass
						# if self._items[rev_idx]['repr'] == 'que':
						# 	print(">> 278:", self._items[rev_idx-1], self._items[rev_idx], paf.intersection(self._items[rev_idx]['pos']))
					if right_trimming_func(self._items[rev_idx]):
						continue
					else:
						first_found = True
				if first_found:
					children.insert(0 ,deepcopy(self._items[rev_idx]))
					idxs_efetivamente_usados.append(rev_idx)

			if len(children) == 0:
				for idx in p_indexes:
					self._items[rev_idx]['construct_error'] = 'empty'
				raise EmptyConstructError()

		if not validation_func is None and not validation_func(children):
			for idx in p_indexes:
				self._items[rev_idx]['construct_error'] = 'invalid'
			raise ConstructValidationError(children)

		srt_idxs2 = sorted(idxs_efetivamente_usados)

		for idx in reversed(srt_idxs2):
			self.remove_at(idx)

		insert_obj = {
			"construct": p_tag,
			"children": children
		}

		repr_list = []
		for c in children:
			if 'repr' in c.keys():
				repr_list.append(c['repr'])
			elif 'ok' in c.keys():
				repr_list.append(c['ok'])
		if len(repr_list) > 0:
			insert_obj['repr'] = " ".join(repr_list)

		if not adic_attribs is None:
			for k, v in adic_attribs:
				insert_obj[k] = v

		self._items.insert(min(srt_idxs), deepcopy(insert_obj))

	def __iter__(self) -> Iterator[Dict[str, Any]]:
		"""Iterate over (read-only-by-convention) copies of the items."""
		return iter(deepcopy(item) for item in self._items)

	def __len__(self) -> int:
		return len(self._items)

	def __getitem__(self, index: int) -> Dict[str, Any]:
		return self._items[index]

	# ------------------------------------------------------------------ #
	# Serialization
	# ------------------------------------------------------------------ #
	def to_json(self, path: Optional[str] = None, indent: int = 4, do_tee=False) -> str | None:
		"""
		Serialize the list to a JSON string or to a file. 
		If ``path`` is given, write it to that file. In this case, 
		 returns the JSON string only if ``do_tee`` is true.
		"""
		text = None

		if path is not None:
			with open(path, "w", encoding="utf-8") as f:
				json.dump(self._items, indent=indent, ensure_ascii=False, cls=self.Encoder)

		if path is None or do_tee:
			text = json.dumps(self._items, indent=indent, ensure_ascii=False,  cls=self.Encoder)

		return text

	@classmethod
	def from_json(
		cls,
		source: str,
		schemas: Optional[List[Dict[str, Type]]] = None,
		# defaults: Optional[Dict[str, Any]] = None,
		# strict_types: bool = True,
		from_file: Optional[bool] = None,
	) -> "DictListManager":
		"""
		Build a DictListManager from a JSON string or a path to a JSON
		file. ``source`` is treated as a file path if it ends in
		``.json`` or if ``from_file=True`` is passed explicitly;
		otherwise it's parsed as a raw JSON string.
		"""
		looks_like_path = source.strip().endswith(".json")
		use_file = from_file if from_file is not None else looks_like_path

		if use_file:
			with open(source, "r", encoding="utf-8") as f:
				raw = f.read()
		else:
			raw = source

		data = json.loads(raw)
		if not isinstance(data, list):
			raise ValueError("JSON source must decode to a list of objects")

		mgr = cls(schemas=schemas) #, defaults=defaults, strict_types=strict_types)
		mgr.extend(data)
		return mgr

	def __repr__(self) -> str:
		return f"DictListManager(count={len(self._items)}, schemas={self.schemas})"

if __name__ == "__main__":
	# Minimal smoke test / usage demo.

	sch_a = {
		"type" : "object",
		"properties" : {
			"id" : {"type" : "number"},
			"name" : {"type" : "string"},
			"active" : {"type" : "boolean", "default": True}
		}
	}

	sch_b = {
		"type" : "object",
		"properties" : {
			"id" : {"type" : "number"},
			"brr" : {"type" : "string"}
		}
	}

	mgr = DictListManager((sch_a, sch_b))
	mgr.insert(id=1, name="Alice")
	mgr.insert(id=2, name="Bob", active=False)
	mgr.insert(id=3, name="Carol")

	# Walk: uppercase every name, and flip 'active' for even ids.
	mgr.walk(lambda item: item.update(name=item["name"].upper()))
	mgr.walk(
		lambda item: item.update(active=not item["active"]),
		predicate=lambda item: item["id"] % 2 == 0,
	)

	json_str = mgr.to_json()
	print(json_str)

	reloaded = DictListManager.from_json(json_str, (sch_a, sch_b))
	print(reloaded)
	assert list(reloaded) == list(mgr)
	print("Round-trip OK")


# Resultado esperado:

# [
#	 {
#		 "id": 1,
#		 "name": "ALICE",
#		 "active": true
#	 },
#	 {
#		 "id": 2,
#		 "name": "BOB",
#		 "active": true - valor invertido pelo segundo 'walk' que apenas inverte itens de número de ordem par
#	 },
#	 {
#		 "id": 3,
#		 "name": "CAROL",
#		 "active": true
#	 }
# ]