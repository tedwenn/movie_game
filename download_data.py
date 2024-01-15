import requests
import time
import os
import json
from datetime import datetime

# Your read access token
access_token = 'eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJhMjc0MzE5ODRjYjQ5ZDE5NWIxZTk2MjQxMzllNjcyOCIsInN1YiI6IjY1OTNmZDQ0MDI4ZjE0NzdiYmM2MGQ2YiIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.dKw_as9PsyvjLcLnIfH0GSBy66E-a9SW_ff232Q4p2M'
api_key = 'a27431984cb49d195b1e9624139e6728'
api_key_url = f'?api_key={api_key}'

# Include the token in the headers
headers = {
    'Authorization': f'Bearer {access_token}'
}

def get_response(url):
    print('getting', url)
    response = requests.get(url, headers=headers)
    time.sleep(0.251) # 40 requests every 10 seconds
    if response.status_code == 200:
        # Process the response data
        data = response.json()
    else:
        # Raise an exception for errors
        raise Exception(f"Error with status code {response.status_code} for URL: {url}")
    return data

def get_film_response(id, endpoint=None):

    if endpoint:
        return get_film_response(id)[endpoint]

    ptf = f'api_responses/{id}.json'
    if os.path.exists(ptf):
        # If the file exists, read it
        with open(ptf, 'r') as file:
            data = json.load(file)
            return data

    url = f'https://api.themoviedb.org/3/movie/{id}'
    data = get_response(url)
    endpoints = ['credits', 'keywords', 'release_dates', 'similar_movies']
    for endpoint in endpoints:
        data[endpoint] = get_response(f'{url}/{endpoint}')

    with open(ptf, 'w') as file:
        json.dump(data, file)

    return data

def get_top_films(year=None, page=None):

    today = datetime.now()

    if year:

        date_str = today.strftime('%Y-%m-%d')
        url = f'https://api.themoviedb.org/3/discover/movie?include_video=false&with_runtime.gte=60&release_date.lte={date_str}&primary_release_year={year}&vote_count.gte=50&sort_by=vote_count.desc'

        if page:
            url += f'&page={page}'
            response = get_response(url)
            results = response['results']
            for result in results:
                yield result['id']
        else:
            response = get_response(url)
            total_pages = min(response['total_pages'], 500) # API limits to 500 pages
            for page in range(1, total_pages+1):
                for film_id in get_top_films(year, page):
                    yield film_id
    else:

        for year in range(today.year, 1899, -1):
            for film_id in get_top_films(year, page):
                yield film_id

def download_data():
    for film_id in get_top_films():
        try:
            get_film_response(film_id)
        except Exception as e:
            if str(e).startswith('Error with status code 404'):
                print(e)
            else:
                raise e