
import os
import geopandas as gpd
import pyogrio
import json

from shutil import copy2

from .elementos import ReconhecimentoElementos
from .dict_list_manager import DictListManager, find_unserializable

import warnings

# warnings.simplefilter("error")
os.environ["SHAPE_RESTORE_SHX"] = "YES"

def corrigir_chars(p_layer_vals):
	for i, val in enumerate(p_layer_vals):
		p_layer_vals[i] = val.replace('Ã', 'Á')
		p_layer_vals[i] = p_layer_vals[i].replace('Ã³', 'ó')
		p_layer_vals[i] = p_layer_vals[i].replace('Ã§', 'ç')		
		p_layer_vals[i] = p_layer_vals[i].replace('Ã£', 'ã')	
		p_layer_vals[i] = p_layer_vals[i].replace('Ã¡', 'á')		
		p_layer_vals[i] = p_layer_vals[i].replace('Ãº', 'ú')		
		p_layer_vals[i] = p_layer_vals[i].replace('Ãµ', 'õ')
		p_layer_vals[i] = p_layer_vals[i].replace('Ã­', 'í')


def ler_layers_logicas(p_path_versao, p_path, p_layer_field, p_geom_ext):

	global_ret = {}
	ret = {}

	file_count = 0
	layer_count = 0

	layers_file_path = os.path.join(p_path_versao, 'output', 'layers.json')
	if os.path.exists(layers_file_path):
		with open(layers_file_path, "r", encoding="utf-8") as fp:
			try:
				global_ret.update(json.load(fp))
				del global_ret["layers"]
			except:
				pass

	messages = []
	for dirpath, folders, files in os.walk(p_path):

		for the_file in files:

			if not the_file.lower().endswith(p_geom_ext.lower()):
				continue

			file_count += 1

			if file_count % 20 == 0:
				print(f"ficheiros lidos: {file_count}")

			fullpath = os.path.join(dirpath, the_file)
			relpath = os.path.relpath(fullpath, start=p_path)

			# encoding = "utf-8"
			# with open(fullpath.replace(".shp", ".dbf"), "rb") as f:
			# 	f.seek(29)
			# 	ldid = f.read(1)[0]
			# 	if hex(ldid) == '0x3':
			# 		encoding = "cp1252"

			del messages[:]

			try:
				df = read_file_strict(messages, fullpath, read_geometry=True, engine="pyogrio", on_invalid="fix")
				if df is None:
					print('>> df is None', the_file)
				gts = df.geom_type.unique()
				df.drop(columns="geometry")
			except pyogrio.errors.DataSourceError as dse:
				print(">DataSourceError< :", dse, relpath)
				continue

			for i, msg in enumerate(messages):
				print("># msg" ,i, ":", msg)

			# with warnings.catch_warnings(reco):
			# 	warnings.simplefilter("error", RuntimeWarning)
			# 	df = gpd.read_file(fullpath, read_geometry=True, engine="pyogrio") #, encoding=encoding)
			# 	gts = df.geom_type.unique()
			# 	df.drop(columns="geometry")

			# try:
			# 	print(">>>>")
			# 	df = gpd.read_file(fullpath, read_geometry=True) #, engine="pyogrio", encoding=encoding)
			# 	gts = df.geom_type.unique()
			# 	df.drop(columns="geometry")
			# except pyogrio.errors.DataSourceError as dse:
			# 	print("DataSourceError:", dse, relpath)
			# 	continue
			# except RuntimeError as rwe:
			# 	print(">> Exception:", rwe, relpath)
			# 	raise RuntimeError("bwa!!")

			cols = df.columns.tolist()
			layer_cols = [col for col in cols if col.lower() == p_layer_field.lower()]

			try:
				layer_vals = list(df[layer_cols[0]].unique())
				corrigir_chars(layer_vals)
				layer_count += len(layer_vals)
				retkey = len(ret.keys())+1
				ret[retkey] = { "p": relpath, "gt": gts[0], "l": [] }
				for lv in layer_vals:
					ret[retkey]["l"].append({ "txt": lv })
			except IndexError as ie:
				print("IndexError:", ie, relpath)
				print("cols:", cols)
				# ret.append([relpath, os.path.splitext(the_file)[0]])
				ret[len(ret.keys())+1] = { "p": relpath, "l": [{ "txt": os.path.splitext(the_file)[0] }] } 
				layer_count += 1


	global_ret["layers"] = ret
	find_unserializable(global_ret)

	with open(layers_file_path, "w", encoding="utf-8") as fp:
		json.dump(global_ret, fp, indent=4, ensure_ascii=False)

	print(f"Final, totais ficheiros: {file_count}, totais layers: {layer_count}")

def elementos_layers_logicas(p_path_versao):

	rref = ReconhecimentoElementos()

	lyrs_obj = {}
	lyrfile_path = rref.tratarNomesLayers(p_path_versao, lyrs_obj, "layers.json")
	bak_lyrfile_path = lyrfile_path.replace(".json", ".bak.json")

	copy2(lyrfile_path, bak_lyrfile_path)

	find_unserializable(lyrs_obj)

	with open(lyrfile_path, "w", encoding="utf-8") as fp:
		json.dump(lyrs_obj, fp, indent=4, ensure_ascii=False, cls=DictListManager.Encoder)