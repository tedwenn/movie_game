import tmdbpy
import film
import similarity_matrix

def main():
    # tmdb = tmdbpy.TMDB()
    # for film_id in tmdb.film_list(year_range=(1900, 2024)):
    #     f = film.Film(film_id)
    print(similarity_matrix.SimilarityMatrix().get_ranked_similarities(667538))

if __name__ == "__main__":
    main()