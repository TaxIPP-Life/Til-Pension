# -*- coding: utf-8 -*-
'''
Created on 1 juin 2014

@author: alexis
'''
import datetime as dt
from pandas import Series, DataFrame
from numpy import zeros

def calculate_age(birth_date, date):
    ''' calculate age at date thanks birthdate '''
    def _age(birthdate):
        try: 
            birthday = birthdate.replace(year=date.year)
        except ValueError: # raised when birth date is February 29 and the current year is not a leap year
            birthday = birthdate.replace(year=date.year, month=birthdate.month+1, day=1)
        if birthday > date:
            return date.year - birthdate.year - 1
        else:
            return date.year - birthdate.year
    return birth_date.apply(_age)

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

def _info_numpy(np_object, ident, list_ident, text=None):
    id_ix = list(list_ident).index(ident)
    if text:
        print str(text) + " : "
    if len(np_object.shape) == 2:
        #type = '2d-matrix'
        return np_object[id_ix, :]
    else:
        #type = 'vector'
        return np_object[id_ix]

def print_multi_info_numpy(list_timearray, ident, list_ident):
    to_print = {}
    first_shape = list_timearray[0].array.shape
    max_nb_dates = 0
    print "Les informatons personnelles de l'individu {} sont : ".format(ident)
    for timearray in list_timearray:
        array = timearray.array
        assert len(array.shape) == 2
        nb_rows = array.shape[0]
        nb_cols = array.shape[1]
        assert first_shape[0] == nb_rows
        if nb_cols > max_nb_dates:
            max_nb_dates = nb_cols
    
    for timearray in list_timearray:
        array = timearray.array
        nb_dates = array.shape[1]
        col_to_print = _info_numpy(array, ident, list_ident, text=None)
        if nb_dates < max_nb_dates:
            long_col_to_print = zeros(max_nb_dates)
            long_col_to_print[-len(col_to_print):] = col_to_print
            col_to_print = long_col_to_print
        to_print[timearray.name] = col_to_print
    print DataFrame(to_print).to_string()