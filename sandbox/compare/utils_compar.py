# -*- coding: utf-8 -*-
'''
Created on 1 juin 2014

@author: alexis
'''

from pandas import Series, DataFrame
from numpy import zeros, array, ones, concatenate
import logging as log
from itertools import groupby

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

def count_enf_by_year(data, info_enf):
    ''' Update le info_ind contenue dans Data avec le nombre d'enfant par régime '''
    parents_id = data.info_ind.index
    info = info_enf.loc[info_enf['id_parent'].isin(parents_id),:]
    info['naiss_liam'] = [ datenaiss.year*100 + 1 for datenaiss in info['naiss']]
    info = info.sort('id_parent')

    list_ident = data.info_ind.index
    id_par = info['id_parent']
    id_ix = [list(list_ident).index(ident) for ident in id_par]

    list_dates = data.workstate.dates
    datenaiss = info['naiss_liam']
    naiss_ix = [list(list_dates).index(date) for date in datenaiss]
    list_ix = sorted([(ident, year) for ident, year in zip(id_ix, naiss_ix)])
    
    count_by_ix = [(i, list_ix.count(i)) for i,_ in groupby(list_ix)]
    id_ix = [k[0][0] for k in count_by_ix]
    year_ix = [k[0][1] for k in count_by_ix]
    nb_enf = [k[1] for k in count_by_ix]
    enf_by_year = zeros(data.workstate.array.shape)
    enf_by_year[(id_ix, year_ix)] = array(nb_enf)
    #TODO: check pb with twins
    return enf_by_year

def print_info_timearrays(list_timearrays, all_ident, label_func, loglevel="info", list_ident=None):
    ''' Cette fonction permet d'imprimer (sous format DataFrame) le déroulé individuel
    contenus dans différents timearrays (pour l'ensemble des individus de la base)'''
    first_shape = list_timearrays[0].array.shape
    max_nb_dates = 0
    for timearray in list_timearrays:
        array = timearray.array
        assert len(array.shape) == 2
        nb_rows = array.shape[0]
        nb_cols = array.shape[1]
        assert first_shape[0] == nb_rows
        if nb_cols > max_nb_dates:
            max_nb_dates = nb_cols
            dates_all = timearray.dates
    
    if not list_ident:
        list_ident = all_ident

    for ident in list_ident:
        getattr(log,loglevel)( "Les informations longitudinales de l'individu {} dans le calcul de {} sont : ".format(ident, label_func))
        to_print = zeros((len(list_timearrays), max_nb_dates))
        names = []
        i = 0
        for timearray in list_timearrays:
            array = timearray.array
            nb_dates = array.shape[1]
            id_ix = list(list_ident).index(ident)
            col_to_print = timearray.array[id_ix,:]
            if nb_dates < max_nb_dates:
                long_col_to_print = zeros(max_nb_dates)
                long_col_to_print[-len(col_to_print):] = col_to_print
                col_to_print = long_col_to_print
            to_print[i,:] = col_to_print
            names += [timearray.name] 
            i += 1
        frame_to_print = DataFrame(to_print, columns=dates_all)
        frame_to_print['names'] = names
        frame_to_print.index = frame_to_print['names']
        getattr(log,loglevel)(frame_to_print)

    
def print_info_vectors(dic_vectors, all_ident, label_func, loglevel="info", list_ident=None):
    ''' Cette fonction permet d'imprimer (sous format DataFrame) les paramètres individuels 
    contenus dans différents vecteurs (pour l'ensemble des individus de la base)'''
    if not list_ident:
        list_ident=all_ident
    
    for ident in list_ident:
        getattr(log,loglevel)("Les informations personnelles de l'individu {} dans le calcul de {} sont : ".format(ident, label_func))
        for name, vec in dic_vectors.iteritems():
            id_ix = list(list_ident).index(ident)
            val = vec[id_ix] 
            getattr(log,loglevel)('  - {} = {}'.format(name, val))


        
def print_info(dic_vectors, list_timearrays, all_ident, label, loglevel="info",list_ident=None):
    print_info_vectors(dic_vectors, all_ident, label)
    print_info_timearrays(list_timearrays, all_ident, label)
    
if __name__ == '__main__':  
    
    # Example for count_enf_by_year
    nb_enf = [1,2,1,1]
    id_ix = [0,0,1,2]
    year_ix = [1,2,0,3]
    test = zeros((3,4))
    test[(id_ix, year_ix)] = array(nb_enf)
    print test