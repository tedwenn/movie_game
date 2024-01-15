from film import SimilarityMatrix, Film
import pandas as pd

class Game():

    def __init__(self, answer):
        self.answer = Film(answer)
        self.ranked_similarities = SimilarityMatrix().get_ranked_similarities(self.answer.film_id).set_index('film_id').to_dict('index')
        # print(self.ranked_similarities)
        # print(self.ranked_similarities.head(5))
        # df = pd.DataFrame.from_dict(self.ranked_similarities, orient='index').reset_index()

    def guess(self, film_id):

        # get similarity
        similarity = self.ranked_similarities[film_id]

        # get overlap
        overlap = self.get_overlap(film_id)

        # show similarity and overlap to user
        print(similarity)
        print(overlap)

        # add these to the similarity and overlap totals
        # show totals

    def get_overlap(self, film_id):
        film = Film(film_id)
        for k, v in self.answer.film_info.items():
            print(k, v)
        return f'overlap with {film_id}'
    
    # def get_overlap(self, v2):
    #     def get_binary_labels(v):
    #         return [label for label, x in v.items() if x == 1]
    #     l1, l2 = [get_binary_labels(v) for v in (self.v_answer, v2)]
    #     return list(set(l1).intersection(set(l2)))