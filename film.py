from download_data import get_film_response
from datetime import datetime
import numpy as np
from scipy.sparse import coo_matrix
from sklearn.metrics.pairwise import cosine_similarity

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

class Film():

    def __init__(self, film_id):
        self.film_id = film_id
        self.film_response = get_film_response(self.film_id)
        self._film_info = None
        self._vec = None
        
    @property
    def film_info(self):

        if self._film_info:
            return self._film_info

        film_info = {}
        if self.film_response['belongs_to_collection']:
            film_info['collection'] = self.film_response['belongs_to_collection']['id']
        film_info['budget'] = self.film_response['budget']
        film_info['genres'] = [genre['id'] for genre in self.film_response['genres']]
        film_info['language'] = self.film_response['original_language']
        film_info['production_companies'] = [company['id'] for company in self.film_response['production_companies']]
        film_info['production_countries'] = [country['iso_3166_1'] for country in self.film_response['production_countries']]
        film_info['release_date'] = datetime.strptime(self.film_response['release_date'], "%Y-%m-%d")
        film_info['revenue'] = self.film_response['revenue']
        film_info['runtime'] = self.film_response['runtime']
        film_info['spoken_languages'] = [language['iso_639_1'] for language in self.film_response['spoken_languages']]
        film_info['title'] = self.film_response['title']
        film_info['vote_count'] = self.film_response['vote_count']

        film_info['characters'] = []
        film_info['actors'] = []
        for character in self.film_response['credits']['cast']:
            film_info['characters'].append(character['character'])
            film_info['actors'].append(character['id'])

        crew = {}
        for crew_member in self.film_response['credits']['crew']:
            department = crew_member['department']
            job = crew_member['job']
            role_id = f'{department}|{job}'
            if role_id not in crew:
                crew[role_id] = []
            crew[role_id].append(crew_member['id'])
            
        film_info['crew'] = crew

        film_info['keywords'] = [keyword['id'] for keyword in self.film_response['keywords']['keywords']]

        self._film_info = film_info

        return self._film_info

    @property
    def vec(self):
        if self._vec:
            return self._vec
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
                    if k == 'keywords':
                        for x in v:
                            vec[f'{k}|{x}'] = 1
                    else:
                        for x in v[:5]:
                            vec[f'{k}|{x}'] = 1
                    if k == 'actors':
                        for n in range(1, 3):
                            for x in v[:n]:
                                vec[f'{k}|top{n}|{x}'] = 1
            elif k == 'crew':
                for role_id, crew_members in v.items():
                    if role_id in role_ids:
                        for crew_member_id in crew_members:
                            vec[f'{k}|{role_id}|{crew_member_id}'] = 1
            else:
                raise Exception(f'Unhandled data type for({k}, {type(v)})')
        self._vec = vec
        return self._vec

class FilmSet():

    def __init__(self, film_ids):
        self.film_ids = film_ids
        self.films = [Film(film_id) for film_id in self.film_ids]
        self._vecs = None
        self._feature_mapping = None

    @property
    def vecs(self):
        if self._vecs:
            return self._vecs
        self._vecs = {film.film_id: film.vec for film in self.films}
        return self._vecs
    
    @property
    def feature_mapping(self):
        if self._feature_mapping:
            return self._feature_mapping
        feature_mapping = {}
        i = 0
        for vec in self.vecs.values():
            for feature, x in vec.items():
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
                if feature not in feature_mapping:
                    feature_mapping[feature] = {'idx': i, 'norm_type': norm_type, 'min': x, 'max': x}
                    i += 1
                if x < feature_mapping[feature]['min']:
                    feature_mapping[feature]['min'] = x
                if x > feature_mapping[feature]['max']:
                    feature_mapping[feature]['max'] = x
        self._feature_mapping = feature_mapping
        return self._feature_mapping
    
    def get_sparse_vec_norm(self, film_id):
        indices = []
        values = []
        for feature, x in self.vecs[film_id].items():
            fm = self.feature_mapping[feature]
            indices.append(fm['idx'])
            norm_type = fm['norm_type']
            if norm_type:
                min_x, max_x = [fm[s] for s in ('min', 'max')]
                if norm_type == 'log':
                    if x > 0:
                        x = np.log(x)
                    else:
                        x = -1
                x = (x - min_x) / (max_x - min_x)
            values.append(x)
        return coo_matrix((values, (indices, [0]*len(indices))), shape=(len(self.feature_mapping), 1))
    
    def get_similarity(self, f1, f2):
        v1, v2 = [self.get_sparse_vec_norm(f).transpose() for f in (f1, f2)]
        return cosine_similarity(v1, v2)[0][0]

    def get_similar_films(self, film_id):
        similar_films = []
        for f2 in self.film_ids:
            similarity = self.get_similarity(film_id, f2)
            similar_films.append((similarity, (f2, Film(f2).film_info['title'])))
        return sorted(similar_films, reverse=True)