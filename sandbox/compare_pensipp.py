# -*- coding: utf-8 -*-

import pandas as pd
import datetime
from pandas import read_table

from CONFIG_compare import pensipp_comparison_path
from simulation import PensionSimulation
from utils_compar import calculate_age, count_enf_born, count_enf_pac
from pension_data import PensionData
from pension_legislation import PensionParam, PensionLegislation
first_year_sal = 1949 

def _child_by_age(info_child, year, id_selected):
    info_child = info_child.loc[info_child['id_parent'].isin(id_selected),:]
    info_child['age'] = calculate_age(info_child.loc[:,'naiss'], datetime.date(year,1,1))
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
    info_enf.columns =  ['id_parent', 'enf', 'id_enf']
    info_enf = info_enf.merge(info_ind[['sexe', 'id']], left_on='id_parent', right_on= 'id')
    info_enf = info_enf.merge(info_ind[['naiss', 'id']], left_on='id_enf', right_on= 'id').drop(['id_x', 'id_y', 'enf'], axis=1)
    return info_enf

def load_from_csv(path):
    ''' the csv are directly produce after executing load_from_Rdata 
            - we don't need to work on columns names'''
    statut = read_table(path + 'statut.csv', sep=',', index_col=0)
    salaire = read_table(path + 'salaire.csv', sep=',', index_col=0)
    info = read_table(path + 'info.csv', sep=',', index_col=0)
    info_child = read_table(path + 'info_child.csv', sep=',', index_col=0)
    # is read_table not able to convert directly to datetime
    info_child['naiss'] = [datetime.date(int(date[0:4]),int(date[5:7]),int(date[8:10])) for date in info_child['naiss']]
    info['naiss'] = [datetime.date(int(year),1,1) for year in info['t_naiss']]
    result_pensipp = read_table(path + 'result_pensipp.csv', sep=',', index_col=0)
    for table in [salaire, statut]:
        table.columns = [int(col) for col in table.columns]
    return info, info_child, salaire, statut, result_pensipp

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
    info['t_naiss'] = 1900 + info['t_naiss']
    info['naiss'] = [datetime.date(int(year),1,1) for year in info['t_naiss']]
    info['id'] = info.index
    id_enf = com.load_data('enf')
    id_enf.columns =  [ 'enf'+ str(i) for i in range(id_enf.shape[1])]
    info_child = build_info_child(id_enf,info) 
    
    output_pensipp = path + 'output2.RData'
    r.r['load'](output_pensipp)
    result_pensipp = com.load_data('output1')
    result_pensipp.rename(columns= {'dec': 'decote_RG', 'surc': 'surcote_RG', 'taux': 'taux_RG', 'sam':'salref_RG', 'pliq_rg': 'pension_RG',
                                     'prorat' : 'CP_RG', 'pts_ar' : 'nb_points_arrco', 'pts_ag' : 'nb_points_agirc', 'pliq_ar' :'pension_arrco',
                                     'pliq_ag' :'pension_agirc', 'DA_rg_maj': 'DA_RG', 'taux_rg': 'taux_RG', 'pliq_fp': 'pension_FP',
                                     'taux_fp': 'taux_FP', 'DA_fp_maj':'DA_FP', 'DA_in' : 'DA_RSI_brute', 'DA_in_maj' : 'DA_RSI',
                                     'DAcible_rg': 'n_trim_RG', 'DAcible_fp':'n_trim_FP', 'CPcible_rg':'N_CP_RG'},
                                    inplace = True)     
    if to_csv:
        for table in ['info', 'info_child', 'salaire', 'statut', 'result_pensipp']:
            temp = eval(table)
            temp.to_csv(pensipp_comparison_path + table + '.csv', sep =',')
            
    return info, info_child, salaire, statut, result_pensipp

