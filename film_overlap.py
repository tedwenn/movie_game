from film import Film
import pandas as pd

class FilmOverlap():

    def __init__(self, film):
        self.df = film.film_info_df
        self.df['known'] = None

    def guess(self, other_film):
        def cool_func(row):
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
        df = df.apply(cool_func, axis=1)
        overlap = df[['overlap']]
        self.df = df[original_columns]

        return overlap

a = FilmOverlap(Film(11))
guesses = [181808, 330459, 140607, 181812]
for guess in guesses:
    print('guessing', guess)
    print(a.guess(Film(guess)))
    print(a.df['known'])