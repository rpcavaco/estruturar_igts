
import json
import re
import os
import warnings

from uuid import uuid4
from copy import copy

from docnode import DocNode



SEQ_LETRAS = "abcdefghijklmnopqrstuvwxyz"

MAX_LINHAS_ENTRE_BRANCO = 5 # Número máximo de linhas a serem lidas pelas funções ler_entre_branco*


def ler_entre_branco_file(p_path, p_from_line_num):
	"""Ler linhas de texto em ficheiro propositadamente aberto para esse fim, removendo as linhas inteiramente em branco.

		p_path -- caminho para o ficheiro
		p_from_line_num -- número de linha inicial, ordem iniciada em 1
	"""

	ret = None
	tmp = []
	cnt = 0
	started = False

	with open(p_path, 'r', encoding='utf-8') as fp:
		for _ in range(p_from_line_num-1):
			next(fp)
		for ln in fp:
			cnt += 1
			if cnt >= MAX_LINHAS_ENTRE_BRANCO:
				break
			if len(ln.strip()) > 0:
				started = True
				tmp.append(ln.strip())
			else:
				if started:
					break

	if len(tmp) > 0:
		ret = r'\n'.join(tmp).strip()

	return cnt, ret

def ler_entre_branco(p_text, p_from_line_num):
	"""Ler linhas de texto numa string, removendo as linhas inteiramente em branco.

		p_text -- string contendo o texto de entrada
		p_from_line_num -- número de linha inicial, ordem iniciada em 1
	"""

	ret = None
	tmp = []
	cnt = 0
	started = False

	text_lines = iter(p_text.split(r"\n"))

	try:
		for _ in range(p_from_line_num-1):
			next(text_lines)
	except:
		print('################')
		print(p_from_line_num, p_text.split(r"\n"))
		raise

	for ln in text_lines:
		cnt += 1
		if cnt >= MAX_LINHAS_ENTRE_BRANCO:
			break
		if len(ln.strip()) > 0:
			started = True
			tmp.append(ln.strip())
		else:
			if started:
				break

	if len(tmp) > 0:
		ret = r'\n'.join(tmp).strip()
	return cnt, ret

def ler_entre_linhas_file(p_path, p_line_num_start, line_num_stop=None):
	"""Ler linhas de texto em ficheiro propositadamente aberto para esse fim, entre duas linhas específicas

		p_path -- caminho para o ficheiro
		p_line_num_start -- número de linha inicial, ordem iniciada em 1
		line_num_stop -- número de linha final
	"""

	assert line_num_stop is None or line_num_stop > p_line_num_start, f"erro ler_entre_linhas_file, start:{p_line_num_start} stop:{line_num_stop}"
	ret = None
	tmp = []
	cnt = 0

	with open(p_path, 'r', encoding='utf-8') as fp:
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
	"""Ler linhas de texto em ficheiro propositadamente aberto para esse fim, entre duas linhas específicas

		p_text -- string contendo o texto de entrada
		p_line_num_start -- número de linha inicial, ordem iniciada em 1
		line_num_stop -- número de linha final
	"""

	assert line_num_stop is None or line_num_stop > p_line_num_start, f"erro ler_entre_linhas, start:{p_line_num_start} stop:{line_num_stop}"
	ret = None
	tmp = []
	cnt = 0

	text_lines = iter(p_text.split(r"\n"))

	# with open(p_path, 'r', encoding='utf-8') as fp:

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
		ret = r'\n'.join(tmp).strip()

	return ret

def titulos_maiusculas_com_romano_final(p_caminho) -> list:
	"""Extração de títulos em maiúsculas terminados por número em notação romana, a partir de ficheiro aberto propositadamente para esse fim.

		p_caminho -- caminho para o ficheiro
	"""

	ret = []
	cnt = 0
	nr = NumeracaoRomana()

	with open(p_caminho, 'r', encoding='utf-8') as fp:
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

