
import os
import geopandas as gpd
import pyogrio
import json

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

	ret = {}

	file_count = 0
	layer_count = 0

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

			try:
				df = gpd.read_file(fullpath, read_geometry=True) #, engine="pyogrio", encoding=encoding)
				gts = df.geom_type.unique()
				df.drop(columns="geometry")
			except pyogrio.errors.DataSourceError as dse:
				print("DataSourceError:", dse, relpath)
				continue

			cols = df.columns.tolist()
			layer_cols = [col for col in cols if col.lower() == p_layer_field.lower()]

			try:
				layer_vals = list(df[layer_cols[0]].unique())
				corrigir_chars(layer_vals)
				layer_count += len(layer_vals)
				ret[len(ret.keys())+1] = { "p": relpath, "gt": gts[0], "l": layer_vals }
			except IndexError as ie:
				print("IndexError:", ie, relpath)
				print("cols:", cols)
				# ret.append([relpath, os.path.splitext(the_file)[0]])
				ret[len(ret.keys())+1] = { "p": relpath, "l": [os.path.splitext(the_file)[0]] } 
				layer_count += 1


	with open(os.path.join(p_path_versao, 'output', 'layers.json'), "w") as fp:
		json.dump(ret, fp, indent=4, ensure_ascii=False)

	print(f"Final, totais ficheiros: {file_count}, totais layers: {layer_count}")

def tokenizar_layers_logicas(p_path_versao):

	lyrfile_path = os.path.join(p_path_versao, 'output', 'layers.json')

	ll_obj = None
	with open(lyrfile_path) as fp:
		ll_obj = json.load(fp)

	assert not ll_obj is None