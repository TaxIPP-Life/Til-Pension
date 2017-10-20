# -*- coding: utf-8 -*-

import os
import datetime
import logging
import numpy as np
import pandas as pd

from til_pension.sandbox.compare.CONFIG_compare import pensipp_comparison_path
from til_pension.sandbox.compare.utils_compar import calculate_age, count_enf_pac, count_enf_by_year
from til_pension.pension_data import PensionData


log = logging.getLogger(__name__)


def _child_by_age(info_child, year, id_selected):
    info_child = info_child.query('id_parent in @id_selected').copy()
    info_child['age'] = calculate_age(info_child.naiss, datetime.date(year, 1, 1))
    nb_enf = info_child.groupby(['id_parent', 'age']).size().reset_index()
    nb_enf.columns = ['id_parent', 'age_enf', 'nb_enf']
    return nb_enf


def build_info_child(enf, info_ind):
    '''
    Input tables :
        - 'enf' : pour chaque personne sont donnés les identifiants de ses enfants
        - 'ind' : table des infos perso (dates de naissances notamment)
    Output table :
        - info_child_father : identifiant du pere, ages possibles des enfants, nombre d'enfant ayant cet age
        - info_child_mother : identifiant de la mere, ages possibles des enfants, nombre d'enfant ayant cet age
    '''
    info_enf = enf.stack().reset_index()
    info_enf.columns = ['id_parent', 'enf', 'id_enf']
    info_enf = info_enf.merge(info_ind[['sexe', 'id']], left_on = 'id_parent', right_on = 'id')
    info_enf = (info_enf
        .merge(info_ind[['naiss', 'id']], left_on = 'id_enf', right_on = 'id')
        .drop(
            ['id_x', 'id_y', 'enf'],
            axis = 1,
            )
        )
    return info_enf


def load_from_csv(path):
    ''' the csv are directly produce after executing load_from_Rdata
            - we don't need to work on columns names'''
    statut = pd.read_table(os.path.join(path, 'statut.csv'), sep=',', index_col=0)
    salaire = pd.read_table(os.path.join(path, 'salaire.csv'), sep=',', index_col=0)
    info = pd.read_table(os.path.join(path, 'info.csv'), sep=',', index_col=0)
    info_child = pd.read_table(os.path.join(path, 'info_child.csv'), sep=',', index_col=0)
    # is pd.read_table not able to convert directly to datetime
    info_child.loc[:, 'naiss'] = [
        datetime.date(int(date[0:4]), int(date[5:7]), int(date[8:10]))
        for date in info_child['naiss']
        ]
    t_naiss = info['t_naiss'].astype(int).copy()
    info['naiss'] = pd.to_datetime(
        pd.DataFrame(dict(
            year = t_naiss.where(t_naiss < 2262, 2262),
            month = 1,
            day = 1,
            )),
        )
    print info['naiss']
    for table in [salaire, statut]:
        table.columns = [int(col) for col in table.columns]
    assert pd.api.types.is_datetime64_any_dtype(info['naiss'])
    return info, info_child, salaire, statut


def load_from_Rdata(path, to_csv=False):
    import pandas.rpy.common as com
    from rpy2 import robjects as r
    input_pensipp = path + 'dataALL.RData'
    dates_to_col = [year * 100 + 1 for year in range(1901, 2061)]
    r.r("load('" + str(input_pensipp) + "')")
    statut = com.load_data('statut')
    statut.columns = dates_to_col
    salaire = com.load_data('salaire')
    salaire.columns = dates_to_col
    info = com.load_data('ind')
    info.loc[:, 'naiss'] = [datetime.date(1900 + int(year), 1, 1) for year in info['t_naiss']]
    info.loc[:, 'id'] = info.index
    id_enf = com.load_data('enf')
    id_enf.columns = ['enf' + str(i) for i in range(id_enf.shape[1])]
    info_child = build_info_child(id_enf, info)

    if to_csv:
        for table in ['info', 'info_child', 'salaire', 'statut']:
            temp = eval(table)
            temp.to_csv(pensipp_comparison_path + table + '.csv', sep =',')

    return info, info_child, salaire, statut


