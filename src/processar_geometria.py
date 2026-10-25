
import os
import geopandas as gpd
import pyogrio
import json


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

			try:
				df = gpd.read_file(fullpath, read_geometry=True)
				gts = df.geom_type.unique()
				df.drop(columns="geometry")
			except pyogrio.errors.DataSourceError as dse:
				print("DataSourceError:", dse, relpath)
				continue

			cols = df.columns.tolist()
			layer_cols = [col for col in cols if col.lower() == p_layer_field.lower()]

			try:
				layer_vals = list(df[layer_cols[0]].unique())
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

