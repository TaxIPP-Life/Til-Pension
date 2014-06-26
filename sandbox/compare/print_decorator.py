# -*- coding: utf-8 -*-
import sys
from pandas import DataFrame, Series
from numpy import ndarray
from time_array import TimeArray
from load_pensipp import load_pensipp_data
from CONFIG_compare import pensipp_comparison_path

def _to_print(key, val, index, cache, intermediate=False):
    add_print = 'qui'
    if key in cache:
        return cache
    else:
        if intermediate:
            add_print = "est également appelé(e)/calculé(e) au cours du calcul et"
        if isinstance(val, dict):
            for child_key, child_val in val.iteritems():
                _to_print(child_key, child_val, index, cache)
        elif isinstance(val, DataFrame):
            print "    - La table pandas {} {} vaut: \n{}".format(key, add_print, val.to_string())
            cache.append(key)
        elif isinstance(val,TimeArray):
            val_print = DataFrame(val.array, index=index, columns=val.dates).to_string()
            print "    - Le TimeArray {} {} vaut: \n{}".format(key, add_print, val_print)
            cache.append(key)
        elif isinstance(val, ndarray):
            #It has to be a vetor, numpy matrix should be timearrays
            val_print = Series(val, index=index).to_string()
            print "    - Le vecteur {} {} vaut: \n {}".format(key, add_print, val_print)
        elif isinstance(val,Series):
            print "    - Le vecteur {} {} vaut: \n {}".format(key, add_print, val.to_string())
        else:
            if key != 'self':
                print "    - L'objet {}".format(key)
            #cache.append(key) : probleme 
        return cache

def prep_to_print(yearsim, print_level, selection_id=None, first_year_sal=1949):
    data_to_print = load_pensipp_data(pensipp_comparison_path,
                                     yearsim, 
                                     first_year_sal=first_year_sal, 
                                     selection_id = selection_id)
    intermediate_print = print_decorator(print_level, index=data_to_print.info_ind.index)
    return data_to_print, intermediate_print
      

class print_decorator(object):
    def __init__(self, print_level, index):
        self._locals = {}
        self.print_level = print_level
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
                self.cache = _to_print(key, val, self.index, self.cache, intermediate=True)
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
                    self.cache = _to_print(arg_name, arg, self.index, self.cache,)
                return call_func(*args,**kwargs)
            else:
                return func(*args, **kwargs)        
        return wrapper
    
    
yearsim = 2004
selection_id =  [186,7338]
func_to_print = {'calculate_coeff_proratisation': True}
data_to_print, intermediate_print = prep_to_print(yearsim, func_to_print, selection_id=selection_id, first_year_sal=1949)

if __name__ == '__main__':
        
    print_level = {'is_sum_lt_prod': True}
    test = print_decorator(print_level)
    print_level = {'calculate_coeff_proratisation': True}
    intermediate_print = print_decorator(print_level)
    @test
    def is_sum_lt_prod(a,b,c):
        sum = a+b+c
        prod = a*b*c
        return prod/sum
    
    print_level = {'is_sum_lt_prod': True}
    
    test = is_sum_lt_prod(13,7,4)
    print test