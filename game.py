from film import SimilarityMatrix, Film, id_to_str
import pandas as pd
import pprint as pp
import person

class Game():

    def __init__(self, answer):
        self.answer = Film(answer)
        self.answer_info = self.answer.film_info
        self.ranked_similarities = SimilarityMatrix().get_ranked_similarities(self.answer.film_id)
        self.guesses = []
        self.known_info = {}
        for feature_name, value in self.answer_info.items():
            if isinstance(value, list):
                self.known_info[feature_name] = []
            else:
                self.known_info[feature_name] = (None, None)

    def guess(self, film_id):

        print('guessing', film_id)
        print()

        # add to films guessed
        self.guesses.append(film_id)

        # get similarity
        similarity = self.ranked_similarities.set_index('film_id').to_dict('index')[film_id]

        # get overlap
        overlap = self.get_overlap_and_update_known_info(film_id)

        # show similarity and overlap to user
        print('similarity', similarity)
        print()
        print('overlap')
        pp.pprint(overlap)
        print()

        # show totals
        print('films guessed')
        print(self.ranked_similarities[self.ranked_similarities['film_id'].isin(self.guesses)])
        print()
        print('known info')
        pp.pprint(self.known_info)
        print()
    
    def get_overlap_and_update_known_info(self, film_id):
        overlap = {norm_type: {} for norm_type in self.answer_info.keys()}
        guess = Film(film_id)
        for feature_name, answer_value in self.answer_info.items():
            if guess_value := guess.film_info.get(feature_name):
                if isinstance(answer_value, list):
                    overlap[feature_name] = [id_to_str(feature_name, x) for x in answer_value if x in guess_value]
                    self.known_info[feature_name] = [id_to_str(feature_name, x) for x in answer_value if x in (self.known_info[feature_name] + guess_value)]
                else:
                    overlap[feature_name] = answer_value - answer_value
                    min_x, max_x = self.known_info[feature_name]
                    if guess_value < answer_value and (min_x is None or guess_value > min_x):
                        self.known_info[feature_name] = (guess_value, max_x)
                    elif guess_value > answer_value and (max_x is None or guess_value < max_x):
                        self.known_info[feature_name] = (min_x, guess_value)
        return overlap