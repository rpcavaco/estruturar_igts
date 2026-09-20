import codecs
import json
import re
import os


from uuid import uuid4
from copy import copy

from docnode import DocNode
from documento_regulamentar import processar_documento
from nlp import NumeracaoRomana


# Gera árvore a partir de ficheiro de texto

SEQ_LETRAS = "abcdefghijklmnopqrstuvwxyz"

def ler_linha(p_path, p_line_num):
	ret = None
	cnt = 0
	with codecs.open(p_path, 'r', encoding='utf-8') as fp:
		for _ in range(p_line_num-1):
			cnt += 1
			next(fp)
		ret = next(fp).strip()
	return ret

def ler_entre_branco_file(p_path, p_from_line_num):

	ret = None
	tmp = []
	cnt = 0
	started = False

	with codecs.open(p_path, 'r', encoding='utf-8') as fp:
		for _ in range(p_from_line_num-1):
			next(fp)
		for ln in fp:
			cnt += 1
			if cnt >= 5:
				break
			if len(ln.strip()) > 0:
				started = True
				tmp.append(ln.strip())
			else:
				if started:
					break

	if len(tmp) > 0:
		ret = r'\n'.join(tmp)
	return cnt, ret.strip()

def ler_entre_branco(p_text, p_from_line_num):

	ret = None
	tmp = []
	cnt = 0
	started = False

	text_lines = iter(p_text.split(r"\n"))

	try:
		for _ in range(p_from_line_num-1):
			next(text_lines)
	except:
		print('################3')
		print(p_from_line_num, p_text.split(r"\n"))
		raise

	for ln in text_lines:
		cnt += 1
		if cnt >= 5:
			break
		if len(ln.strip()) > 0:
			started = True
			tmp.append(ln.strip())
		else:
			if started:
				break

	if len(tmp) > 0:
		ret = r'\n'.join(tmp)
	return cnt, ret.strip()

def ler_entre_linhas_file(p_path, p_line_num_start, line_num_stop=None):

	assert line_num_stop is None or line_num_stop > p_line_num_start, f"start:{p_line_num_start} stop:{line_num_stop}"
	ret = None
	tmp = []
	cnt = 0

	with codecs.open(p_path, 'r', encoding='utf-8') as fp:
		for _ in range(p_line_num_start-1):
			cnt += 1
			next(fp)
		for ln in fp:	
			cnt += 1
			stripp = ln.strip()
			if stripp.lower() not in ['anexos']:
				tmp.append(ln.strip())
			if not line_num_stop is None:
				if cnt == line_num_stop:
					break
	if len(tmp) > 0:
		while len(tmp[0].strip()) == 0:
			del tmp[0]
		while len(tmp[-1].strip()) == 0:
			del tmp[-1]
	if len(tmp) > 0:
		ret = r'\n'.join(tmp)
	return ret

def ler_entre_linhas(p_text, p_line_num_start, line_num_stop=None):

	assert line_num_stop is None or line_num_stop > p_line_num_start, f"start:{p_line_num_start} stop:{line_num_stop}"
	ret = None
	tmp = []
	cnt = 0

	text_lines = iter(p_text.split(r"\n"))

	# with codecs.open(p_path, 'r', encoding='utf-8') as fp:

	for _ in range(p_line_num_start-1):
		cnt += 1
		next(text_lines)
	for ln in text_lines:	
		cnt += 1
		tmp.append(ln.strip())
		if not line_num_stop is None:
			if cnt == line_num_stop:
				break

	if len(tmp) > 0:
		while len(tmp[0].strip()) == 0:
			del tmp[0]
		while len(tmp[-1].strip()) == 0:
			del tmp[-1]
	if len(tmp) > 0:
		ret = r'\n'.join(tmp)
	return ret

def titulos_maiusculas_com_romano_final(p_caminho):

	ret = []
	cnt = 0
	nr = NumeracaoRomana()

	with codecs.open(p_caminho, 'r', encoding='utf-8') as fp:
		for ln in fp:
			cnt += 1
			lntxt = ln.strip()
			if len(lntxt) == 0:
				continue
			sample = lntxt[:10].strip()[:3]
			if all(ch.isupper() for ch in sample):
				splits = lntxt.strip().split()
				l = len(splits)
				if l > 1 and l <= 3 and nr.checkIsRoman(splits[-1]):
					ret.append((cnt, ' '.join([spl.strip() for spl in splits[:-1]]), lntxt))
	return ret

