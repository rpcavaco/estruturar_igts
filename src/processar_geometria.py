
import os
import geopandas as gpd
import pyogrio
import json
import re

from shutil import copy2
from typing import Optional

from osgeo import ogr, gdal

from .elementos import ReconhecimentoElementos
from .dict_list_manager import DictListManager, find_unserializable
from .ui.progress_bar import ProgressDialog

#import warnings

# warnings.simplefilter("error")
os.environ["SHAPE_RESTORE_SHX"] = "YES"

class GDALLog:
    def __init__(self):
        self.messages = []

    def handler(self, err_class, err_no, msg):
        self.messages.append((err_class, err_no, msg))
	
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

def layer_name_for(path: str, used: set, use_parentdir = False) -> str:
	"""Shapefile stem -> safe, unique layer name."""
	basename = os.path.basename(path)
	prename = None
	if use_parentdir:
		prename = re.sub(r"\W+", "_", os.path.basename(os.path.dirname(path))).strip("_").lower()
	name = re.sub(r"\W+", "_", os.path.splitext(basename)[0]).strip("_").lower() or "layer"

	i = 2
	if use_parentdir:
		fullname = f"{prename}_{name}"
	else:
		fullname = name
	if fullname[0].isdigit():
		fullname = f"l_{fullname}"

	base = fullname
	
	while fullname in used:
		fullname = f"{base}_{i}"
		i += 1

	used.add(fullname)
	return fullname

def transferir_para_geopkg(p_app, p_path, p_out_gpkg_path, p_geom_format, p_encoding, out_msgs, overwrite=True):

	gdal.UseExceptions()
	ogr.UseExceptions()

	del out_msgs[:]

	if p_geom_format == "SHP":
		geom_ext = ".shp"

	open_opts = [f"ENCODING={p_encoding}"]
	gpkg_kwargs = dict(
		format="GPKG",
		accessMode="overwrite",		  # replaces this layer only, not the whole file
		geometryType="PROMOTE_TO_MULTI",  # avoids mixed Polygon/MultiPolygon in shapefiles
		layerCreationOptions=["GEOMETRY_NAME=geom", "SPATIAL_INDEX=YES"],
		dstSRS="EPSG:3763"
	)
	used = set()

	drv = ogr.GetDriverByName("GPKG")

	if os.path.exists(p_out_gpkg_path):
		if not overwrite:
			raise FileExistsError(f"{p_out_gpkg_path} existe e overwrite = False")
		drv.DeleteDataSource(p_out_gpkg_path)

	dst_ds = drv.CreateDataSource(p_out_gpkg_path)
	file_count = 0

	found_files = []
	for dirpath, folders, files in os.walk(p_path):	
		for the_file in files:
			if not the_file.lower().endswith(geom_ext.lower()):
				continue
			found_files.append((os.path.join(dirpath, the_file), the_file))

	contagem = len(found_files)

	log = GDALLog()
	gdal.PushErrorHandler(log.handler)

	try:
		with ProgressDialog(p_app, total=contagem, desc="Convertendo") as d:
			for full_path, the_file in found_files:
				
				if d.cancelled: break

				# relpath = os.path.relpath(fullpath, start=p_path)
				src_ds = gdal.OpenEx(full_path, gdal.OF_VECTOR, open_options=open_opts)
				src_layer = src_ds.GetLayer(0)
				name = layer_name_for(full_path, used, use_parentdir=True)
		
				gpkg_kwargs["layerName"] = name
				if src_layer.GetSpatialRef() is None:
					gpkg_kwargs["srcSRS"] = f"EPSG:3763"

				opts = gdal.VectorTranslateOptions(**gpkg_kwargs)
				result = None
				try:
					result = gdal.VectorTranslate(dst_ds, src_ds, options=opts)
				except RuntimeError as err:
					out_msgs.append(f"Erro: {err}")
					
				if result is None:
					out_msgs.append(f"Erro: falhou a conversão de {the_file}")
					src_ds = None
					d.update()
					continue

				file_count += 1
				# if file_count % 20 == 0:
				# 	print(f"ficheiros lidos: {file_count}")

				#print(f"{the_file} -> layer '{name}' ({src_layer.GetFeatureCount()} features)")
				src_ds = None

				d.update()

	finally:
		gdal.PopErrorHandler()

	for cls, no, msg in log.messages:
		tipo = "Erro"
		if cls == gdal.CE_Warning:
			tipo = "Aviso"
		out_msgs.append(f"{tipo} {no}: {msg}")

	return file_count

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
				df = None # read_file_strict(messages, fullpath, read_geometry=True, engine="pyogrio", on_invalid="fix")
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