def extrair_artigos(p_txt_content) -> list:
	"""Extração de artigos 'raw' a partir de uma string. 
		O conteúdo de cada artigo é estruturado e retornado como dict JSON (formato inicial) e 
		 acrescentado a uma lista, retornada no final.
		Cada conteúdo de artigo retornado tem um atributo textual 'cont', a ser separado, por outras funções, 
		 em conteúdo efetivamente textual e, se necessário, numa lista de 'números' ou alíneas.

		p_txt_content -- string contendo o texto a processar
	"""

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

def parsing_sequencias_artigo(p_conteudo, num=None) -> dict:
	"""Extração de sequências dentro de um artigo, primeiro nível de recursividade.
		O conteúdo estruturado é retornado como dict.
		O retorno contém 'text' (conteúdo textual) e 'children' ('números' ou artigos)

		p_conteudo -- string contendo o texto do artigo a processar
	"""

	seqcias = { }
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

def parsing_subsequencias_artigo(p_conteudo_list, num=None) -> dict:
	"""Extração de sequências dentro de um artigo, segundo nível de recursividade.
		O conteúdo estruturado é retornado como dict.
		O retorno contém 'text' (conteúdo textual) e 'children' ('números' ou artigos).

		p_conteudo_list -- lista de strings contendo o texto do artigo a processar
	"""

	seqcias = { }
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

def parsing_subsubsequencias_artigo(p_conteudo_list, num=None) -> dict:
	"""Extração de sequências dentro de um artigo, terceiro nível de recursividade.
		O conteúdo estruturado é retornado como dict.
		O retorno contém 'text' (conteúdo textual) e 'children' ('números' ou artigos).

		p_conteudo_list -- lista de strings contendo o texto do artigo a processar
	"""	

	seqcias = { }
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

def parsing_3subsequencias_artigo(p_conteudo_list, num=None) -> dict:
	"""Extração de sequências dentro de um artigo, quarto nível de recursividade.
		O conteúdo estruturado é retornado como dict.
		O retorno contém 'text' (conteúdo textual) e 'children' ('números' ou artigos).

		p_conteudo_list -- lista de strings contendo o texto do artigo a processar
	"""	

	seqcias = { }
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

def parsing_artigo(p_conteudo, num=None) -> dict:
	"""Estruturação do conteúdo do artigo a partir de uma string. 

		p_conteudo -- string contendo o texto a processar
	"""

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

