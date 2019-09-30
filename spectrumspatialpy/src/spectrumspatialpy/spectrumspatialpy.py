import requests
import lxml
import urllib
from urllib.parse import quote
import spectrum
import json
import shapely
import pandas as pd
import geopandas as gpd
import colour

class SpatialServer:
	def __init__(self, spectrum):
		''' Constructor for this class. '''
		self.spectrum = spectrum
		self.featureService=FeatureService(self, spectrum)
		self.geometryOperations=Geometry(self, spectrum)
		self.thematics=Thematics(self, spectrum)
		self.namedResourceService=NamedResourceService(self, spectrum)
		
	def Spectrum(self):
		"""Return the Spectrum server. """
		return self.spectrum
		
	def NamedResourceService(self):
		"""Return the Named Resource Service for this server. """
		return self.namedResourceService
		
	def FeatureService(self):
		"""Return the Feature Service for this server. """
		return self.featureService
		
	def GeometryOperations(self):
		"""Return the Geometry Service for this server. """
		return self.geometryOperations
		
	def Thematics(self):
		"""Return the Thematics Service for this server. """
		return self.thematics

class NamedResourceService:
	def __init__(self, spatialserver, spectrum):
		''' Constructor for this class. '''
		self.spatialserver=spatialserver
		self.spectrum=spectrum
		self.service=self.spectrum.getSoapService("soap/NamedResourceService?wsdl")

	def listNamedResources(self, path):
		"""Lists the named resosurces at this server within the specified path. Use '/'for the root to return all resources. """
		return self.service.service.listNamedResources(path)['NamedResource']
		
	def does_exist(self, path, name):
		"""Indicates True/False if the specified named resource exists. """
		try:
			resources=self.service.service.listNamedResources(path)['NamedResource']
			for resource in resources:
				if resource["Path"] == path + "/" + name:
					return True
		except:
			# do nothing
			return False
			
		return False

	def upsert(self, path, name, sz_resource):
		"""Inserts or updates the named resource with the specified contents. """
		resource = lxml.etree.fromstring(sz_resource)
		if self.does_exist(path, name):
			#Update
			self.service.service.updateNamedResource(Resource=resource, Path=path + "/" + name)
		else:
			#Add
			self.service.service.addNamedResource(Resource=resource, Path=path + "/" + name)
		
