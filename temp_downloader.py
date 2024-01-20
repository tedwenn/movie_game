import tmdbpy
import film

tmdb = tmdbpy.TMDB()
for start_year in range(2023, 1899, -1):
    for film_id in tmdb.film_list(year_range=(start_year, 2024), min_vote_count=50):
        f = film.Film(film_id)