def extrair_artigos(p_txt_content):

	blocos = []
	for li, ln in enumerate(p_txt_content.split(r"\n")):
		# print("----", ln)
		if ln.startswith('Art.') or ln.startswith('Artigo'):
			num_str_mo = re.search(r'([\d]+).º', ln, re.I)
			# print(num_str_mo.groups(1))
			num_art = int(num_str_mo.group(1))
			if len(blocos) == 0:
				if li > 0:
					blocos.append({'start': 1, 'end': li})
				blocos.append({'start': li+2, 'end': None, 'num_art': num_art})
			else:
				blocos[-1]['end'] = li
				blocos.append({'start': li+2, 'end': None, 'num_art': num_art})

	# print(blocos)

	artigos = []
	for bloco in blocos:

		text = ler_entre_linhas(p_txt_content, bloco['start'], line_num_stop=bloco['end'])
		dz_sz, dz_txt = ler_entre_branco(text, 1)

		effective_text = text.split(r"\n")[dz_sz:]

		artigos.append({
			'start': bloco['start'],
			'num': bloco['num_art'],
			'tit': dz_txt,
			'cont': r'\n'.join(effective_text)
		})

	return artigos

def parsing_sequencias_artigo(p_conteudo, num=None):

	seqcias = {
	}
	patt_ponto = r'([\d]+) \- '
	patt_alinea = r'([a-z])\) '

	for ln in p_conteudo.split(r'\n'):
		if len(ln) < 1:
			continue
		mo = re.match(patt_ponto, ln)
		if not mo is None:
			seqcias[int(mo.group(1))] = None

	if not seqcias:
		for ln in p_conteudo.split(r'\n'):
			if len(ln) < 1:
				continue
			mo = re.match(patt_alinea, ln)
			if not mo is None:
				seqcias[mo.group(1)] = None

	if not seqcias:
		return None
	
	chaves = [k for k in seqcias.keys()]

	if isinstance(chaves[0], int):
		# Sequencia de PONTOS, garantir ordem
		assert chaves[0] == 1
		kprev = None
		for k in chaves:
			if not kprev is None and k - kprev > 1:
				del seqcias[k]
			else:
				kprev = k

	else:
		# Sequencia primária de alíneas em substituição de pontos, garantir ordem
		assert chaves[0] == 'a'

		# garantir que alineas contem apenas uma letra
		for k in chaves:
			if len(k) > 1:
				del seqcias[k]

		chaves = [k for k in seqcias.keys()]
		kprev = None
		for k in chaves:
			if not kprev is None and (SEQ_LETRAS.index(k) - SEQ_LETRAS.index(kprev) > 1):
				del seqcias[k]
			else:
				kprev = k

	pares = []
	prev = None
	for k in seqcias.keys():
		if prev is None:
			prev = k
			continue
		pares.append((prev, k))
		prev = k
	pares.append((list(seqcias.keys())[-1], None))

	text_content_list = []

	idx = -1
	for kthis, knext in pares:

		idx += 1

		# print('----------->', kthis, knext)

		conteudo = []
		if isinstance(kthis, int):

			for ln in p_conteudo.split(r'\n'):
				if len(ln) < 1:
					continue
				mo = re.match(patt_ponto, ln)
				if not mo is None:
					if int(mo.group(1)) == kthis:
						conteudo.append(ln[mo.end():])
					else:
						if not knext is None:
							if int(mo.group(1)) == knext:
								seqcias[kthis] = copy(conteudo)
								del conteudo[:]
								break
							else:
								if len(conteudo) > 0:
									conteudo.append(ln)
						else:
							if len(conteudo) > 0:
								conteudo.append(ln)
				else:
					if len(conteudo) > 0:
						conteudo.append(ln)

			if len(conteudo) > 0:
				seqcias[kthis] = copy(conteudo)
				del conteudo[:]

		else:

			# print('----------->', kthis)

			for ln in p_conteudo.split(r'\n'):
				if len(ln) < 1:
					continue
				mo = re.match(patt_alinea, ln)
				if not mo is None:
					if mo.group(1) == kthis:
						#print('  ', kthis, ln[mo.end():])
						conteudo.append(ln[mo.end():])
					else:
						if not knext is None:
							if mo.group(1) == knext:
								seqcias[kthis] = copy(conteudo)
								del conteudo[:]
								break
							else:
								if len(conteudo) > 0:
									conteudo.append(ln)
						else:
							if len(conteudo) > 0:
								conteudo.append(ln)
				else:
					if idx == 0 and len(conteudo) == 0:
						text_content_list.append(ln)
					if len(conteudo) > 0:
						conteudo.append(ln)


			if len(conteudo) > 0:
				seqcias[kthis] = copy(conteudo)
				del conteudo[:]

	ret = {	}
	if seqcias:
		ret['children'] = seqcias
	if len(text_content_list) > 0:
		ret['txt'] = r'\n'.join(text_content_list)

	return ret

