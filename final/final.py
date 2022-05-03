from pathlib import Path

import pandas
from shapely.geometry import Polygon
from scipy.spatial import Voronoi

import numpy
from stormevents import StormEvent
import geopandas
from stormevents.coops import COOPS_Station
import xarray
from geopandas import GeoSeries

data_directory = Path() / 'data'
countries = geopandas.read_file(geopandas.datasets.get_path('naturalearth_lowres'))
storm = StormEvent('florence', 2018)
best_track = storm.track(advisories=['BEST'])
track_bounds = numpy.stack([
    best_track.data[['longitude', 'latitude']].min().values,
    best_track.data[['longitude', 'latitude']].max().values,
], axis=1)
track_bounds[:, 0] -= 1
track_bounds[:, 1] += 1
wind_swath_34kt = best_track.wind_swaths(wind_speed=34)['BEST']['20180830T060000']
filename = data_directory / 'run_20220502_florence2018_coopsstations' / 'runs' / 'unperturbed' / 'fort.61.nc'
modeled_water_levels = xarray.open_dataset(filename, drop_variables=['neta', 'nvel', 'max_nvdll', 'max_nvell'])
modeled_water_levels['station_name'] = modeled_water_levels['station_name'].astype(str).astype(int)
modeled_water_levels = modeled_water_levels.rename({
    'station_name': 'nos_id',
})
modeled_water_levels = modeled_water_levels.assign_coords({
    'station': modeled_water_levels['nos_id'],
    'x': modeled_water_levels['x'],
    'y': modeled_water_levels['y'],
})
modeled_water_levels = modeled_water_levels.drop(['nos_id'])
modeled_water_levels = modeled_water_levels.rename({
    'station': 'nos_id',
})
stations_bounds = numpy.array([
    [modeled_water_levels['x'].min(), modeled_water_levels['x'].max()],
    [modeled_water_levels['y'].min(), modeled_water_levels['y'].max()],
])
stations_bounds[:, 0] -= 1
stations_bounds[:, 1] += 1

first_value_of_interest = 'v'

voronoi_regions = Voronoi(numpy.stack([modeled_water_levels['x'], modeled_water_levels['y']], axis=1))

polygons = {}
for region_index, region in enumerate(voronoi_regions.regions):
    if region_index in voronoi_regions.point_region:
        point_indices = voronoi_regions.point_region[voronoi_regions.point_region == region_index]
        points = voronoi_regions.points[[index for index in point_indices if index != -1]]
        point = points[0, :]
        entry = modeled_water_levels.where((modeled_water_levels['x'] == point[0]) & (modeled_water_levels['y'] == point[1]), drop=True)
        polygon = Polygon([voronoi_regions.vertices[vertex_index] for vertex_index in region if vertex_index != -1])
        polygons[int(entry['nos_id'][0].values)] = polygon
polygons = GeoSeries(polygons)
