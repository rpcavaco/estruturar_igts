
import os

from doctree import DocNode, parseFromText


# from documento_regulamentar import processar_documento

def run(p_versao_concelho):

	in_path = os.path.join(p_versao_concelho, 'regl', 'aviso_publicacao.txt')
	assert os.path.exists(in_path), in_path

	out_dir = os.path.join(p_versao_concelho, 'output')
	if not os.path.exists(out_dir):
		os.makedirs(out_dir)

	assert os.path.exists(out_dir)

	out_path = os.path.join(out_dir, "NOVO_regulamento.json")

	dn = DocNode()
	parseFromText(in_path, out_path, dn)

	# processar_documento(in_path, os.path.join(out_dir, "NOVO_regulamento.json"))

if __name__ == "__main__":
	# run('../dados/Maia_1306/2_revisao_AVISO_4731_2025_2')
	#run('../dados/Alfandega_Fe_0401/2_revisao_AVISO_23096_2025_2')
	run('../dados/Sernancelhe_1818/2_revisao_AVISO_11229_2025_2')

