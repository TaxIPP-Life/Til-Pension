# -*- coding: utf-8 -*-
'''
Created on 1 juin 2014

@author: alexis
'''

from pandas import Series, DataFrame
from numpy import zeros, array, ones, concatenate
import logging as log

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
    info.sort('id_parent')
#     info['idx'] = info.groupby('id_parent').cumcount()
#     info =  info.pivot(index='id_parent',columns='idx')[['naiss_liam']].fillna(-1)
#     nb_enf_max = info.shape[1]
#     info.columns = ['yearnaiss' + str(i) for i in range(nb_enf_max)]
#     
#     nb_enf =  info[info != -1 ].count(1)
#     idx_rows = [val*ones(nb) for val, nb in zip(info['id_parent'],nb_enf)]
#     id_row = concatenate(idx_rows)
#     idx_col = []
    list_ident = data.info_ind.index
    id_par = info['id_parent']
    id_ix = [list(list_ident).index(ident) for ident in id_par]
    
    list_dates = data.workstate.dates
    datenaiss = info['naiss_liam']
    naiss_ix = [list(list_dates).index(date) for date in datenaiss]
    enf_by_year = zeros(data.workstate.array.shape)
    enf_by_year[(id_ix, naiss_ix)] = 1
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

    def _print_info_perso(list_timearray, ident, label_func):
        getattr(log,loglevel)( "Les informations longitudinales de l'individu {} dans le calcul de {} sont : ".format(ident, label_func))
        to_print = zeros((len(list_timearray), max_nb_dates))
        names = []
        i = 0
        for timearray in list_timearray:
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
        getattr(log,loglevel)(frame_to_print.to_string())
    
    for ident in list_ident:
        _print_info_perso(list_timearrays, ident, label_func)
    
    
def print_info_vectors(dic_vectors, all_ident, label_func, loglevel="info", list_ident=None):
    ''' Cette fonction permet d'imprimer (sous format DataFrame) les paramètres individuels 
    contenus dans différents vecteurs (pour l'ensemble des individus de la base)'''
    if not list_ident:
        list_ident=all_ident
    
    def _print_info_perso(dic_vectors, ident, label_func):
        getattr(log,loglevel)("Les informations personnelles de l'individu {} dans le calcul de {} sont : ".format(ident, label_func))

        for name, vec in dic_vectors.iteritems():
            id_ix = list(list_ident).index(ident)
            val = vec[id_ix] 
            getattr(log,loglevel)( '  - {} = {}'.format(name, val))

    for ident in list_ident:
        _print_info_perso(dic_vectors, ident, label_func)
        
def print_info(dic_vectors, list_timearrays, all_ident, label, loglevel="info",list_ident=None):
    print_info_vectors(dic_vectors, all_ident, label)
    print_info_timearrays(list_timearrays, all_ident, label)
    
if __name__ == '__main__':  
    a = [1,2,1,3]
    b = [100,1,100,1]
    test = list()
    from numpy import ones, concatenate
    test +=[val*ones(nb) for val, nb in zip(b,a)]
    concatenate(test)
    print test, concatenate(test)