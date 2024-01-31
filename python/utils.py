import os
import pickle
import time

pickle_directory = 'local_storage/pickles'
pickle_duration_days = 7
    
def pickle_init(init):
    def wrapper(self, *args, **kwargs):
        str_args = (str(arg) for arg in args)
        class_name = self.__class__.__name__
        directory = os.path.join('local_storage', 'pickles', class_name, *str_args, **kwargs)
        ptf = os.path.join(directory, f'{class_name}.pkl')
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

for root, dirs, files in os.walk(pickle_directory, topdown=False):
    for file in files:
        ptf = os.path.join(root, file)
        if (time.time() - os.path.getmtime(ptf)) / 60 / 60 / 24 > pickle_duration_days:
            print('clearing', ptf)
            os.remove(ptf)

    # Remove empty directories
    for name in dirs:
        directory = os.path.join(root, name)
        if not os.listdir(directory):
            print('clearing', directory)
            os.rmdir(directory)