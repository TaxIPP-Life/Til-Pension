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

def unemployment_trimesters(timearray, code_regime=None):
    ''' Input : monthly or yearly-table (lines: indiv, col: dates 'yyyymm') 
    Output : vector with number of trimesters for unemployment'''
    table = timearray.copy()
    if not code_regime:
        print "Indiquer le code identifiant du régime"

    table = table.isin(code_regime + [code_chomage]) 
    unemp_trim = table.select_unemployment(code_regime, code_chomage)
    if timearray.frequency == 'month':
        month_by_year_unemp = unemp_trim.translate_frequency('year', method='sum')
        trim_unemp = TimeArray(divide(month_by_year_unemp, 3), timearray.dates)
        return trim_unemp   
    else:
        assert timearray.frequency == 'year'
        return TimeArray(multiply(unemp_trim, 4), timearray.dates)
    

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

def count_enf_pac(info_child, index):
    info_child['enf_pac'] = ( info_child['age_enf'] <= 18)*( info_child['age_enf'] >= 0 )*info_child['nb_enf']
    info = info_child.groupby(['id_parent'])['enf_pac'].sum().reset_index()
    info.columns = ['id_parent', 'nb_pac']
    info.index = info['id_parent']
    nb_pac= Series(zeros(len(index)), index=index)
    nb_pac += info['nb_pac']
    return nb_pac.fillna(0)

def count_enf_born(info_child, index):
    info_child['enf_born'] =  ( info_child['age_enf'] >= 0 )*info_child['nb_enf']
    info = info_child.groupby(['id_parent'])['enf_born'].sum().reset_index()
    info.columns = ['id_parent', 'nb_born']
    info.index = info['id_parent']
    nb_born= Series(zeros(len(index)), index=index)
    nb_born += info['nb_born']
    return nb_born.fillna(0)

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
