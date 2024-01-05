import pprint
from film import Film, FilmSet
import os

pp = pprint.PrettyPrinter(indent=4)

film_ids = []
for filename in os.listdir('api_responses'):
    film_ids.append(int(filename.split('.')[0]))
films = FilmSet(film_ids)
pp.pprint(films.get_similar_films(313369)[:10])