def processar_documento_regulamentar(p_caminho_entrada: str, p_caminho_saida: str, ident_ato_normativo: str | None) -> None:
	"""Processar conteúdo textual de um ato normativo para estrutura JSON de Documento Regulamentar DocNode.

		p_caminho_entrada -- caminho completo para o ficheiro TXT de entrada
		p_caminho_saida -- caminho completo para o ficheiro JSON de saída
	"""

	first_class_types = ["TÍTULO", "ANEXO"]
	
	# Listar posições dos TÍTULOS terminados com número em notação romana
	posicoes_titulos_maiusc = titulos_maiusculas_com_romano_final(p_caminho_entrada)

	porcoes = []
	prev_start = None
	prev_tit = None
	prev_titlvl = None
	for start_line, titlvl, tit in posicoes_titulos_maiusc:

		if prev_start is None:
			if start_line > 1:
				porcoes.append({
					'start': 1,
					'stop': start_line-1,
					'tit': None,
					'titlevel': 'INTRO'
				})
		else:
			porcoes.append({
				'start': prev_start,
				'stop': start_line-1,
				'tit': prev_tit,
				'titlevel': prev_titlvl
			})
		prev_start = start_line
		prev_tit = tit
		prev_titlvl = titlvl
	porcoes.append({
		'start': prev_start,
		'stop': None,
		'tit': prev_tit,
		'titlevel': prev_titlvl
	})

	tree_root = DocNode()

	if not ident_ato_normativo is None:
		tree_root.setIdentAto(ident_ato_normativo)

	current_node = tree_root

	for porcao in porcoes:

		hier = current_node.typeHierarchy()
		stypes = current_node.siblingTypes()

		if porcao['titlevel'] in first_class_types:
			current_node = tree_root
			current_node.addEmptySibling(porcao['titlevel'])
		else:
			if len(stypes) == 0 or porcao['titlevel'] == stypes[-1]:
				current_node.addEmptySibling(porcao['titlevel'])
			else:
				if porcao['titlevel'] not in hier:
					current_node = current_node.addEmptySibling2LastSibling(porcao['titlevel'])
				else:
					while porcao['titlevel'] != current_node.typestr:
						current_node = current_node.parent
					current_node = current_node.parent
					current_node.addEmptySibling(porcao['titlevel'])

		attrs_to_store = {
			'start': porcao['start'],
			'stop': porcao['stop'],
			'tit': porcao['tit']
		}

		if porcao['tit'] is None:
			dz_sz, dz_txt = ler_entre_branco_file(p_caminho_entrada, porcao['start'])
		else:
			dz_sz, dz_txt = ler_entre_branco_file(p_caminho_entrada, porcao['start']+1)

		if porcao['titlevel'] == 'INTRO':
			# Passar designacao a designacao do documento
			if tree_root.attrs is None:
				tree_root.attrs = {}
			tree_root.attrs['design'] = dz_txt
		else:
			attrs_to_store['design'] = dz_txt

		if porcao['stop'] is None or porcao['stop'] > porcao['start']+dz_sz:
			
			txt = ler_entre_linhas_file(p_caminho_entrada, porcao['start']+dz_sz, line_num_stop=porcao['stop'])
			artigos = extrair_artigos(txt)
			if len(artigos) > 0:

				if artigos[0]['start'] > 2:
					# Nó com lista de artigos, com parágrafo(s) de texto em preâmbulo antes dos artigos
					# print("cont + artigos, num artigo:", artigos[0]['num'])
					attrs_to_store['cont'] = txt[:artigos[0]['start']-1]

				attrs_to_store['artigos'] = [{'num': a['num'], 'id': str(uuid4()), 'atit': a['tit'], 'cont': parsing_artigo(a['cont'], num=a['num']) } for a in artigos]

			else:
				attrs_to_store['cont'] = txt
		
		current_node.setLastSiblingAttrs(attrs_to_store)

	with open(p_caminho_saida, 'w', encoding='utf-8') as fp: 
		json.dump(tree_root.toJSON(), fp, indent=4, ensure_ascii=False)