def load_pensipp_data(pensipp_path, yearsim, first_year_sal, selection_id = False, selection_naiss = False,
        selection_age = [63]):

    # try:
    log.info(" Les données sont chargées à partir du csv")
    info, info_child, salaire, statut = load_from_csv(pensipp_comparison_path)
    # except:
    #     log.info(" Les données sont chargées à partir du Rdata et non du csv")
    #     info, info_child, salaire, statut = load_from_Rdata(pensipp_comparison_path, to_csv=True)

    if max(info['sexe']) == 2:
        info.replace(dict(sexe = {1: 0}), inplace = True)
        info.replace(dict(sexe = {2: 1}), inplace = True)

    info['sexe'] = info['sexe'].astype(int)
    info['agem'] = ((yearsim - info['t_naiss']) * 12).astype('int')

    print info.columns
    if selection_id:
        id_selected = selection_id

    elif selection_naiss:
        select_id_depart = (info.t_naiss.isin(selection_naiss))
        id_selected = select_id_depart[select_id_depart].index.copy()

    elif selection_age:
        agem_selected = [12 * age for age in selection_age]
        id_selected = info.query('agem in @agem_selected')['id'].unique().tolist()

    print id_selected
    print info.id.loc[id_selected]
    ix_selected = [int(ident) - 1 for ident in id_selected]

    salaire.index.name = 'id'
    sali = salaire.reset_index().query('id in @id_selected').copy()
    info.drop('t_naiss', axis = 1, inplace=True)
    statut.index.name = 'id'
    workstate = statut.reset_index().query('id in @id_selected').copy()
    info_child_ = _child_by_age(info_child, yearsim, id_selected)

    nb_pac = count_enf_pac(info_child_, info.index)
    info_ind = info.query('id in @id_selected').copy()
    RESTART_HERE
    info_ind.loc[:, 'nb_pac'] = nb_pac
    print 'Before PensionData'
    print info_ind.dtypes

    data = PensionData.from_arrays(workstate, sali, info_ind)
    print 'After PensionData'
    print data.info_ind.dtype
    data_bounded = data.selected_dates(first=first_year_sal, last=yearsim)
    # TODO: commun declaration for codes and names regimes : Déclaration inapte (mais adapté à Taxipp)
    array_enf = count_enf_by_year(data_bounded.workstate, info_ind, info_child)
    # On met les inactifs/chomeurs/avpf ou préretraité au RG
    dict_regime = {'FP': [5, 6], 'RG': [3, 4, 1, 2, 9, 8, 0], 'RSI': [7]}
    # ajoute les variables d'enfants pour info_ind
    rec = data_bounded.info_ind
    print rec.dtype
    print rec.dtype.descr
    newdtype = [('nb_enf_' + name, '<i8') for name in dict_regime] + [('nb_enf_all', '<i8')]
    old_dtype = [(name.encode("ascii"), data_type) for name, data_type in rec.dtype.descr]  # See https://stackoverflow.com/questions/46329365/numpy-dtype-data-type-not-understood
    newdtype = np.dtype(old_dtype + newdtype)
    log.debug("Creating a dataframe using {}".format(newdtype))
    info_ind = pd.DataFrame.from_records(
        np.empty(rec.shape, dtype=newdtype)
        )
    # rempli les colonnes nb_enf
    for name_reg, code_reg in dict_regime.iteritems():
        nb_enf_regime = (array_enf * data_bounded.workstate.isin(code_reg)).sum(axis=1)
        info_ind['nb_enf_' + name_reg] = nb_enf_regime
        info_ind['nb_enf_all'] += nb_enf_regime
#         data_bounded.info_ind['nb_enf_' + name_reg] = nb_enf_regime
#         nb_enf_all += nb_enf_regime
#     info_ind.loc[:,'nb_enf'] = nb_enf_all
    # print sum(nb_enf_all -  info_ind.loc[:,'nb_born'])
    # print info_ind.loc[15478, ['nb_born', 'nb_enf', 'nb_enf_RG', 'nb_enf_FP', 'nb_enf_RSI']]
    data_bounded.info_ind = info_ind
    print info_ind
    BIM
    return data_bounded


def load_pensipp_result(pensipp_path, to_csv=False):
    path = os.path.join(pensipp_path, 'result_pensipp.csv')
    # try:
    log.debug("Loading from path {}".format(path))
    result_pensipp = pd.read_table(path, sep=',', index_col=0)
    # except Exception as e:
    #     import pandas.rpy.common as com
    #     from rpy2 import robjects as r
    #     print(" Les données sont chargées à partir du Rdata et non du csv")
    #     output_pensipp = os.path.join(pensipp_path, 'output20.RData')
    #     r.r['load'](output_pensipp)
    #     result_pensipp = com.load_data('output1')
    #     result_pensipp.rename(columns= {'dec_rg': 'decote_RG', 'surc_rg': 'surcote_RG', 'taux': 'taux_RG', 'sam_rg':'salref_RG', 'pliq_rg': 'pension_RG',
    #                                      'prorat_rg' : 'CP_RG', 'pts_ar' : 'nb_points_arrco', 'pts_ag' : 'nb_points_agirc', 'pliq_ar' :'pension_arrco',
    #                                      'pliq_ag' :'pension_agirc', 'DA_rg_maj': 'DA_RG', 'taux_rg': 'taux_RG', 'pliq_fp': 'pension_FP', 'prorat_fp': 'CP_FP',
    #                                      'taux_fp': 'taux_FP', 'surc_fp': 'surcote_FP', 'dec_fp':'decote_FP', 'DA_fp_maj':'DA_FP', 'DA_in' : 'DA_RSI_brute', 'DA_in_maj' : 'DA_RSI',
    #                                      'DAcible_rg': 'n_trim_RG', 'DAcible_fp':'n_trim_FP', 'CPcible_rg':'N_CP_RG', 'sam_fp':'salref_FP'},
    #                                     inplace = True)
    if to_csv:
        result_pensipp.to_csv(path, sep =',')

    return result_pensipp