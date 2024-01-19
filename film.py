from download_data import get_film_response
from datetime import datetime
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import pickle
import os
from scipy.sparse import csr_matrix
import pandas as pd
import person

crew_roles = [
    ('Directing', 'Director'),
    ('Directing', 'Co-Director'),
    ('Production', 'Producer'),
    ('Production', 'Co-Producer'),
    ('Writing', 'Screenplay'),
    ('Writing', 'Writer'),
    ('Writing', 'Story'),
    ('Camera', 'Director of Photography'),
    ('Sound', 'Original Music Composer'),
    ('Sound', 'Music'),
    ('Editing', 'Editor')
]

film_info_schema = [
    ('budget', 'log', None),
    ('revenue', 'log', None),
    ('vote_count', 'log', None),
    ('release_date', 'linear', None),
    ('runtime', 'linear', None),
    ('vote_average', 'linear', None),
    ('collection', 'binary', 'collection'),
    ('genre', 'binary', 'genre'),
    ('language', 'binary', None),
    ('production_company', 'binary', 'company'),
    ('production_country', 'binary', None),
    ('spoken_language', 'binary', None),
    ('actor', 'binary', 'person'),
    ('keyword', 'binary', 'keyword')
]
film_info_schema.extend([(crew_role, 'binary', 'person') for crew_role in crew_roles])
film_info_schema = {feature_name: {'norm_type': norm_type, 'id_type': id_type} for feature_name, norm_type, id_type in film_info_schema}

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
        self.film_id = film_id
        film_response = get_film_response(self.film_id)
        self.film_info = self._film_info(film_response)
        
    def _film_info(self, film_response):
        
        film_info = {}

        # log_features: 'budget', 'revenue', 'vote_count'
        film_info['budget'] = film_response['budget']
        film_info['revenue'] = film_response['revenue']
        film_info['vote_count'] = film_response['vote_count']

        # continuous_features: 'release_date', 'runtime'
        film_info['release_date'] = (datetime.strptime(film_response['release_date'], "%Y-%m-%d") - datetime(1970, 1, 1)).days
        film_info['runtime'] = film_response['runtime']
        film_info['vote_average'] = film_response['vote_average']

        # binary features
        if film_response['belongs_to_collection']:
            film_info['collection'] = [film_response['belongs_to_collection']['id']]
        film_info['genre'] = [genre['id'] for genre in film_response['genres']]
        film_info['language'] = [film_response['original_language']]
        film_info['production_company'] = [company['id'] for company in film_response['production_companies']]
        film_info['production_country'] = [country['iso_3166_1'] for country in film_response['production_countries']]
        film_info['spoken_language'] = [language['iso_639_1'] for language in film_response['spoken_languages']]
        # binary_info['title'] = film_response['title']
        film_info['actor'] = [cast_member['id'] for cast_member in film_response['credits']['cast']]
        film_info['keyword'] = [keyword['id'] for keyword in film_response['keywords']['keywords']]

        # binary features: crew
        crew = film_response['credits']['crew']
        for crew_role in crew_roles: # crew_roles defined at top of file
            department, job = crew_role
            job_crew = [cm['id'] for cm in crew if cm['department'] == department and cm['job'] == job]
            if len(job_crew) > 0:
                film_info[crew_role] = job_crew

        return film_info

    @property
    def vec(self):

        # log + linear
        # can just pull these straight in, since they're never lists, and they're already in key/value pairs
        vec = {feature_name: value for feature_name, value in self.film_info.items() if film_info_schema[feature_name]['norm_type'] in ('log', 'linear')}

        # binary
        for feature_name, values in self.film_info.items():
            if film_info_schema[feature_name]['norm_type'] == 'binary':
                for item in values:
                    vec[(feature_name, item)] = 1

        # extra weight binary items
        if collection_ids := self.film_info.get('collection'):
            for collection_id in collection_ids:
                vec[('collection_extra_weight', collection_id)] = 1
        n_top_actors = 5
        for n, actor_id in enumerate(self.film_info['actor'][:n_top_actors]):
            for counter in range(n_top_actors, n, -1):
                vec[(f'actor_top_{counter}', actor_id)] = 1
        
        # return vec
        return vec
    
def id_to_str(feature_name, id):
    print('getting', feature_name, id)
    id_type = film_info_schema[feature_name]['id_type']
    print(id_type)
    if id_type == 'person':
        print(person.get_name(id))
        return person.get_name(id)
    
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
        
        # in order to normalize, we need to know the min/max of each feature
        feature_normalization_factors = self._feature_normalization_factors(vecs_non_norm)

        # apply normalization factors to get normalized vecs
        vecs = {}
        for film_id, vec_non_norm in vecs_non_norm.items():
            vecs[film_id] = self._normalize_vec(vec_non_norm, feature_normalization_factors)

        # create feature index for CSR calculations
        unique_feature_names = set(feature_name for vec_non_norm in vecs_non_norm.values() for feature_name in vec_non_norm)
        feature_name_to_int = {feature_name: i for i, feature_name in enumerate(unique_feature_names)}

        # Create a CSR matrix
        csr_matrix = self._csr_matrix(vecs, feature_name_to_int)

        # Compute cosine similarities
        self.similarity_matrix = self._similarity_matrix(csr_matrix)
    
    def _feature_normalization_factors(self, vecs_non_norm):
        fnf = {} # feature_normalization_factors
        for vec_non_norm in vecs_non_norm.values():
            for feature_name, weight in vec_non_norm.items():
                if feature_schema := film_info_schema.get(feature_name):
                    norm_type = feature_schema['norm_type']
                    if norm_type in ('log', 'linear'):
                        if norm_type == 'log':
                            weight = np.log(weight) if weight >= 1 else -1
                        if feature_name not in fnf:
                            fnf[feature_name] = {'min': weight, 'max': weight}
                        if weight < fnf[feature_name]['min']:
                            fnf[feature_name]['min'] = weight
                        if weight > fnf[feature_name]['max']:
                            fnf[feature_name]['max'] = weight
        return fnf

    def _normalize_vec(self, vec_non_norm, feature_normalization_factors):
        vec = {}
        for feature_name, weight in vec_non_norm.items():
            if feature_normalization := feature_normalization_factors.get(feature_name):
                if film_info_schema[feature_name]['norm_type'] == 'log':
                    weight = np.log(weight) if weight >= 1 else -1
                min_weight, max_weight = [feature_normalization[s] for s in ('min', 'max')]
                weight = (weight - min_weight) / (max_weight - min_weight)
            vec[feature_name] = weight
        return vec

    def _csr_matrix(self, vecs, feature_name_to_int):
        """Convert dictionary of sparse vectors into a CSR matrix."""
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