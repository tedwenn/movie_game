from film import Film
from pprint import pformat
from datetime import datetime, timedelta
from similarity_matrix import SimilarityMatrix
import pandas as pd
import random
from itertools import islice
import tmdbpy
tmdb = tmdbpy.TMDB()

class Game():

    def __init__(self, film_id=None):
        year_range = (2022, 2025)
        if film_id is None:
            all_film_ids = tmdb.film_list(year_range=year_range, min_vote_count=50)
            top_film_ids = list(islice(all_film_ids, 50))
            film_id = random.choice(top_film_ids)
        self.answer = Answer(Film(film_id))
        self.ranked_similarities = SimilarityMatrix(year_range).get_ranked_similarities(film_id)
        self.guess_films = []
        print('answer:', film_id)

    def guess(self, film_name_str):
        guess_film_id = tmdb.search_film_id_by_title(film_name_str)
        guess_film = Film(guess_film_id)

        print('guessing', guess_film.title)
        self.guess_films.append(guess_film)
        self.answer.guess(guess_film)
        # self.display_status()

    @property
    def status(self):
        return {'info': self.answer.status, 'guess_similarity_scores': self.guess_similarity_scores}
    
    @property
    def guess_similarity_scores(self):
        guess_data = {guess_film.film_id: guess_film.title for guess_film in self.guess_films}
        guess_df = pd.DataFrame.from_dict(guess_data, orient='index', columns=['title'])
        guess_df = self.ranked_similarities.merge(guess_df, left_index=True, right_index=True)
        return guess_df.to_dict(orient='records')


    # def display_status(self):
    #     print(self.answer)
    #     self.display_ranked_similarities()

    # def display_ranked_similarities(self):
    #     guess_data = {guess_film.film_id: guess_film.title for guess_film in self.guess_films}
    #     guess_df = pd.DataFrame.from_dict(guess_data, orient='index', columns=['title'])
    #     # guess_df = guess_df.merge(self.ranked_similarities, left_index=True, right_index=True)
    #     guess_df = self.ranked_similarities.merge(guess_df, left_index=True, right_index=True)
    #     print(guess_df)


class Answer():

    def __init__(self, film):
        self.df = film.film_info_df
        self.df['known'] = None
        self.df['overlap'] = None

    @property
    def status(self):
        overlap = {}
        known = {}
        for feature_name, row in self.df.iterrows():
            known_values = row['known']
            overlap_values = row['overlap']
            if row['norm_type'] == 'binary':
                if len(known_values) > 0:
                    if id_type := row['id_type']:
                        known[feature_name] = [tmdb.get_name_by_id(id_type, x) for x in known_values]
                        if len(overlap_values) > 0:
                            overlap[feature_name] = [tmdb.get_name_by_id(id_type, x) for x in overlap_values]
            else:
                if feature_name == 'release_date':
                    known_values = tuple([(datetime(1970, 1, 1) + timedelta(days=d)).strftime('%Y-%m-%d') if d else None for d in known_values])
                known[feature_name] = known_values
                overlap[feature_name] = overlap_values
        return {'overlap': overlap, 'known': known}

    def __repr__(self):
        return pformat(self.status, indent=4, width=100)

    def guess(self, other_film):
        def guess_row(row):
            value = row['value']
            value_other = row['value_other']
            value_known = row['known']
            if row['norm_type'] == 'binary':
                value_known = value_known or []
                overlap = []
                known = []
                for x in value:
                    if x in value_other:
                        overlap.append(x)
                        known.append(x)
                    elif x in value_known:
                        known.append(x)
            else:
                min_x, max_x = value_known or (None, None)
                if value_other < value:
                    overlap = 'under'
                    if min_x is None or value_other > min_x:
                        min_x = value_other
                elif value_other > value:
                    overlap = 'over'
                    if max_x is None or value_other < max_x:
                        max_x = value_other
                else:
                    overlap = 'match'
                    min_x, max_x = (value, value)
                known = (min_x, max_x)
            row['overlap'] = overlap
            row['known'] = known
            return row
        
        original_columns = self.df.columns
        df = self.df.merge(other_film.film_info_df, left_index=True, right_index=True, suffixes=('', '_other'))
        df = df.apply(guess_row, axis=1)
        self.df = df[original_columns]
