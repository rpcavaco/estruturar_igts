import os
import json

from copy import copy, deepcopy
from typing import Optional, List

from json_helpers import find_unserializable
from referentes import ReconhecimentoReferentes
from documento_regulamentar import dump_docnodes
from dict_list_manager import DictListManager
from nlp import update_parts_of_speech_dict

from tqdm import tqdm

def main(p_versao_concelho, p_output_file, preserve_tokens_ords: Optional[List[int]] = None, update_pos: Optional[bool] = False, limit: Optional[int] = 0, reverse_limit: Optional[bool] = False) -> None:

	wrkdir = os.path.join(p_versao_concelho, "output")
	infile = os.path.join(wrkdir, "regulamento.json")
	outfile = os.path.join(wrkdir, 'docnodes_regulamento.json')

	# Gerar lista serial de nós, com backup em disco
	out_dict = dump_docnodes(infile, outfile)

	rref = ReconhecimentoReferentes()
	ret = {}
	janela_dict = {}

	for i, item in enumerate(tqdm(out_dict.items())):
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
				rref.reconhecerEmJanela(instr, janela_dict)
				janela_dict['ord'] = i + 1
				janela_dict['p'] = copy(val['p'])
				if len(val['p']) > 0:
					janela_dict['p'].append(j)
				janela_dict['input'] = instr
				ret.setdefault('nodes', [])
				if not preserve_tokens_ords is None and not i+1 in preserve_tokens_ords:
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

if __name__ == "__main0__":
	main('../dados/Maia_1306/2_revisao_AVISO_4731_2025_2', 'referentes_regulamento_maia.json', preserve_tokens_ords=[1102])

if __name__ == "__main1__":
	main('../dados/Alfandega_Fe_0401/2_revisao_AVISO_23096_2025_2', 'referentes_regulamento.json', preserve_tokens_ords=[], update_pos=True, limit=0, reverse_limit=False)

if __name__ == "__main__":
	main('../dados/Sernancelhe_1818/2_revisao_AVISO_11229_2025_2', 'referentes_regulamento.json', preserve_tokens_ords=[], update_pos=True, limit=0, reverse_limit=False)