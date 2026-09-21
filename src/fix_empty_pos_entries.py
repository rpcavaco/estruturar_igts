
import os
import json

from nlp import update_parts_of_speech_dict

def fix_empty_pos_entries(p_versao_concelho):

	in_path = os.path.join('setup', 'part_of_speech.json')
	out_path = os.path.join(p_versao_concelho, 'output', 'empty_upd_pos.json')

	pos_dict = None
	with open(in_path, 'r', encoding='utf-8') as fp: 
		pos_dict = json.load(fp)

	empty_pos_words = [k for k, v in pos_dict.items() if len(v) == 0]

	update_parts_of_speech_dict(pos_dict, empty_pos_words, opt_out_path=out_path)


if __name__ == "__main__":
	fix_empty_pos_entries("../dados/Alfandega_Fe_0401/2_revisao_AVISO_23096_2025_2")
	#fix_empty_pos_entries("../dados/Sernancelhe_1818/2_revisao_AVISO_11229_2025_2")