from flask import Flask, jsonify, request, send_file
import os
import requests
from geopy.geocoders import Nominatim
from shapely.geometry import shape, Point
from fake_useragent import UserAgent, FakeUserAgentError
import numpy as np
# import folium
# from folium.plugins import MarkerCluster

def get_random_useragent():
  try:
    ua = UserAgent()
    return ua.random
  except FakeUserAgentError:
    return 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'

def get_city_polygon(city):
  try:
    print("Getting city polygon...")
    geolocator = Nominatim(user_agent=get_random_useragent())
    location = geolocator.geocode(city)
    if location is not None:
      print(f"Found location: {location}")
      url = f'https://nominatim.openstreetmap.org/search.php?q={location.address}&polygon_geojson=1&format=jsonv2'
      headers = {'User-Agent': get_random_useragent()}
      response = requests.get(url, headers=headers)
      response_json = response.json()
      if response_json:
        print(f"Response JSON: {response_json}")
        polygon_geojson = response_json[0]['geojson']
        polygon = shape(polygon_geojson)
        print(f"Got city polygon: {polygon}")
        return polygon
  except Exception as e:
    print(f"An error occurred while getting the city polygon for {city}: {e}")
    return None

def create_grid(city_polygon):
  try:
    print("Generating the list of grid points for this city...")
    minx, miny, maxx, maxy = city_polygon.bounds
    # Number of grid points in x and y direction
    nx = round((maxx - minx) * 69)  # number of points is distance (in degrees) times miles per degree
    ny = round((maxy - miny) * 69)  # same for y direction
    x_coords = np.linspace(minx, maxx, nx)
    y_coords = np.linspace(miny, maxy, ny)
    grid_points = []
    for x in x_coords:
      for y in y_coords:
        point = Point(x, y)
        if city_polygon.contains(point):
          grid_points.append((x, y))
    print(f"Successfully generated {len(grid_points)} grid points.")
    return grid_points
  except Exception as e:
    print(f"An error occurred while creating the grid in the city: {e}")
    return []

# def plot_grid_points(grid_points, filename):
#     if grid_points:
#         # Create a folium map centered at the first grid point
#         folium_map = folium.Map(location=[grid_points[0][1], grid_points[0][0]], zoom_start=13)

#         # Create a marker cluster
#         marker_cluster = MarkerCluster().add_to(folium_map)

#         # Add all grid points to the map within the marker cluster
#         for i, point in enumerate(grid_points):
#             folium.CircleMarker([point[1], point[0]], radius=1, color="red").add_to(marker_cluster)
#             if i % 100 == 0:  # log every 100 points
#                 print(f"Plotted {i} points so far.")

#         # Save the map to an HTML file
#         folium_map.save(filename + '.html')
#         print(f"Successfully plotted all {len(grid_points)} points.")

def generate_google_maps_url(city_name, location_of_interest, point):
  # Order of coordinates is important for Google Maps
  longitude, latitude = point
  
  # https://www.google.com/maps/search/{keyword}/@{LAT},{LONG},15z
  google_maps_url = f'https://www.google.com/maps/search/{location_of_interest}/@{latitude},{longitude},15z'
  
  return google_maps_url

def write_urls_to_file(urls, filename):
  try:
    with open(filename, 'w') as f:
      for url in urls:
        f.write(f"{url}\n")
    print(f"Successfully wrote {len(urls)} URLs to {filename}.")
  except Exception as e:
    print(f"An error occurred while writing URLs to the file: {e}")
  
app = Flask(__name__)

@app.route('/generate', methods=['POST'])
def generate():
  try:
    data = request.get_json()
    city_name = data['city_name']
    location_of_interest = data['location_of_interest']
    urls_filename = f"urls_{city_name.replace(' ', '_')}_{location_of_interest.replace(' ', '_')}.txt"

    city_polygon = get_city_polygon(city_name)
    grid_points = create_grid(city_polygon)
    urls = [generate_google_maps_url(city_name, location_of_interest, point) for point in grid_points]
    write_urls_to_file(urls, urls_filename)

    return jsonify({'message': 'URLs generated and saved to file successfully'}), 200
  except Exception as e:
    return jsonify({'error': 'Internal server error', 'message': str(e)}), 500

@app.route('/generate_urls', methods=['GET'])
def generate_urls():
  try:
    city_name = request.args.get('city_name')
    location_of_interest = request.args.get('location_of_interest')

    urls_filename = f"urls_{city_name.replace(' ', '_')}_{location_of_interest.replace(' ', '_')}.txt"

    if not os.path.exists(urls_filename):
      # response = requests.post('http://localhost:5000/generate', json={'city_name': city_name, 'location_of_interest': location_of_interest})
      response = requests.post('https://generate-google-maps-urls.holdeeno.repl.co/generate', json={'city_name': city_name, 'location_of_interest': location_of_interest})
      if response.status_code != 200:
        return jsonify({'error': 'Could not generate URLs', 'details': response.text}), 500

    with open(urls_filename, 'r') as f:
      urls = f.readlines()
    return jsonify(urls), 200

  except Exception as e:
    return jsonify({'error': 'Internal server error', 'message': str(e)}), 500

if __name__ == '__main__':
  app.run(host='0.0.0.0')