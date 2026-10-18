
import os
import json

from .doctree import DocNode, parseFromText, traverseNodes


# from documento_regulamentar import processar_documento

def genfiles_regulamento(p_versao_concelho, p_tipo_numeracao_alineas, limite = 0):
	"""
	Processar o regulamento de PDM.

	São processados conteúdos guardados na pasta de versão de PDM indicada por 'p_versao_concelho'.

	O conteúdo de texto a analisar tem de se encontrar num ficheiro de texto chamado 'aviso_publicacao.txt'.

	São gerados dois ficheiros:
		- 'regulamento.json': árvore DocTree resultante do texto do regulamento
		- 'docnodes_regulamento.json': lista serial de chunks de texto; cada elemento da 
			lista tem o chunk de texto propriamente dito e um caminho (sequência de identificadores)
			espelhando o percurso entre sucessivos nós de árvore, desde a raíz, para atingir este chunk

	Argumentos:
	- p_versao_concelho - indica o nome da pasta de versão de PDM, dentro da pasta do concelho
		(dados/<concelho>/<versão_concelho>)
	- p_tipo_numeracao_alineas - 'TIPO1' / 'TIPO2'	('TIPO1' por defeito)
		TIPO1: aa, ab, ac ... ax, ba, bb
		TIPO2: aa, bb, cc, ... (apenas Maia)
	- limite - processar apenas <limite> linhas do texto original
	"""

	in_path = os.path.join(p_versao_concelho, 'regl', 'aviso_publicacao.txt')
	assert os.path.exists(in_path), in_path

	out_dir = os.path.join(p_versao_concelho, 'output')
	if not os.path.exists(out_dir):
		os.makedirs(out_dir)

	assert os.path.exists(out_dir)

	out_path = os.path.join(out_dir, "regulamento.json")
	out_path2 = os.path.join(out_dir, "docnodes_regulamento.json")

	dn = DocNode()
	parseFromText(in_path, out_path, dn, tipo_numeracao_alineas=p_tipo_numeracao_alineas, limit=limite)

	out_dict = {}
	traverseNodes(dn.toJSON(), out_dict)

	with open(out_path2, 'w', encoding='utf-8') as fp:
		json.dump(out_dict, fp, indent=4, ensure_ascii=False)	

if __name__ == "__main__":
	# run('../dados/Maia_1306/2_revisao_AVISO_4731_2025_2', 'TIPO2', 1380)
	# run('../dados/Alfandega_Fe_0401/2_revisao_AVISO_23096_2025_2', 'TIPO1')
	genfiles_regulamento('../dados/Sernancelhe_1818/2_revisao_AVISO_11229_2025_2', 'TIPO1')

