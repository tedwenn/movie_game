from download_data import get_response

def get_name(person_id):
    url = f'https://api.themoviedb.org/3/person/{person_id}'
    return get_response(url)['name']