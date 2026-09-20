import os
import json

from copy import copy, deepcopy

from json_helpers import find_unserializable
from referentes import ReconhecimentoReferentes
from documento_regulamentar import dump_docnodes
from dict_list_manager import DictListManager

from tqdm import tqdm

def main(p_versao_concelho, p_output_file, preserve_tokens_ords: Optional[List[int]] = None) -> None:

	wrkdir = os.path.join(p_versao_concelho, "output")
	infile = os.path.join(wrkdir, "regulamento.json")
	outfile = os.path.join(wrkdir, 'docnodes_regulamento.json')

	# Gerar lista serial de nós, com backup em disco
	out_dict = dump_docnodes(infile, outfile)

	rref = ReconhecimentoReferentes()
	ret = {}
	janela_dict = {}

	for i, item in enumerate(tqdm(out_dict.items())):
		# if i < 1100:
		# 	continue
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
	for node_dict in enumerate(ret['nodes']):
		if 'faltas' in node_dict:
			faltas.update(node_dict['faltas'])

	if len(faltas) > 0:
		ret['faltas'] = list(sorted(faltas))


	find_unserializable(ret)

	#with open(os.path.join("..", "temp", p_output_file), 'w') as fp:
	with open(os.path.join(wrkdir, p_output_file), 'w') as fp:
		print(f"Ver {p_output_file} em 'output'")
		json.dump(ret, fp, indent=4, ensure_ascii=False, cls=DictListManager.Encoder)

if __name__ == "__main__":
	main('../dados/Maia_1306/2_revisao_AVISO_4731_2025_2', 'referentes_regulamento_maia.json', preserve_tokens_ords=[1102])