def compare_til_pensipp(pensipp_comparison_path, var_to_check_montant, var_to_check_taux, threshold, loggerlevel):
    try: 
        info, info_child, salaire, statut, result_pensipp = load_from_csv(pensipp_comparison_path)
    except:
        print(" Les données sont chargées à partir du Rdata et non du csv")
        info, info_child, salaire, statut, result_pensipp = load_from_Rdata(pensipp_comparison_path, to_csv=True)
    result_til = pd.DataFrame(columns = var_to_check_montant + var_to_check_taux, index = result_pensipp.index)
    result_til['yearliq'] = -1
    for yearsim in range(2004,2005):
        print(yearsim)
        info.loc[:,'agem'] =  (yearsim - info['t_naiss'])*12
        select_id = (info.loc[:,'agem'] ==  12*63)
        id_selected = select_id[select_id == True].index
        sali = salaire.loc[select_id, :]
        workstate = statut.loc[select_id, :]
        info_child = _child_by_age(info_child, yearsim, id_selected)
        nb_pac = count_enf_pac(info_child, info.index)
        nb_enf = count_enf_born(info_child, info.index)
        info_ind = info.loc[select_id,:]
        info_ind.loc[:,'nb_pac'] = nb_pac
        info_ind.loc[:,'nb_born'] = nb_enf
        if max(info_ind.loc[:,'sexe']) == 2:
            info_ind.loc[:,'sexe'] = info_ind.loc[:,'sexe'].replace(1,0)
            info_ind.loc[:,'sexe'] = info_ind.loc[:,'sexe'].replace(2,1)
        data = PensionData.from_arrays(workstate, sali, info_ind)
        data_bounded = data.selected_dates(first=first_year_sal, last=yearsim)
        param = PensionParam(yearsim, data_bounded)
        legislation = PensionLegislation(param)
        simul_til = PensionSimulation(data_bounded, legislation, loggerlevel)
        result_til_year = simul_til.profile_evaluate(to_check=True)
        id_year_in_initial = [ident for ident in result_til_year.index if ident in result_til.index] 
        assert (id_year_in_initial == result_til_year.index).all()
        result_til.loc[result_til_year.index, :] = result_til_year
        result_til.loc[result_til_year.index, 'yearliq'] = yearsim

    def _check_var(var, threshold, var_conflict, var_not_implemented):
        if var not in result_til.columns:
            print("La variable {} n'est pas bien implémenté dans Til".format(var))
            var_not_implemented['til'] += [var]
        if var not in result_pensipp.columns:
            print("La variable {} n'est pas bien implémenté dans Pensipp".format(var))
            var_not_implemented['pensipp'] += [var]
        to_compare = (result_til['yearliq']!= -1)
        til_compare = result_til.loc[to_compare,:]
        til_var = til_compare.loc[:, var].fillna(0)
        pensipp_var = result_pensipp.loc[to_compare,var].fillna(0)
        if (til_var == 0).all():
            var_not_implemented['til'] += [var]
        if (pensipp_var == 0).all():
            var_not_implemented['pensipp'] += [var]
        conflict = ((til_var.abs() - pensipp_var.abs()).abs() > threshold)
        if conflict.any():
            var_conflict += [var]
            print u"Le calcul de {} pose problème pour {} personne(s) sur {}: ".format(var, sum(conflict), sum(result_til['yearliq'] == 2004))
            print pd.DataFrame({
                "TIL": til_var[conflict],
                "PENSIPP": pensipp_var[conflict],
                "diff.": til_var[conflict].abs() - pensipp_var[conflict].abs(),
                "year_liq": til_compare.loc[conflict, 'yearliq']
                }).to_string()
            #relevant_variables = relevant_variables_by_var[var]
    var_conflict = []
    var_not_implemented = {'til':[], 'pensipp':[]}
    for var in var_to_check_montant:
        _check_var(var, threshold['montant'], var_conflict, var_not_implemented)
    for var in var_to_check_taux:
        _check_var(var, threshold['taux'], var_conflict, var_not_implemented)
    no_conflict = [variable for variable in var_to_check_montant + var_to_check_taux
                        if variable not in var_conflict + var_not_implemented.values()]  
    print( u"Avec un seuil de {}, le calcul est faux pour les variables suivantes : {} \n Il est mal implémenté dans : \n - Til: {} \n - Pensipp : {}\n Il ne pose aucun problème pour : {}").format(threshold, var_conflict, var_not_implemented['til'], var_not_implemented['pensipp'], no_conflict)   

if __name__ == '__main__':    

    var_to_check_montant = [ u'pension_RG', u'salref_RG', u'DA_RG', u'DA_RSI', 
                            u'nb_points_arrco', u'nb_points_agirc', u'pension_arrco', u'pension_agirc',
                            u'DA_FP', u'pension_FP',
                            u'n_trim_RG', 'N_CP_RG', 'n_trim_FP'
                            ] 
    var_to_check_taux = [u'taux_RG', u'surcote_RG', u'decote_RG', u'CP_RG',
                         u'taux_FP'
                          ]
    threshold = {'montant' : 1, 'taux' : 0.05}
    import logging
    import sys
    logging.basicConfig(format='%(funcName)s(%(levelname)s): %(message)s', level = logging.INFO, stream = sys.stdout)
    loggerlevel = {'evaluate': 'info'}
    compare_til_pensipp(pensipp_comparison_path, var_to_check_montant, var_to_check_taux, threshold, loggerlevel)

#    or to have a profiler : 
#    import cProfile
#    import re
#    command = """compare_til_pensipp(input_pensipp, output_pensipp, var_to_check_montant, var_to_check_taux, threshold)"""
#    cProfile.runctx( command, globals(), locals(), filename="profile_run_compare")