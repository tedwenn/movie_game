import numpy as np
from scipy.sparse import csr_matrix
import pandas as pd
import tmdbpy
from film import Film, film_info_schema
from sklearn.preprocessing import MinMaxScaler
from utils import pickle_init

class SimilarityMatrix():

    @pickle_init
    def __init__(self, year_range):

        '''
        get all non-normalized vectors from set of films
        also filter to a few specs
        '''
        vecs_non_norm = {} 
        for film_id in tmdbpy.TMDB().film_list(year_range=year_range, min_vote_count=50):
            vecs_non_norm[film_id] = Film(film_id).vec

        # normalize vectors
        vecs = self._normalize_vecs(vecs_non_norm)

        # create film index for lookups later
        self.film_index = {film_id: idx for idx, film_id in enumerate(vecs_non_norm.keys())}

        # Create a CSR matrix
        csr_matrix = self._csr_matrix(vecs)

        # Compute cosine similarities
        self.similarity_matrix = self._similarity_matrix(csr_matrix)

    def _normalize_vecs(self, vecs_non_norm):

        # create a DataFrame of non-binary features to be normalized
        filtered_vecs_non_norm = {}
        for film_id, vec_non_norm in vecs_non_norm.items():
            filtered_vec_non_norm = {}
            for feature_name, feature_schema in film_info_schema.items():
                if feature_schema['norm_type'] != 'binary':
                    filtered_vec_non_norm[feature_name] = vec_non_norm[feature_name]
            filtered_vecs_non_norm[film_id] = filtered_vec_non_norm
        df = pd.DataFrame(filtered_vecs_non_norm).T  # .T is for transpose

        # Normalize the DataFrame
        scaler = MinMaxScaler()
        df_normalized = pd.DataFrame(scaler.fit_transform(df), columns=df.columns, index=df.index)
        filtered_vecs_norm = df_normalized.to_dict(orient='index')

        # put normalized values back in original vecs
        vecs = {}
        for film_id, vec_non_norm in vecs_non_norm.items():
            vecs[film_id] = vec_non_norm
            for feature_name, weight in filtered_vecs_norm[film_id].items():
                vecs[film_id][feature_name] = weight

        return vecs

    def _csr_matrix(self, vecs):

        """Convert dictionary of sparse vectors into a CSR matrix."""

        unique_feature_names = set(feature_name for vec_non_norm in vecs.values() for feature_name in vec_non_norm)
        feature_name_to_int = {feature_name: i for i, feature_name in enumerate(unique_feature_names)}

        data = []
        indices = []
        indptr = [0]

        for vec in vecs.values():
            for feature_name, weight in vec.items():
                if weight > 0:
                    data.append(weight)
                    indices.append(feature_name_to_int[feature_name])
            indptr.append(len(data))

        return csr_matrix((data, indices, indptr), dtype=float)
    
    def _similarity_matrix(self, csr_mat):
        """Compute cosine similarity matrix from CSR matrix."""
        # Normalize the rows of the matrix
        norm = np.sqrt(csr_mat.power(2).sum(axis=1))
        csr_mat_normalized = csr_mat.multiply(1 / norm)

        # Compute cosine similarity
        similarity_matrix = csr_mat_normalized.dot(csr_mat_normalized.T).toarray()
        return similarity_matrix
    
    def get_similarity(self, film_id_1, film_id_2):
        return self.get_similarity_from_film_idx(self.film_index[film_id_1], self.film_index[film_id_2])
    
    def get_similarity_from_film_idx(self, film_idx_1, film_idx_2):
        """Retrieve similarity from the precomputed matrix."""
        return self.similarity_matrix[film_idx_1, film_idx_2]
    
    def get_ranked_similarities(self, film_id):

        # get df of similarity scores
        film_idx = self.film_index[film_id]
        df = pd.DataFrame.from_dict(self.film_index, orient='index', columns=['film_idx'])
        df['similarity_score'] = df['film_idx'].apply(lambda i: self.get_similarity_from_film_idx(film_idx, i))

        # Sort the DataFrame by similarity score in descending order
        df.sort_values(by='similarity_score', ascending=False, inplace=True)

        # Use the rank method to assign ranks, with the same rank for tie scores
        df['rank'] = df['similarity_score'].rank(method='min', ascending=False).astype(int)

        # return df with columns ordered
        return df[['rank', 'similarity_score']]
