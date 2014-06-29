# -*- coding: utf-8 -*-
import sys
from pandas import DataFrame, Series
from numpy import ndarray
from time_array import TimeArray
from load_pensipp import load_pensipp_data
from CONFIG_compare import pensipp_comparison_path

def _to_print(key, val, selection, cache, intermediate=False):
    add_print = 'qui'
    if key in cache:
        return cache
    else:
        print selection
        if intermediate:
            add_print = "est également appelé(e)/calculé(e) au cours du calcul et"
        if isinstance(val, dict):
            for child_key, child_val in val.iteritems():
                _to_print(child_key, child_val, selection, cache)
        elif isinstance(val, DataFrame):
            print "    - La table pandas {} {} vaut: \n{}".format(key, add_print, val.iloc[selection,:].to_string())
            cache.append(key)
        elif isinstance(val, TimeArray):
#             val_print = DataFrame(val.array, index=selection, columns=val.dates).to_string()
            print "    - Le TimeArray {} {} vaut: \n{}".format(key, add_print, val.array[selection,:])
            cache.append(key)
        elif isinstance(val, ndarray):
            #It has to be a vetor, numpy matrix should be timearrays
#             val_print = Series(val, index=selection).to_string()
            print "    - Le vecteur {} {} vaut: \n {}".format(key, add_print, val[selection])
        elif isinstance(val, Series):
            print "    - Le vecteur {} {} vaut: \n {}".format(key, add_print, val[selection].to_string())
        else:
            if key != 'self':
                print "    - L'objet {}".format(key)
            #cache.append(key) : probleme 
        return cache      

class PrintDecorator(object):
    def __init__(self, print_level, selection, index=None):
        ''' 
        - print_level : TODO
        doit mémoriser 
        on a besoin du len_data pour les valeurs par défaut
        - selection est pour la liste de lignes à afficher
        - si index est rempli alors la selection s'exprime en indice
        '''
           
        self._locals = {}
        self.print_level = print_level
        self.selection = selection
        
        if index is not None:
            assert isinstance(index, list)
            sel = []
            for idx in selection:
                sel += [index.index(idx)] 
            self.selection = sel

        self.index = index
        self.cache = []

    def __call__(self, func):
        fname = func.__name__

        def call_func(*args):
            def tracer(frame, event, arg):
                if event=='return':
                    self._locals = frame.f_locals.copy()
                    
            sys.setprofile(tracer)
            try:
                # trace the function call
                res = func(*args)
            finally:
                # disable tracer and replace with old one
                sys.setprofile(None)
            for key, val in self._locals.iteritems():
                self.cache = _to_print(key, val, self.selection, self.cache, intermediate=True)
            return res
        
        def wrapper(*args, **kwargs):
            if fname in self.print_level.keys() and self.print_level[fname]:
                print "Pour la fonction {}, les arguments appelés sont : ".format(fname)
                arg_name = ''
                args_names = []

                for arg in args:
                    if hasattr(arg, 'name'): 
                        arg_name = arg.name
                        args_names.append(arg_name)
                    if hasattr(arg, '__name__'): 
                        arg_name = arg.__name__
                        args_names.append(arg_name)
                    self.cache = _to_print(arg_name, arg, self.selection, self.cache,)
                return call_func(*args,**kwargs)
            else:
                return func(*args, **kwargs)        
        return wrapper

if __name__ == '__main__':
        
    print_level = {'is_sum_lt_prod': True}
    test = PrintDecorator(print_level)
    print_level = {'calculate_coeff_proratisation': True}
    intermediate_print = PrintDecorator(print_level)
    @test
    def is_sum_lt_prod(a,b,c):
        sum = a+b+c
        prod = a*b*c
        return prod/sum
    
    print_level = {'is_sum_lt_prod': True}
    
    test = is_sum_lt_prod(13,7,4)
    print test