def parsing_subsequencias_artigo(p_conteudo_list, num=None):

	seqcias = {
	}
	patt_alinea = r'([a-z])\) '
	patt_alinea_rom = r'([a-z]+)\) '

	nr = NumeracaoRomana()

	text_content_list = []

	for ln in p_conteudo_list:
		mo = re.match(patt_alinea, ln)
		if not mo is None:
			seqcias[mo.group(1)] = None

	if not seqcias:
		text_content_list = copy(p_conteudo_list)
	else:
		chaves = [k for k in seqcias.keys()]

		# Sequencia primária de alíneas em substituição de pontos, garantir ordem
		if chaves[0] != 'a':

			if chaves[0] == 'i':
				for k in chaves:
					return parsing_subsubsequencias_artigo(p_conteudo_list, num=num)
			else:
				# print('::::::: CH:', chaves[0])
				text_content_list = copy(p_conteudo_list)

		else:

			# garantir que alineas contem apenas uma letra
			for k in chaves:
				if len(k) > 1:
					del seqcias[k]

			chaves = [k for k in seqcias.keys()]
			kprev = None
			for k in chaves:
				if not kprev is None and (SEQ_LETRAS.index(k) - SEQ_LETRAS.index(kprev) > 1):
					del seqcias[k]
				else:
					kprev = k

			pares = []
			prev = None
			for k in seqcias.keys():
				if prev is None:
					prev = k
					continue
				pares.append((prev, k))
				prev = k
			pares.append((list(seqcias.keys())[-1], None))

			# print(' -- pares subsequencia --')
			# print(pares)

			for kthis, knext in pares:

				# print('----------->', kthis, knext)

				conteudo = []

				for li, ln in enumerate(p_conteudo_list):
					if len(ln) < 1:
						continue
					mo = re.match(patt_alinea, ln)
					if not mo is None:
						if mo.group(1) == kthis:
							if len(text_content_list) == 0:
								if li > 0:
									text_content_list.extend(p_conteudo_list[:li])
							conteudo.append(ln[mo.end():])
						else:
							if not knext is None:
								if mo.group(1) == knext:
									seqcias[kthis] = copy(conteudo)
									del conteudo[:]
									break
								else:
									if len(conteudo) > 0:
										conteudo.append(ln)
							else:
								if len(conteudo) > 0:
									conteudo.append(ln)
					else:
						if len(conteudo) > 0:
							conteudo.append(ln)

				if len(conteudo) > 0:
					seqcias[kthis] = copy(conteudo)
					del conteudo[:]

	new_sqcias = {}
	for k in seqcias:
		new_sqcias[k] = parsing_subsubsequencias_artigo(seqcias[k], num=num)

	ret = {	}
	if new_sqcias:
		ret['children'] = new_sqcias
	if len(text_content_list) > 0:
		ret['txt'] = r'\n'.join(text_content_list)

	assert bool(ret)

	return ret

def parsing_subsubsequencias_artigo(p_conteudo_list, num=None):
	
	seqcias = {
	}
	patt_subalinea = r'([a-z]+)\) '
	# patt_sub_subalinea = r'(\([\d]+\)) '

	nr = NumeracaoRomana()

	for ln in p_conteudo_list:
		mo = re.match(patt_subalinea, ln)
		if not mo is None and nr.checkIsRoman(mo.group(1)):
			seqcias[mo.group(1)] = None

	if not seqcias:
		return { "txt": r'\n'.join(p_conteudo_list) }
	
	chaves = [k for k in seqcias.keys()]

	# Sequencia primária de alíneas em substituição de pontos, garantir ordem
	if chaves[0].lower()!= 'i':
		return { "txt": r'\n'.join(p_conteudo_list) }

	chaves = [k for k in seqcias.keys()]
	kprev = None
	for k in chaves:
		if not kprev is None and (nr.fromRomanStr(k) - nr.fromRomanStr(kprev) > 1):
			del seqcias[k]
		else:
			kprev = k

	pares = []
	prev = None
	for k in seqcias.keys():
		if prev is None:
			prev = k
			continue
		pares.append((prev, k))
		prev = k
	pares.append((list(seqcias.keys())[-1], None))

	# print(' -- pares sub-subsequencia --')
	# print(pares)

	texto = []
	for kthis, knext in pares:

		# print('----------->', kthis, knext)

		conteudo = []

		for li, ln in enumerate(p_conteudo_list):
			if len(ln) < 1:
				continue
			mo = re.match(patt_subalinea, ln)
			if not mo is None:
				if mo.group(1) == kthis:
					if len(texto) == 0:
						if li > 0:
							texto.extend(p_conteudo_list[:li])
					conteudo.append(ln[mo.end():])
				else:
					if not knext is None:
						if mo.group(1) == knext:
							seqcias[kthis] = copy(conteudo)
							del conteudo[:]
							break
						else:
							if len(conteudo) > 0:
								conteudo.append(ln)
					else:
						if len(conteudo) > 0:
							conteudo.append(ln)
			else:
				if len(conteudo) > 0:
					conteudo.append(ln)

		if len(conteudo) > 0:
			seqcias[kthis] = copy(conteudo)
			del conteudo[:]

	new_sqcias = {}
	for k in seqcias:
		new_sqcias[k] = parsing_3subsequencias_artigo(seqcias[k], num=num)

	ret = { 
		"children": new_sqcias 
	}
	if len(texto) > 0:
		ret['txt'] = r'\n'.join(texto)

	# print('::: num:', num, new_sqcias)

	return ret