class FeatureService:
	def __init__(self, spatialserver, spectrum):
		''' Constructor for this class. '''
		self.spatialserver=spatialserver
		self.spectrum=spectrum
		self.service='rest/Spatial/FeatureService'

	def listTables(self):
		try:
			response = self.spectrum.get(self.service + '/listTableNames.json')
			python_obj = json.loads(response.content)
			return python_obj["Response"]["table"]
		except requests.exceptions.RequestException as e:
			print (e)

	def describeTable(self,table):
		print ("TABLE:" + table)
		print ("------------------------------------------------------------------------------------")
		try:
			response = self.spectrum.get(self.service + '/tables' + table + '/metadata.json')
			metadata = json.loads(response.content)

			maxw = 10
			for i in range(len(metadata["Metadata"])):
				if (len(metadata["Metadata"][i]["name"]) > maxw):
					maxw = len(metadata["Metadata"][i]["name"])
			for i in range(len(metadata["Metadata"])):
				w = maxw - len(metadata["Metadata"][i]["name"])
				print (metadata["Metadata"][i]["name"], end='')
				for j in range(w):
					print(' ',end='')
				print ("\t", end='')
				print (metadata["Metadata"][i]["type"], end='')
				if "totalDigits" in metadata["Metadata"][i] and "fractionalDigits" in metadata["Metadata"][i]:
					print ("\t", end='')
					print (" (" + str(metadata["Metadata"][i]["totalDigits"]) + "," + str(metadata["Metadata"][i]["fractionalDigits"]) + ")", end='')
				print ("")
			print ("")
		except requests.exceptions.RequestException as e:  # This is the correct syntax
			print (e)

	def createViewTable(self, query, path, viewName, refTables):
		sz=''
		sz=sz+'<NamedDataSourceDefinition version="MXP_NamedResource_1_5" xmlns="http://www.mapinfo.com/mxp" >'
		sz=sz+'	<ConnectionSet/>'
		sz=sz+'	<DataSourceDefinitionSet>'
		if refTables is not None:
			for refTable in refTables:
				sz=sz+'    <NamedDataSourceDefinitionRef id="id2" resourceID="'+refTable+'"/>	'
		sz=sz+'	<MapinfoSQLDataSourceDefinition id="id3" readOnly="true">'
		sz=sz+'			<DataSourceName>'+viewName+'</DataSourceName>'
		sz=sz+'			<MapinfoSQLQuery>'
		sz=sz+'				<Query>'+query+'</Query>'
		sz=sz+'			</MapinfoSQLQuery>'
		sz=sz+'	</MapinfoSQLDataSourceDefinition>'
		sz=sz+'	</DataSourceDefinitionSet>'
		sz=sz+'	<DataSourceRef ref="id3"/>'
		sz=sz+'</NamedDataSourceDefinition>'
		self.spatialserver.NamedResourceService().upsert(path,viewName,sz)
	
	
	def query(self, q, debug=False, pageLength=0):
	
		class FeatureStream:
			
			def __init__ (self, service, spatialserver, spectrum, q, pageLen, paging, dbg):
				self.spatialserver=spatialserver
				self.service=service
				self.spectrum=spectrum
				self.pageNum=0
				self.pglen=pageLen
				self.featureCollection=None
				self.q=q
				self.first=True
				self.done=False
				self.paging=paging
				self.iter_numReturned=0
				self.total=0
				self.debug=dbg
				
			def __iter__(self):
				return self

			def __querynext__(self):
				try:
					self.iter_numReturned = 0
					done=False
					while not done:
						self.iter_numReturned=0
						done=True
						url = self.service + '/tables/features.json?'
						if self.pglen > 0:
							url = url + 'pageLength=' + str(self.pglen) + '&page=' + str(self.pageNum) + '&'
						url = url +'q=' + self.q
						if self.debug:
							print (url)
						response = self.spectrum.get(url)
						fc = response.json()
						if fc is None:
							fc = {'features':[]}
						if 'features' not in fc:
							fc['features']=[]
						self.iter_numReturned+=len(fc['features'])
						if self.first:
							self.first=False
							self.featureCollection=fc
						elif self.paging:
							self.featureCollection=fc
						else:
							for feature in fc['features']:
								self.featureCollection['features'].append(feature)
						if self.iter_numReturned == self.pglen and not self.paging:
							self.pageNum+=1
							done=False
				except requests.exceptions.RequestException as e:  # This is the correct syntax
					print (e)
				return self.featureCollection
			
			def __next__(self): 
				if self.done:
					raise StopIteration
				else:
					self.pageNum += 1
					fc = self.__querynext__()
					if fc is None or self.iter_numReturned == 0:
						raise StopIteration
					self.total+=self.iter_numReturned
					return fc
					
		paging = pageLength > 0
		if pageLength == 0:
			pageLength = 1000
		fs = FeatureStream(self.service, self.spatialserver, self.spectrum, urllib.parse.quote(q), pageLength, paging, debug)
		if not paging:
			fc = fs.__next__()
			return fc
		else:
			return fs
			
	def get(self, path):
		try:
			response = self.spectrum.get(self.service + path)
			return response
		except requests.exceptions.RequestException as e:
			print (e)

