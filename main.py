import tmdbpy

def main():
    tmdb = tmdbpy.TMDB()
    for film_id in tmdb.film_list(year_range=(1900, 2024)):
        tmdb.film(film_id)

if __name__ == "__main__":
    main()