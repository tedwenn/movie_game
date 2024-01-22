from film import Film
from pprint import pformat
from datetime import datetime, timedelta
import tmdbpy
tmdb = tmdbpy.TMDB()

class Game():

    def __init__(self, film_id):
        self.answer = Answer(Film(film_id))

class Answer():

    def __init__(self, film):
        self.df = film.film_info_df
        self.df['known'] = None
        self.df['overlap'] = None

    def __repr__(self):
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
        return pformat({'overlap': overlap, 'known': known}, indent=4, width=100)

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
                overlap = value_other - value
                min_x, max_x = value_known or (None, None)
                if overlap < 0 and (min_x is None or value_other > min_x):
                    min_x = value_other
                elif overlap > 0 and (max_x is None or value_other < max_x):
                    max_x = value_other
                known = (min_x, max_x)
            row['overlap'] = overlap
            row['known'] = known
            return row
        
        original_columns = self.df.columns
        df = self.df.merge(other_film.film_info_df, left_index=True, right_index=True, suffixes=('', '_other'))
        df = df.apply(guess_row, axis=1)
        self.df = df[original_columns]

Game(11)