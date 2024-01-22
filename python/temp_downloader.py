import tmdbpy
import film

tmdb = tmdbpy.TMDB()
for start_year in range(2024, 1899, -1):
    print(start_year)
    for film_id in tmdb.film_list(year_range=(start_year, start_year+1), min_vote_count=50):
        film.Film(film_id)
# for film_id in tmdb.film_list(year_range=(1900, 2024), min_vote_count=50):
#     f = film.Film(film_id)