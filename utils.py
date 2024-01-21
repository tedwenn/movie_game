import os
from datetime import datetime
import pickle
    
def pickle_init(init):
    def wrapper(self, *args, **kwargs):
        str_args = (str(arg) for arg in args)
        directory = os.path.join('local_storage', 'pickles', self.__class__.__name__, *str_args, **kwargs)
        ptf = os.path.join(directory, f"{datetime.now().strftime('%Y-%m-%d')}.pkl")
        if os.path.exists(ptf):
            with open(ptf, 'rb') as file:
                temp_obj = pickle.load(file)
                self.__dict__.update(temp_obj.__dict__)
        else:
            init(self, *args, **kwargs)
            if not os.path.exists(directory):
                os.makedirs(directory)
            with open(ptf, 'wb') as file:
                pickle.dump(self, file)
    return wrapper