class Geometry:
	def __init__(self, spatialserver, spectrum):
		self.spatialserver=spatialserver
		self.spectrum=spectrum
	
	def __coordinateArray2tupleArray(self, coordinates):
		tuple_array=[]
		for i in range(len(coordinates)):
			tuple_array.append((coordinates[i][0],coordinates[i][1]))
		return tuple_array

	def __arrayOfCoordinateArray2arrayOfTupleArray(self, coordinateArray):
		arrayOfTupleArray=[]
		for i in range(len(coordinateArray)):
			arrayOfTupleArray.append(self.__coordinateArray2tupleArray(coordinateArray[i]))
		return arrayOfTupleArray

	def __arrayOfArrayOfCoordinateArray2arrayOfArrayOfTupleArray(self, coordinateArray):
		arrayOfArrayOfTupleArray=[]
		for i in range(len(coordinateArray)):
			arrayOfArrayOfTupleArray.append(self.__arrayOfCoordinateArray2arrayOfTupleArray(coordinateArray[i]))
		return arrayOfArrayOfTupleArray

	def __ToPolygon(self, coordinates):
		ext=[]
		ints=[]
		for i in range(len(coordinates)):
			if i == 0:
				ext = self.__coordinateArray2tupleArray(coordinates[i])
			else:
				ints.append(self.__coordinateArray2tupleArray(coordinates[i]))
		return shapely.geometry.Polygon(ext, ints)
		
	def __ToMultiPolygon(self, coordinates):
		polys=[]
		for i in range(len(coordinates)):
			polys.append(self.__ToPolygon(coordinates[i]))
		return shapely.geometry.MultiPolygon(polys)

	def __ToPoint(self, coordinates):
		shape=shapely.geometry.Point(coordinates[0],coordinates[1])
		return shape

	def __ToMultiPoint(self, coordinates):
		return shapely.geometry.MultiPoint(self.__coordinateArray2tupleArray(coordinates))

	def __ToLineString(self, coordinates):
		return shapely.geometry.LineString(self.__coordinateArray2tupleArray(coordinates))

	def __ToMultiCurve(self, coordinates):
		lines=[]
		for i in range(len(coordinates)):
			lines.append(self.__ToLineString(coordinates[i]))
		return shapely.geometry.MultiLineString(lines)

	def ToGeometry(self, geometry):
		if geometry is None:
			return None
		# TODO: Set the crs
		
		gtype = geometry['type']
		coords = geometry['coordinates']
		if gtype == 'MultiPolygon':
			return self.__ToMultiPolygon(coords)
		elif gtype == 'Point':
			return self.__ToPoint(coords)
		elif gtype == 'MultiPoint':
			return self.__ToMultiPoint(coords)
		elif gtype == 'MultiLineString':
			return self.__ToMultiCurve(coords)
	#     elif gtype == 'Collection': TODO

	def GeoJSON2GeoDataFrame(self, fc):
		hasGeometry=False
		column_list=[]
		data_list=[]
		if fc['features'] is not None:
			if len(fc['features']) > 0:
				for propset in fc['features'][0]['properties']:
					column_list.append(propset)
				if fc['features'][0]['geometry'] is not None:
					column_list.append('geometry')
					hasGeometry=True
			for feature in fc['features']:
				record=[]
				for prop in feature['properties']:
					record.append(feature['properties'][prop])
				if feature['geometry'] is not None:
					record.append(self.ToGeometry(feature['geometry']))
				if not hasGeometry or feature['geometry'] is not None: 
					data_list.append(record)
		if not hasGeometry:
			gdf=pd.DataFrame(data_list,columns=column_list)
		else:
			gdf=gpd.GeoDataFrame(data_list,columns=column_list,crs={'init': 'epsg:4326'})
		return gdf

class Thematics:
	def __init__(self, spatialserver, spectrum):
		self.spatialserver=spatialserver
		self.spectrum=spectrum
	
	def generate_range_theme_buckets(self, data_series, n_bins, start_color, end_color):
		quantiles = pd.qcut(data_series, n_bins, retbins=True)
		bins=quantiles[1]
		colors = list(colour.Color(start_color).range_to(colour.Color(end_color),n_bins))
		colors.append(colour.Color(end_color))
		range_buckets = list(zip(bins, colors))
		return range_buckets
	
	def convert_to_indiv_value(self, data, theme_property, ranges, lookup_table, stroke_color, stroke_weight, fill_opacity, all_others_fill_color):
		indiv_value_theme_buckets = []
		for feature in data['features']:
			tp = feature['properties'][theme_property]
			fill = all_others_fill_color
			for x in lookup_table.axes[0]:
				if tp == x:
					rv = lookup_table[x]
					for bucket, color in ranges:
						if rv >= bucket:
							fill = color.get_hex()
			row=[tp, {'color':stroke_color, 'weight': stroke_weight, 'fillColor':fill, 'fillOpacity':fill_opacity}]
			indiv_value_theme_buckets.append(row)
		return indiv_value_theme_buckets
	
	def apply_indiv_value_theme(self, data, theme_property, indiv_value_theme_buckets):
		for feature in data['features']:
			tp = feature['properties'][theme_property]
			for x in indiv_value_theme_buckets:
				if tp == x[0]:
					feature['properties']['style'] = x[1]
					