def traverseNodes(p_out_dict, p_node, path=None, typestr_filter_list=None, maxdepth=None, maxchildren=None, scrap_attributes=None): #get_path=False):
	
	assert typestr_filter_list is None or isinstance(typestr_filter_list, list)
	assert scrap_attributes is None or isinstance(scrap_attributes, list)

	if not scrap_attributes is None:
		_scrap_attributes = scrap_attributes
	else:
		_scrap_attributes = []

	if not maxdepth is None and len(path) > maxdepth:
		warnings.warn(f"depth de {path}, {len(path)}, é maior que maxdepth:{maxdepth}")
		return

	if p_node.typestr == 'ANEXO':
		return
	
	if not typestr_filter_list is None:
		if p_node.typestr != 'ROOT' and not p_node.typestr.lower() in [f.lower() for f in typestr_filter_list]:
			return
		
	local_buf = []

	if path is None:
		_path = []
	else:
		_path = copy(path)
		_path.append(p_node.id)

	if 'tit' in p_node.attrs and not 'tit' in _scrap_attributes:
		if not p_node.attrs['tit'] is None:
			local_buf.append(p_node.attrs['tit'])
	if 'design' in p_node.attrs and not 'design' in _scrap_attributes:
		local_buf.append(p_node.attrs['design'])
	if 'cont' in p_node.attrs and not 'cont' in _scrap_attributes:
		local_buf.append(p_node.attrs['cont'])
	if 'txt' in p_node.attrs and not 'txt' in _scrap_attributes:
		local_buf.append(p_node.attrs['txt'])

	if len(local_buf) > 0:
		p_out_dict[len(p_out_dict.keys())+1] = {
			'p': copy(_path),
			'c': copy(local_buf)
		}

	if 'artigos' in p_node.attrs.keys():

		for art in p_node.attrs['artigos']:

			p1 = copy(_path)
			p1.append(art['id'])

			del local_buf[:]
			if not 'atit' in _scrap_attributes:
				local_buf.append(art['atit'])
			# if 'txt' in art['cont'].keys() and not 'txt' in _scrap_attributes:
			# 	local_buf.append(art['cont']['txt'])
			if len(local_buf) > 0:
				p_out_dict[len(p_out_dict.keys())+1] = {
					'p': copy(p1),
					'c': copy(local_buf)
				}

			kys = list(art['cont'].keys())

			# Garantir que 'txt' e´ a primeira key
			if 'txt' in kys and not kys[0] == 'txt':
				kys.remove('txt')
				kys.insert(0, 'txt')

			for k in kys:

				del local_buf[:]
				# assert  k != 'txt', art['cont']
				if k == 'txt' and not 'txt' in _scrap_attributes:
					local_buf.append(art['cont'][k])

				p2 = copy(p1)
				p2.append(k)

				if isinstance(art['cont'][k], dict) and 'txt' in art['cont'][k].keys() and not 'txt' in _scrap_attributes:
					local_buf.append(art['cont'][k]['txt'])
				if len(local_buf) > 0:
					p_out_dict[len(p_out_dict.keys())+1] = {
						'p': copy(p2),
						'c': copy(local_buf)
					}

				if isinstance(art['cont'][k], dict) and 'children' in art['cont'][k].keys():
					for l in art['cont'][k]['children'].keys():

						p3 = copy(p2)
						p3.append(l)

						del local_buf[:]
						if 'txt' in art['cont'][k]['children'][l].keys() and not 'txt' in _scrap_attributes:
							local_buf.append(art['cont'][k]['children'][l]['txt'])
						if len(local_buf) > 0:
							p_out_dict[len(p_out_dict.keys())+1] = {
								'p': copy(p3),
								'c': copy(local_buf)
							}

						if 'children' in art['cont'][k]['children'][l].keys():
							for m in art['cont'][k]['children'][l]['children']:

								p4 = copy(p3)
								p4.append(m)

								if 'txt' in art['cont'][k]['children'][l]['children'][m].keys() and not 'txt' in _scrap_attributes:
									p_out_dict[len(p_out_dict.keys())+1] = {
										'p': copy(p4),
										'c': [art['cont'][k]['children'][l]['children'][m]['txt']]
									}
							


	chld_cnt = 0
	for chld in p_node.nextChild():
		chld_cnt += 1
		traverseNodes(p_out_dict, chld, path=_path, typestr_filter_list=typestr_filter_list, maxdepth=maxdepth, maxchildren=maxchildren, scrap_attributes=scrap_attributes) #, get_path=get_path)
		
		if not maxchildren is None and chld_cnt > maxchildren:
			break

def dump_docnodes(p_infile, p_outfile):
	"""Exporta árvore DocNode para lista JSON serial de nós P+C (path +  content)"""

	with open(p_infile, 'r', encoding='utf-8') as fp:
		json_root = json.load(fp)
		tree_root = DocNode.fromJSON(json_root)

	assert not tree_root is None

	out_dict = {}
	traverseNodes(out_dict, tree_root)

	with open(p_outfile, 'w') as fp:
		json.dump(out_dict, fp, indent=4, ensure_ascii=False)

	return out_dict
