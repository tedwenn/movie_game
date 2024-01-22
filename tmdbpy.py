import yaml
import requests
import time
import os
import json
from urllib.parse import urlparse
from datetime import datetime

cache_directory = 'local_storage/tmdb_cache'
cache_duration_days = 7

def get_or_cache_response(func):
    def wrapper(self, url):
        parsed_url = urlparse(url)
        netloc = parsed_url.netloc
        query = parsed_url.query.split('&')
        path_components = parsed_url.path.split('/')
        directory = os.path.join(cache_directory, netloc, *path_components[1:-1], *query)
        ptf = os.path.join(directory, f'{path_components[-1]}.json')
        if os.path.exists(ptf):
            with open(ptf, 'r') as file:
                data = json.load(file)
                return data

        data = func(self, url)
    
        # write data to file
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(ptf, 'w') as file:
            json.dump(data, file)
        return data

    return wrapper

def clear_cache():
    for root, dirs, files in os.walk(cache_directory, topdown=False):
        for file in files:
            ptf = os.path.join(root, file)
            if (time.time() - os.path.getmtime(ptf)) / 60 / 60 / 24 > cache_duration_days:
                print('clearing', ptf)
                os.remove(ptf)

        # Remove empty directories
        for name in dirs:
            directory = os.path.join(root, name)
            if not os.listdir(directory):
                print('clearing', directory)
                os.rmdir(directory)

class TMDB():

    def __init__(self):

        # Your read access token
        with open('config.yaml', 'r') as file:
            config = yaml.safe_load(file)
        self.access_token = config['tmdb']['access_token']

        # clear cache
        clear_cache()

    @get_or_cache_response
    def get_response(self, url):
        print('getting url', url)
        headers = {'Authorization': f'Bearer {self.access_token}'}
        response = requests.get(url, headers=headers)
        time.sleep(0.251) # 40 requests every 10 seconds
        if response.status_code == 200:
            # Process the response data
            data = response.json()
        else:
            # Raise an exception for errors
            raise Exception(f"Error with status code {response.status_code} for URL: {url}")
        
        return data
    
    def film(self, film_id, endpoint=None):
        if endpoint:
            return self.film(film_id)[endpoint]
        url = f'https://api.themoviedb.org/3/movie/{film_id}'
        data = self.get_response(url)
        endpoints = ['credits', 'keywords', 'release_dates']
        for endpoint in endpoints:
            data[endpoint] = self.get_response(f'{url}/{endpoint}')
        return data

    def film_list(self, year=None, page=None, year_range=None, min_vote_count=None):

        if year:

            url = f'https://api.themoviedb.org/3/discover/movie?include_video=false&with_runtime.gte=60&primary_release_year={year}&sort_by=vote_count.desc'

            if min_vote_count:
                url += f'&vote_count.gte={min_vote_count}'

            if page:
                url += f'&page={page}'
                response = self.get_response(url)
                results = response['results']
                for result in results:
                    yield result['id']
            else:
                response = self.get_response(url)
                total_pages = min(response['total_pages'], 500) # API limits to 500 pages
                for page in range(1, total_pages+1):
                    for film_id in self.film_list(year=year, page=page, min_vote_count=min_vote_count):
                        yield film_id
        else:

            for year in range(*year_range):
                for film_id in self.film_list(year=year, min_vote_count=min_vote_count):
                    yield film_id
    
    def __getattr__(self, category):
        return lambda id: self.get_name_by_id(category, id)

    def get_name_by_id(self, category, id):
        url = f'https://api.themoviedb.org/3/{category}/{id}'
        return self.get_response(url)['name']
    
    def search_film_id_by_title(self, title_str):
        url = f'https://api.themoviedb.org/3/search/movie?query={title_str}'
        return self.get_response(url)['results'][0]['id']
