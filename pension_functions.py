# -*- coding: utf-8 -*-
#import bottleneck as bn
import pdb

from time_array import TimeArray
from utils_pension import sum_by_years
from numpy import minimum, array, greater, divide, zeros, in1d, sort, where, \
                     multiply, apply_along_axis, isnan
from pandas import Series
   

def sum_from_dict(dictionnary, key='', plafond=None):
    ''' Somme les TimeArray contenus dans un dictionnaire et dont le nom contient la 'key' '''
    timearray_with_key = [trim for name, trim in dictionnary.items() if key in name]
    first = timearray_with_key[0]
    trim_tot = TimeArray(zeros(first.array.shape), first.dates)
    for timearray in timearray_with_key:
        trim_tot += timearray
    trim_tot = trim_tot.ceil(plaf=plafond)
    return trim_tot

    
def trim_maj_all(trimestres):
    ''' Détermine la somme des trimestres majorés des différents régimes '''
    trimestres_maj = [trimestres[key] for key in trimestres.keys() if str(key)[0:8] == 'maj']
    trim_maj_tot = sum(trimestres_maj)
    return trim_maj_tot
