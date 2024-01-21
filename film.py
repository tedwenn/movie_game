from datetime import datetime
import numpy as np
import tmdbpy
import pandas as pd

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

class Film():

    def __init__(self, film_id):
        self.film_id = film_id
        self.film_info = self._film_info(tmdbpy.TMDB().film(self.film_id))
        
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
        film_info['actor'] = [cast_member['id'] for cast_member in film_response['credits']['cast']]
        film_info['keyword'] = [keyword['id'] for keyword in film_response['keywords']['keywords']]

        # binary features: crew
        crew = film_response['credits']['crew']
        for crew_role in crew_roles: # crew_roles defined at top of file
            department, job = crew_role
            job_crew = [cm['id'] for cm in crew if cm['department'] == department and cm['job'] == job]
            if len(job_crew) > 0:
                film_info[crew_role] = job_crew

        # adding in title, which is necessary for display, but won't be part of the vector
        film_info['title'] = film_response['title']

        return film_info

    @property
    def vec(self):

        vec = {}

        # loop through features and put them into vec
        for feature_name, value in self.film_info.items():
            if feature_schema := film_info_schema.get(feature_name):
                norm_type = feature_schema['norm_type']
                if norm_type == 'binary':
                    for item in value:
                        vec[(feature_name, item)] = 1
                else:
                    if norm_type == 'log':
                        value = np.log(value) if value >= 1 else -1
                    vec[feature_name] = value

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
    
    @property
    def film_info_df(self):
        df = pd.DataFrame.from_dict(self.film_info, orient='index', columns=['value'])
        film_info_schema_df = pd.DataFrame.from_dict(film_info_schema, orient='index')
        return df.merge(film_info_schema_df, left_index=True, right_index=True)

    def __getattr__(self, attr):
        return self.film_info[attr]
