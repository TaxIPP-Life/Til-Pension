# -*- coding: utf-8 -*-

''' crée une fonction qui sert en fait de décorteur : 
        - elle prend comme argument une fonction
        - elle retourne une fonctino
        - la différence entre l'entrée et la sortie c'est que 
    la fonction de sortie affiche ses arguments (pour une liste 
    d'indice donnée)
'''

import sys
from pandas import DataFrame, Series
from numpy import ndarray
from time_array import TimeArray

def _to_print(key, val, selection, cache, intermediate=False):
    add_print = 'qui'
    if key in cache:
        return cache
    else:
        if intermediate:
            add_print = "est également appelé(e)/calculé(e) au cours du calcul et"
        if isinstance(val, dict):
            for child_key, child_val in val.iteritems():
                _to_print(child_key, child_val, selection, cache)
        elif isinstance(val, DataFrame):
            if selection is None:
                selection = range(len(val))
            print "    - La table pandas {} {} vaut: \n{}".format(key, add_print, val.iloc[selection,:].to_string())
            cache.append(key)
        elif isinstance(val, TimeArray):
            print "    - Le TimeArray {} {} vaut: \n{}".format(key, add_print, val.array[selection,:])
            cache.append(key)
        elif isinstance(val, ndarray):
            #It has to be a vetor, numpy matrix should be timearrays
            try:
                print "    - Le vecteur {} {} vaut: \n {}".format(key, add_print, val[selection]) #only for parameter ?
            except:
                pass
        elif isinstance(val, Series):
            if selection is None:
                selection = range(len(val))
            print "    - Le vecteur {} {} vaut: \n {}".format(key, add_print, val.iloc[selection].to_string())
        else:
            if key != 'self':
                print "    - L'objet {}".format(key)
            #cache.append(key) : probleme 
        return cache     


class AddPrint(object):
    def __init__(self, selection):
        ''' 
        - print_level : TODO
        doit mémoriser 
        on a besoin du len_data pour les valeurs par défaut
        - selection est la liste de lignes à afficher
        '''
           
        self._locals = {}
        self.selection = selection

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
        return wrapper