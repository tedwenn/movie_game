from download_data import get_film_response
from datetime import datetime
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import pickle
import os
from scipy.sparse import csr_matrix
import pandas as pd

log_features = ['budget', 'revenue', 'vote_count']
continuous_features = ['release_date', 'runtime']
role_ids = {
    'Directing|Director',
    'Directing|Co-Director',
    'Production|Producer',
    'Production|Co-Producer',
    'Writing|Screenplay',
    'Writing|Writer',
    'Writing|Story',
    'Camera|Director of Photography',
    'Sound|Original Music Composer',
    'Sound|Music',
    'Editing|Editor'
}

# factory function that looks like a class elsewhere
def Film(film_id):

    ptf = os.path.join('Film', f'{film_id}.pkl')
    if os.path.exists(ptf):
        with open(ptf, 'rb') as file:
            return pickle.load(file)
    film = FilmObject(film_id)
    with open(ptf, 'wb') as file:
        pickle.dump(film, file)
    return film

class FilmObject():

    def __init__(self, film_id):
        self.ptf = os.path.join('film', f'{film_id}.pkl')
        self.film_id = film_id
        film_response = get_film_response(self.film_id)
        self.film_info = self._film_info(film_response)
        self.vec = self._vec()
        
    def _film_info(self, film_response):

        film_info = {}
        if film_response['belongs_to_collection']:
            film_info['collection'] = film_response['belongs_to_collection']['id']
        film_info['budget'] = film_response['budget']
        film_info['genres'] = [genre['id'] for genre in film_response['genres']]
        film_info['language'] = film_response['original_language']
        film_info['production_companies'] = [company['id'] for company in film_response['production_companies']]
        film_info['production_countries'] = [country['iso_3166_1'] for country in film_response['production_countries']]
        film_info['release_date'] = datetime.strptime(film_response['release_date'], "%Y-%m-%d")
        film_info['revenue'] = film_response['revenue']
        film_info['runtime'] = film_response['runtime']
        film_info['spoken_languages'] = [language['iso_639_1'] for language in film_response['spoken_languages']]
        film_info['title'] = film_response['title']
        film_info['vote_count'] = film_response['vote_count']

        film_info['characters'] = []
        film_info['actors'] = []
        for character in film_response['credits']['cast']:
            film_info['characters'].append(character['character'])
            film_info['actors'].append(character['id'])

        crew = {}
        for crew_member in film_response['credits']['crew']:
            department = crew_member['department']
            job = crew_member['job']
            role_id = f'{department}|{job}'
            if role_id not in crew:
                crew[role_id] = []
            crew[role_id].append(crew_member['id'])
            
        film_info['crew'] = crew

        film_info['keywords'] = [keyword['id'] for keyword in film_response['keywords']['keywords']]

        return film_info

    def _vec(self):
        vec = {}
        for k, v in self.film_info.items():
            if isinstance(v, int):
                if v in continuous_features:
                    vec[k] = v
                else:
                    vec[f'{k}|{v}'] = 1
            elif isinstance(v, str):
                if k != 'title':
                    vec[f'{k}|{v}'] = 1
            elif isinstance(v, datetime):
                vec[k] = (v - datetime(1970, 1, 1)).days
            elif isinstance(v, list):
                if k != 'characters':
                    if k in ('keywords', 'actors'):
                        for x in v:
                            vec[f'{k}|{x}'] = 1
                        for n in range(1, 3):
                            for x in v[:n]:
                                vec[f'{k}|top{n}|{x}'] = 1
                    else:
                        for x in v[:5]:
                            vec[f'{k}|{x}'] = 1
            elif k == 'crew':
                for role_id, crew_members in v.items():
                    if role_id in role_ids:
                        for crew_member_id in crew_members:
                            vec[f'{k}|{role_id}|{crew_member_id}'] = 1
            else:
                raise Exception(f'Unhandled data type for({k}, {type(v)})')
        return vec
    
def SimilarityMatrix():

    date_str = datetime.now().strftime('%Y-%m-%d')
    ptf = os.path.join('SimilarityMatrix', f'{date_str}.pkl')
    if not os.path.exists(ptf):
        films = SimilarityMatrixObject()
        with open(ptf, 'wb') as file:
            pickle.dump(films, file)
        return films
    with open(ptf, 'rb') as file:
        return pickle.load(file)