#TODO: How to document functions and arguments

	def write_map(self, map_path, map_name, layers, center, zoom=10000, zoomUnit="mi"):
		sz=''
		sz=sz+'<mxp:NamedMapDefinition version="MXP_NamedResource_1_5" xmlns:mxp="http://www.mapinfo.com/mxp" xmlns:gml="http://www.opengis.net/gml">'
		sz=sz+'    <mxp:ConnectionSet/>'
		sz=sz+'    <mxp:DataSourceDefinitionSet/>'
		sz=sz+'    <mxp:MapDefinition id="id1" name="name1" alias="alias1" uniqueId="' + map_name + '">'
		sz=sz+'        <mxp:DisplayConditions>'
		sz=sz+'            <mxp:MapSize uom="mapinfo:imagesize pixel">'
		sz=sz+'                <mxp:ImageWidth>768</mxp:ImageWidth>'
		sz=sz+'                <mxp:ImageHeight>1024</mxp:ImageHeight>'
		sz=sz+'            </mxp:MapSize>'
		sz=sz+'            <mxp:ZoomAndCenter>'
		sz=sz+'                <mxp:MapZoom uom="mapinfo:length '+zoomUnit+'">'+str(zoom)+'</mxp:MapZoom>'
		sz=sz+'                <gml:Point srsName="EPSG:4326">'
		sz=sz+'                    <gml:coordinates>'+str(center[1])+','+str(center[0])+'</gml:coordinates>'
		sz=sz+'                </gml:Point>'
		sz=sz+'            </mxp:ZoomAndCenter>'
		sz=sz+'            <mxp:DisplayCoordSys>'
		sz=sz+'                <mxp:SRSName>EPSG:4326</mxp:SRSName>'
		sz=sz+'            </mxp:DisplayCoordSys>'
		sz=sz+'            <mxp:MapBackground>'
		sz=sz+'                <mxp:AreaStyle/>'
		sz=sz+'            </mxp:MapBackground>'
		sz=sz+'        </mxp:DisplayConditions>'
		sz=sz+'        <mxp:LayerList>'
		for layerRef in layers:
			layer_path = layerRef[0]
			layer_name = layerRef[1]
			sz=sz+'            <mxp:NamedLayerRef name="'+layer_name+'" resourceID="'+layer_path+'/'+layer_name+'"/>'
		sz=sz+'        </mxp:LayerList>'
		sz=sz+'    </mxp:MapDefinition>'
		sz=sz+'</mxp:NamedMapDefinition>'
		self.spatialserver.NamedResourceService().upsert(map_path,map_name,sz)

	def write_indiv_value_theme(self, path, layer_name, table_name, theme_property, value_map):
		isNumeric=True
		for val_set in value_map:
			if type(val_set[0]) != int and type(val_set[0]) != float:
				isNumeric=False
		sz=''
		sz=sz+'<mxp:NamedLayer version="MXP_NamedResource_1_5" xmlns:mxp="http://www.mapinfo.com/mxp" xmlns:gml="http://www.opengis.net/gml">'
		sz=sz+'    <mxp:ConnectionSet/>'
		sz=sz+'    <mxp:DataSourceDefinitionSet>'
		sz=sz+'        <mxp:NamedDataSourceDefinitionRef id="id1" resourceID="'+table_name+'"/>'
		sz=sz+'    </mxp:DataSourceDefinitionSet>'
		sz=sz+'    <mxp:FeatureLayer id="id2" name="'+layer_name+'" alias="'+layer_name+'" namedLabelSourceRef="'+table_name+'">'
		sz=sz+'        <mxp:DataSourceRef ref="id1"/>'
		sz=sz+'        <mxp:FeatureStyleModifierThemeList>'
		sz=sz+'            <mxp:FeatureStyleIndividualValueTheme id="id3" name="IndividualValueTheme" alias="id_1">'
		sz=sz+'                <mxp:IndividualValueExpression>'
		if isNumeric:
			sz=sz+'                    <mxp:NumericValueExpression>'
			sz=sz+'                        <mxp:MapinfoNumericExpression>' + theme_property + '</mxp:MapinfoNumericExpression>'
			sz=sz+'                    </mxp:NumericValueExpression>'
		else:
			sz=sz+'                    <mxp:StringValueExpression>'
			sz=sz+'                        <mxp:MapinfoStringExpression>' + theme_property + '</mxp:MapinfoStringExpression>'
			sz=sz+'                    </mxp:StringValueExpression>'
		sz=sz+'                </mxp:IndividualValueExpression>'
		sz=sz+'                <mxp:IndividualValueBaseStyle applyStylePart="all"/>'
		sz=sz+'                <mxp:IndividualValueBinSet>'
		for val_set in value_map:
			sz=sz+'                    <mxp:IndividualValueBin>'
			if isNumeric:
				sz=sz+'                        <mxp:NumericValue>'+str(val_set[0])+'</mxp:NumericValue>'
			else:
				sz=sz+'                        <mxp:StringValue>'+str(val_set[0])+'</mxp:StringValue>'
			sz=sz+'                        <mxp:CompositeStyle>'
			sz=sz+'                            <mxp:AreaStyle>'
			sz=sz+'                                <mxp:LineStyle stroke="'+val_set[1]["color"]+'" width="'+str(val_set[1]["weight"])+'" width-unit="mapinfo:imagesize pixel">'
			sz=sz+'                                    <mxp:Pen>mapinfo:Pen 2</mxp:Pen>'
			sz=sz+'                                </mxp:LineStyle>'
			sz=sz+'                                <mxp:Interior fill="(#id1)" fill-opacity="'+str(val_set[1]["fillOpacity"])+'">'
			sz=sz+'                                    <mxp:Defs>'
			sz=sz+'                                        <mxp:Pattern id="id1">'
			sz=sz+'                                            <mxp:Bitmap uri="mapinfo:brush 2">'
			sz=sz+'                                                <mxp:ColorAdjustmentSet>'
			sz=sz+'                                                    <mxp:ColorAdjustment color-1="nonWhite" color-2="'+val_set[1]["fillColor"]+'"/>'
			sz=sz+'                                                    <mxp:ColorAdjustment color-1="white" color-2="'+val_set[1]["fillColor"]+'"/>'
			sz=sz+'                                                </mxp:ColorAdjustmentSet>'
			sz=sz+'                                            </mxp:Bitmap>'
			sz=sz+'                                        </mxp:Pattern>'
			sz=sz+'                                    </mxp:Defs>'
			sz=sz+'                                </mxp:Interior>'
			sz=sz+'                            </mxp:AreaStyle>'
			sz=sz+'                        </mxp:CompositeStyle>'
			sz=sz+'                    </mxp:IndividualValueBin>'
		sz=sz+'                    <mxp:AllOthersStyle>'
		sz=sz+'                        <mxp:CompositeStyle>'
		sz=sz+'                            <mxp:AreaStyle>'
		sz=sz+'                                <mxp:LineStyle stroke="black" width="1.0" width-unit="mapinfo:imagesize pixel">'
		sz=sz+'                                    <mxp:Pen>mapinfo:Pen 2</mxp:Pen>'
		sz=sz+'                                </mxp:LineStyle>'
		sz=sz+'                                <mxp:Interior fill="(#id1)" fill-opacity="0.0">'
		sz=sz+'                                    <mxp:Defs>'
		sz=sz+'                                        <mxp:Pattern id="id1">'
		sz=sz+'                                            <mxp:Bitmap uri="mapinfo:brush 1">'
		sz=sz+'                                                <mxp:ColorAdjustmentSet>'
		sz=sz+'                                                    <mxp:ColorAdjustment color-1="black" color-2="black"/>'
		sz=sz+'                                                    <mxp:ColorAdjustment color-1="white" color-2="white"/>'
		sz=sz+'                                                </mxp:ColorAdjustmentSet>'
		sz=sz+'                                            </mxp:Bitmap>'
		sz=sz+'                                        </mxp:Pattern>'
		sz=sz+'                                    </mxp:Defs>'
		sz=sz+'                                </mxp:Interior>'
		sz=sz+'                            </mxp:AreaStyle>'
		sz=sz+'                        </mxp:CompositeStyle>'
		sz=sz+'                        <mxp:LegendRowOverride visible="false">'
		sz=sz+'                            <mxp:Text/>'
		sz=sz+'                        </mxp:LegendRowOverride>'
		sz=sz+'                    </mxp:AllOthersStyle>'
		sz=sz+'                </mxp:IndividualValueBinSet>'
		sz=sz+'            </mxp:FeatureStyleIndividualValueTheme>'
		sz=sz+'        </mxp:FeatureStyleModifierThemeList>'
		sz=sz+'    </mxp:FeatureLayer>'
		sz=sz+'</mxp:NamedLayer>'
		self.spatialserver.NamedResourceService().upsert(path,layer_name,sz)
