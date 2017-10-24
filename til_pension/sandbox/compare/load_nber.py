# -*- coding: utf-8 -*-

import os
import datetime
import numpy as np
import pandas as pd
from numpy.lib import recfunctions


from til_pension.pension_data import PensionData
from til_pension.sandbox.compare.utils_compar import calculate_age, count_enf_born, count_enf_pac, count_enf_by_year



def _child_by_age(info_child, year, id_selected):
    info_child = info_child.loc[info_child['id_parent'].isin(id_selected),:]
    info_child.loc[:, 'age'] = calculate_age(info_child.loc[:, 'naiss'], datetime.date(year,1,1))
    nb_enf = info_child.groupby(['id_parent', 'age']).size().reset_index()
    nb_enf.columns = ['id_parent', 'age_enf', 'nb_enf']
    return nb_enf


def build_info_child(enf, info):
    '''
    Input tables :
        - 'enf' : pour chaque personne sont donnés les identifiants de ses enfants
        - 'ind' : table des infos perso (dates de naissances notamment)
    Output table :
        - info_child_father : identifiant du pere, ages possibles des enfants, nombre d'enfant ayant cet age
        - info_child_mother : identifiant de la mere, ages possibles des enfants, nombre d'enfant ayant cet age
    '''
    info_enf = enf.stack().reset_index()
    info_enf.columns =  ['id_parent', 'enf', 'id_enf']
    info_enf = info_enf.merge(info[['sexe', 'id']], left_on='id_parent', right_on= 'id')
    info_enf = info_enf.merge(info[['naiss', 'id']], left_on='id_enf', right_on= 'id').drop(['id_x', 'id_y', 'enf'], axis=1)
    return info_enf


def load_from_csv(data_path):
    ''' the csv are directly produce after executing load_from_Rdata
            - we don't need to work on columns names'''
    # Workstate and wages        
    sali = pd.read_table(os.path.join(data_path, 'salaire.csv'), sep=',', index_col=0)
    workstate = pd.read_table(os.path.join(data_path, 'statut.csv'), sep=',', index_col=0)
    dates_to_col = [ year*100 + 1 for year in range(1901,2061)]
    workstate.columns =  dates_to_col
    sali.columns = dates_to_col
    for table in [sali, workstate]:
        table.columns = [int(col) for col in table.columns]
    # Individual info
    info_ind = pd.read_table(os.path.join(data_path, 'ind.csv'), sep=',', index_col=0)
    info_ind.loc[:, 'naiss'] = [datetime.date(1900 + int(year),1,1) for year in info_ind['t_naiss']]
    info_ind.loc[:, 'id'] = info_ind.index

    # Children set to 0
    dict_regime = {'FP': [5,6], 'RG': [3,4,1,2,9,8,0], 'RSI':[7]}
    for name_reg, code_reg in dict_regime.iteritems():
        nb_enf_regime = 0
        info_ind['nb_enf_' + name_reg] = nb_enf_regime
        info_ind['nb_enf_' + name_reg] = pd.to_numeric(info_ind['nb_enf_' + name_reg] , downcast='integer')
        
    info_ind['nb_enf_all'] = 0
    info_ind.loc[:,'nb_pac'] = 0
    info_ind = info_ind.sort_values(by = 'id')

    data = PensionData.from_arrays(workstate, sali, info_ind)
    

    return data



def selection_for_simul(data, yearsim):
    ''' the csv are directly produce after executing load_from_Rdata
            - we don't need to work on columns names'''
    # Age at simul        
    data.info_ind.loc[:,'agem'] =  (yearsim - pd.DatetimeIndex(data.info_ind['naiss']).year)*12
    # Date Selection 
    data_bounded = data.selected_dates(first=1949, last=yearsim)

    # Age selection:
    agem_selected = [12*63]
    select_id_depart = (data_bounded.info_ind.loc[:,'agem'].isin(agem_selected))
    id_selected = select_id_depart[select_id_depart == True].index
    #data_bounded.info_ind.drop('t_naiss', axis=1, inplace=True)
   
    ix_selected = [int(ident) - 1 for ident in id_selected]

    data_bounded.sali = data_bounded.sali[ix_selected, :]
    data_bounded.workstate = data_bounded.workstate[ix_selected, :]
    data_bounded.info_ind = data_bounded.info_ind.iloc[ix_selected,:]
    
#    if selection_id:
#        id_selected =  selection_id
#    elif selection_naiss:
#        select_id_depart = (info.loc[:,'t_naiss'].isin(selection_naiss))
#        id_selected = select_id_depart[select_id_depart == True].index
#
#    elif selection_age:
#        agem_selected = [12*age for age in selection_age]
#        select_id_depart = (info.loc[:,'agem'].isin(agem_selected))
#        id_selected = select_id_depart[select_id_depart == True].index


    return data_bounded

