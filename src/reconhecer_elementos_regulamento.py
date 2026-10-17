import os
import json

from copy import copy, deepcopy
from typing import Optional, List

from json_helpers import find_unserializable
from elementos import ReconhecimentoElementos
from dict_list_manager import DictListManager
from nlp import update_parts_of_speech_dict

from tqdm import tqdm

def main(p_versao_concelho, p_output_file, preserve_tokens_ords: Optional[List[int]] = None, update_pos: Optional[bool] = False, limit: Optional[int] = 0, reverse_limit: Optional[bool] = False, break_on_hyphens: Optional[bool] = False) -> None:
	"""
	Processo de reconhecimento de elementos em regulamentos de PDM
	"""

	wrkdir = os.path.join(p_versao_concelho, "output")
	infile = os.path.join(wrkdir, 'docnodes_regulamento.json')

	nodes_dict = None
	with open(infile, 'r', encoding='utf-8') as fp:
		nodes_dict = json.load(fp)

	assert not nodes_dict is None

	rref = ReconhecimentoElementos()
	ret = {}
	janela_dict = {}

	# Limitar
	# items_list = list(nodes_dict.items())[:300]

	items_list = nodes_dict.items()

	for i, item in enumerate(tqdm(items_list)):
		if limit > 0:
			if reverse_limit:
				if i < limit:
					continue
			else:
				if i > limit:
					break
		k, val = item
		if 'c' in val.keys():
			for j, instr in enumerate(val["c"]):
				rref.reconhecerEmJanela(instr, janela_dict, break_on_hyphens=break_on_hyphens)
				janela_dict['ord'] = i + 1
				janela_dict['p'] = copy(val['p'])
				# if len(val['p']) > 0:
				# 	janela_dict['p'].append(j)
				janela_dict['input'] = instr
				ret.setdefault('nodes', [])
				if not preserve_tokens_ords is None and len(preserve_tokens_ords) > 0 and not i+1 in preserve_tokens_ords:
					del janela_dict['tokens_list']
				ret['nodes'].append(deepcopy(janela_dict))

	faltas = set([])
	for node_dict in ret['nodes']:
		if 'faltas' in node_dict.keys():
			faltas.update(node_dict['faltas'])

	print("Palavras em falta (sem POS):", len(faltas))

	if len(faltas) > 0:
		ret['faltas'] = list(sorted(faltas))
		if update_pos:
			update_parts_of_speech_dict(rref.part_of_speech_dict, ret['faltas'], opt_out_path=os.path.join(wrkdir, 'upd_pos.json'))


	find_unserializable(ret)

	#with open(os.path.join("..", "temp", p_output_file), 'w') as fp:
	with open(os.path.join(wrkdir, p_output_file), 'w') as fp:
		print(f"Ver {p_output_file} em 'output'")
		json.dump(ret, fp, indent=4, ensure_ascii=False, cls=DictListManager.Encoder)

def matches_faceis(p_versao_concelho, p_referentes_file, p_output_file) -> None:

	wrkdir = os.path.join(p_versao_concelho, "output")

	referentes_dict = None
	with open(os.path.join(wrkdir, p_referentes_file), 'r') as fp:
		referentes_dict = json.load(fp)

	assert not referentes_dict is None

	part_of_speech_dict = None
	with open(os.path.join('setup', 'part_of_speech.json'), 'r', encoding='utf-8') as fp: 
		part_of_speech_dict = json.load(fp)	

	assert not part_of_speech_dict is None

	sufixos_plurais = None
	with open(os.path.join('setup', 'sufixos_plurais,json'), 'r', encoding='utf-8') as fp: 
		sufixos_plurais = json.load(fp)	

	print(f"{len(referentes_dict["faltas"])} palavras em falta")

	ret = {}

	found = 0
	for wrd in referentes_dict["faltas"]:
		for plur, sing in sufixos_plurais:
			if wrd.endswith(plur):
				nova = wrd[:-len(plur)] + sing
				if nova in part_of_speech_dict.keys():
					ret[wrd] = part_of_speech_dict[nova]
					found += 1
			elif wrd.endswith(sing):
				nova = wrd[:-len(sing)] + plur
				if nova in part_of_speech_dict.keys():
					ret[wrd] = part_of_speech_dict[nova]
					found += 1

	print(f"{found} faltas recuperáveis pelos plurais")

	hsufs = ['-la', '-lhe', '-lhes', '-se']

	found = 0
	for wrd in referentes_dict["faltas"]:
		for hsuf in hsufs:
			if wrd.endswith(hsuf):
				ret[wrd] = ["verbo"]
				found += 1

	print(f"{found} faltas recuperáveis com '-se', '-lhe', etc.")


		



	with open(os.path.join(wrkdir, p_output_file), 'w') as fp:
		print(f"Ver {p_output_file} em 'output'")
		json.dump(ret, fp, indent=4, ensure_ascii=False, cls=DictListManager.Encoder)

if __name__ == "__main0__":
	main('../dados/Maia_1306/2_revisao_AVISO_4731_2025_2', 'referentes_regulamento_maia.json', preserve_tokens_ords=[1102])

if __name__ == "__main1__":
	main('../dados/Alfandega_Fe_0401/2_revisao_AVISO_23096_2025_2', 'referentes_regulamento.json', preserve_tokens_ords=None, update_pos=True, limit=0, reverse_limit=False)

if __name__ == "__main__":
	main('../dados/Sernancelhe_1818/2_revisao_AVISO_11229_2025_2', 'referentes_regulamento.json', 
		preserve_tokens_ords=None, 
		update_pos=False, 
		limit=500, reverse_limit=True
	)

if __name__ == "__main2__":
	matches_faceis('../dados/Sernancelhe_1818/2_revisao_AVISO_11229_2025_2', 'referentes_regulamento.json', 'matches_faceis.json')