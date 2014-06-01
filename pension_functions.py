# -*- coding: utf-8 -*-
#import bottleneck as bn
import pdb

from time_array import TimeArray
from utils_pension import sum_by_years
from numpy import minimum, array, greater, divide, zeros, in1d, sort, where, \
                     multiply, apply_along_axis, isnan
from pandas import Series

code_chomage=2
avpf = 8
id_test = 21310 # 28332 #1882 #1851 #, 18255       

def nb_trim_surcote(trim_by_year, date_start_surcote):
    ''' Cette fonction renvoie le vecteur numpy du nombre de trimestres surcotés à partir de :
    - la table du nombre de trimestre comptablisé au sein du régime par année : trim_by_year.array
    - le vecteur des dates (format yyyymm) à partir desquelles les individus surcote (détermination sur cotisations tout régime confondu)
    '''
    yearmax = max(trim_by_year.dates)
    yearmin = min(date_start_surcote) 
    # Possible dates for surcote :
    dates_surcote = [date for date in trim_by_year.dates
                      if date >= yearmin]
    output = zeros(len(date_start_surcote))
    for date in dates_surcote:
        to_keep = where(greater(date, date_start_surcote))[0]
        ix_date = trim_by_year.dates.index(yearmax)
        if to_keep.any():
            output[to_keep] += trim_by_year.array[to_keep, ix_date]
    return output

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