def parsing_3subsequencias_artigo(p_conteudo_list, num=None):
	
	seqcias = {
	}
	patt_sub_subalinea = r'\(([\d]+)\) '

	for ln in p_conteudo_list:
		mo = re.match(patt_sub_subalinea, ln)
		if not mo is None:
			seqcias[int(mo.group(1))] = None

	if not seqcias:
		return { "txt": r'\n'.join(p_conteudo_list) }
	
	chaves = [k for k in seqcias.keys()]

	# Sequencia primária de alíneas em substituição de pontos, garantir ordem
	if chaves[0] != 1:
		return { "txt": r'\n'.join(p_conteudo_list) }

	chaves = [k for k in seqcias.keys()]
	kprev = None
	for k in chaves:
		if not kprev is None and (k - kprev > 1):
			del seqcias[k]
		else:
			kprev = k

	pares = []
	prev = None
	for k in seqcias.keys():
		if prev is None:
			prev = k
			continue
		pares.append((prev, k))
		prev = k
	pares.append((list(seqcias.keys())[-1], None))

	# print(' -- pares sub-sub-subsequencia --')
	# print(pares)

	texto = []
	for kthis, knext in pares:

		# print('----------->', kthis, knext)

		conteudo = []

		for li, ln in enumerate(p_conteudo_list):
			if len(ln) < 1:
				continue
			mo = re.match(patt_sub_subalinea, ln)
			if not mo is None:
				if int(mo.group(1)) == kthis:
					if len(texto) == 0:
						if li > 0:
							texto.extend(p_conteudo_list[:li])
					conteudo.append(ln[mo.end():])
				else:
					if not knext is None:
						if int(mo.group(1)) == knext:
							seqcias[kthis] = { 'txt': '\n'.join(conteudo) }
							del conteudo[:]
							break
						else:
							if len(conteudo) > 0:
								conteudo.append(ln)
					else:
						if len(conteudo) > 0:
							conteudo.append(ln)
			else:
				if len(conteudo) > 0:
					conteudo.append(ln)

		if len(conteudo) > 0:
			seqcias[kthis] = { 'txt': '\n'.join(conteudo) }
			del conteudo[:]

	ret = { 
		"children": seqcias 
	}
	if len(texto) > 0:
		ret['txt'] = r'\n'.join(texto)

	# print('::: num:', num, seqcias)

	return ret

def parsing_artigo(p_conteudo, num=None):

	ret = {}

	seq_primaria = parsing_sequencias_artigo(p_conteudo, num=num)
	if not seq_primaria is None:

		if 'children' in seq_primaria.keys():
			for k in seq_primaria['children'].keys():
				ret[k] = parsing_subsequencias_artigo(seq_primaria['children'][k], num=num)

		if 'txt' in seq_primaria.keys():
			ret['txt'] = seq_primaria['txt']

	if not ret:
		ret = {
			'txt': p_conteudo
		}

	return ret


def run(p_versao_concelho):

	in_path = os.path.join(p_versao_concelho, 'regl', 'aviso_publicacao.txt')
	assert os.path.exists(in_path), in_path

	out_dir = os.path.join(p_versao_concelho, 'output')
	if not os.path.exists(out_dir):
		os.makedirs(out_dir)

	assert os.path.exists(out_dir)

	processar_documento(in_path, os.path.join(out_dir, "regulamento.json"))

if __name__ == "__main__":
	run('../dados/Maia_1306/2_revisao_AVISO_4731_2025_2')

