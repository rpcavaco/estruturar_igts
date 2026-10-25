
import os
import csv
import json

from copy import deepcopy

from .elementos import ReconhecimentoElementos
from .dict_list_manager import DictListManager

FILENAMES = {
	'condicionantes': 'catalogo_pdm_condicionantes.csv',
	'ordenamento': 'catalogo_pdm_ordenamento.csv'
}

def get_dados_folder():
    ret = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'dados')
    assert os.path.exists(ret), f"pasta 'dados' não existe em '{ret}'"
    return ret

def reconhecer_catalogo_pdm() -> None:
	"""
	Processo de reconhecimento de elementos no catálogo de objetos do PDM
	"""

	folder_dados = get_dados_folder()
	pasta_trabalho = os.path.join(folder_dados, 'PDM', 'CatalogoObjetos')

	out_json = {
	}

	rref = ReconhecimentoElementos()
	janela_dict = {}

	for modo in ['condicionantes', 'ordenamento']:

		found = {}
		csv_file_path = os.path.join(pasta_trabalho, FILENAMES[modo])
		with open(csv_file_path) as csvfile:
			the_reader = csv.reader(csvfile, delimiter=',', quotechar='"')
			for ri, row in enumerate(the_reader):
				if ri == 0:
					continue
				windows = set([row[i] for i in range(3)])
				for w in windows:
					if not w in found.keys():
						found[w] = { "codigos": [row[-1]] }
						rref.reconhecerEmJanela(w, janela_dict)
						found[w]["tokens"] = deepcopy(janela_dict)
						janela_dict.clear()
					else:
						found[w]["codigos"].append(row[-1])

		out_json[modo] = deepcopy(found)
		

	with open(os.path.join(pasta_trabalho, 'tokens_catalogo_objetos_pdm.json'), "w") as fp:
		json.dump(out_json, fp, indent=4, ensure_ascii=False, cls=DictListManager.Encoder)



if __name__ == "__main__":
	reconhecer_catalogo_pdm()