class SimilarityMatrixObject():

    def __init__(self):

        '''
        get all non-normalized vectors from set of films
        also filter to a few specs
        '''
        vecs_non_norm = {}
        for filename in os.listdir('api_responses'):
            film_id = int(filename.split('.')[0])
            film = Film(film_id)
            if film.film_info['vote_count'] >= 50 and film.film_info['runtime'] >= 60:
                vecs_non_norm[film.film_id] = film.vec

        # create film index for lookups later
        self.film_index = {film_id: idx for idx, film_id in enumerate(vecs_non_norm.keys())}

        # create feature index for CSR calculations
        unique_feature_names = set(feature_name for vec_non_norm in vecs_non_norm.values() for feature_name in vec_non_norm.keys())
        feature_name_to_int = {feature_name: i for i, feature_name in enumerate(unique_feature_names)}
        
        # in order to normalize, we need to know the min/max of each feature
        feature_normalization_factors = self._feature_normalization_factors(vecs_non_norm)

        # apply normalization factors to get normalized vecs
        vecs = {}
        for film_id, vec_non_norm in vecs_non_norm.items():
            vecs[film_id] = self._normalize_vec(vec_non_norm, feature_normalization_factors)

        # Create a CSR matrix
        csr_matrix = self._csr_matrix(vecs, feature_name_to_int)

        # Compute cosine similarities
        self.similarity_matrix = self._similarity_matrix(csr_matrix)
    
    def _feature_normalization_factors(self, vecs_non_norm):
        fnf = {} # feature_normalization_factors
        i = 0
        for vec_non_norm in vecs_non_norm.values():
            for feature, x in vec_non_norm.items():
                if feature in log_features:
                    norm_type = 'log'
                    if x > 0:
                        x = np.log(x)
                    else:
                        x = -1
                elif feature in continuous_features:
                    norm_type = 'continuous'
                else:
                    norm_type = None
                if feature not in fnf:
                    fnf[feature] = {'idx': i, 'norm_type': norm_type, 'min': x, 'max': x}
                    i += 1
                if x < fnf[feature]['min']:
                    fnf[feature]['min'] = x
                if x > fnf[feature]['max']:
                    fnf[feature]['max'] = x
        return fnf

    def _normalize_vec(self, vec_non_norm, feature_normalization_factors):
        vec = {}
        for feature, x in vec_non_norm.items():
            nf = feature_normalization_factors[feature]
            norm_type = nf['norm_type']
            if norm_type:
                min_x, max_x = [nf[s] for s in ('min', 'max')]
                if norm_type == 'log':
                    if x > 0:
                        x = np.log(x)
                    else:
                        x = -1
                x = (x - min_x) / (max_x - min_x)
            vec[feature] = x
        return vec

    def _csr_matrix(self, vecs, feature_name_to_int):
        """Convert dictionary of sparse vectors into a CSR matrix."""
        data = []
        indices = []
        indptr = [0]

        for vec in vecs.values():
            for feature_name, value in vec.items():
                data.append(value)
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
        """Retrieve similarity from the precomputed matrix."""
        return self.similarity_matrix[self.film_index[film_id_1], self.film_index[film_id_2]]
    
    def get_ranked_similarities(self, film_id):

        # pull similarities to input film
        similarities = [(f2, self.get_similarity(film_id, f2)) for f2 in self.film_index.keys()]

        # Convert to a DataFrame
        df = pd.DataFrame(similarities, columns=['film_id', 'similarity_score'])

        # Sort the DataFrame by similarity score in descending order
        df.sort_values(by='similarity_score', ascending=False, inplace=True)

        # Use the rank method to assign ranks, with the same rank for tie scores
        df['rank'] = df['similarity_score'].rank(method='min', ascending=False).astype(int)

        # return df with columns ordered
        return df[['film_id', 'rank', 'similarity_score']]

    #     # create a dataframe, which is much lighter for pickling than a pandas df
    #     result_dict = df.set_index('film_id').to_dict('index')

    #     return result_dict
