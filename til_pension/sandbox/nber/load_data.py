# -*- coding: utf-8 -*-

import os
import datetime
import numpy as np
import pandas as pd
from numpy.lib import recfunctions

from til_pension.sandbox.nber.CONFIG_nber import data_path
from til_pension.pension_data import PensionData


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
    statut = pd.read_table(os.path.join(data_path, 'statut.csv'), sep=',', index_col=0)
    salaire = pd.read_table(os.path.join(data_path, 'salaire.csv'), sep=',', index_col=0)
    dates_to_col = [ year*100 + 1 for year in range(1901,2061)]
    statut.columns =  dates_to_col
    salaire.columns = dates_to_col
    for table in [salaire, statut]:
        table.columns = [int(col) for col in table.columns]
    
    info = pd.read_table(os.path.join(data_path, 'ind.csv'), sep=',', index_col=0)
    info.loc[:, 'naiss'] = [datetime.date(1900 + int(year),1,1) for year in info['t_naiss']]
    info.loc[:, 'id'] = info.index
    
    enf = pd.read_table(os.path.join(data_path, 'enf.csv'), sep=',', index_col=0)
    enf.columns =  [ 'enf'+ str(i) for i in range(enf.shape[1])]
    info_child = build_info_child(enf, info)
    info_child.loc[:, 'naiss'] = [datetime.date(int(date[0:4]), int(date[5:7]), int(date[8:10]))
                          for date in info_child['naiss']]

    return info, info_child, salaire, statut


def load_from_Rdata(path, to_csv=False):
    import pandas.rpy.common as com
    from rpy2 import robjects as r
    input_pensipp = path + 'dataALL.RData'
    dates_to_col = [ year*100 + 1 for year in range(1901,2061)]
    r.r("load('" + str(input_pensipp) + "')")
    statut = com.load_data('statut')
    statut.columns =  dates_to_col
    salaire = com.load_data('salaire')
    salaire.columns = dates_to_col
    info = com.load_data('ind')
    info.loc[:, 'naiss'] = [datetime.date(1900 + int(year),1,1) for year in info['t_naiss']]
    info.loc[:, 'id'] = info.index
    id_enf = com.load_data('enf')
    id_enf.columns =  [ 'enf'+ str(i) for i in range(id_enf.shape[1])]
    info_child = build_info_child(id_enf,info)

    if to_csv:
        for table in ['info', 'info_child', 'salaire', 'statut']:
            temp = eval(table)
            temp.to_csv(pensipp_comparison_path + table + '.csv', sep =',')

    return info, info_child, salaire, statut


def load_data(path):
    input_pensipp = data_path + 'dataALL.RData'
    dates_to_col = [ year*100 + 1 for year in range(1901,2061)]
    r.r("load('" + str(input_pensipp) + "')")
    statut = com.load_data('statut')
    statut.columns =  dates_to_col
    salaire = com.load_data('salaire')
    salaire.columns = dates_to_col
    info = com.load_data('ind')
    info.loc[:, 'naiss'] = [datetime.date(1900 + int(year),1,1) for year in info['t_naiss']]
    info.loc[:, 'id'] = info.index
    id_enf = com.load_data('enf')
    id_enf.columns =  [ 'enf'+ str(i) for i in range(id_enf.shape[1])]
    info_child = build_info_child(id_enf,info)

    if to_csv:
        for table in ['info', 'info_child', 'salaire', 'statut']:
            temp = eval(table)
            temp.to_csv(pensipp_comparison_path + table + '.csv', sep =',')

    return info, info_child, salaire, statut

