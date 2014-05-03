# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
from utils import sum_by_years
from datetime import datetime
import pdb

chomage=2
avpf = 8
id_test = 21310 # 28332 #1882 #1851 #, 18255

def translate_frequency(table, input_frequency='month', output_frequency='month', method=None):
    '''method should eventually control how to switch from month based table to year based table
        so far we assume year is True if January is True 
        '''
    if input_frequency == output_frequency:
        return table
    if output_frequency == 'year': # if True here, input_frequency=='month'
        detected_years = set([date // 100 for date in table.columns])
        output_dates = [100*x + 1 for x in detected_years]
        #here we could do more complex
        if method is None:
            return table.loc[:, output_dates]
        if method is 'sum':
            pdb.set_trace()
            return output_table
    if output_frequency == 'month': # if True here, input_frequency=='year'
        output_dates = [x + k for k in range(12) for x in table.columns ]
        output_table1 = pd.DataFrame(np.tile(table, 12), index=table.index, columns=output_dates)
        return output_table1.reindex_axis(sorted(output_table1.columns), axis=1)       
    
def select_unemployment(data, code_regime, option='dummy'):
    ''' Ne conserve que les périodes de chomage succédant directement à une période de cotisation au régime
    TODO: A améliorer car boucle for très moche
    Rq : on fait l'hypothèse que les personnes étant au chômage en t0 côtisent au RG '''
    data_col = data.columns[1:]
    previous_col = data.columns[0]
    unemp = data.copy().replace(code_regime, 0)
    #unemp.loc[unemp[previous_col] == chomage, previous_col] = 1 -> A commenter si l'on ne veut pas comptabiliser les trimestres de chômage initiaux (Hypothèse)
    for col in data_col:
        selected_chom = (data[previous_col].isin(code_regime + [chomage]))& (data[col] == chomage)
        unemp.loc[selected_chom, col] = 1
        previous_col = col
    if option == 'code':
        unemp = unemp.replace(1, chomage)
    return unemp == 1

def unemployment_trimesters(table, code_regime = None, input_step = 'month', output = None):
    ''' Input : monthly or yearly-table (lines: indiv, col: dates 'yyyymm') 
    Output : vector with number of trimesters for unemployment'''
    if not code_regime:
        print "Indiquer le code identifiant du régime"
        
    def _calculate_trim_unemployment(data, step, code_regime):
        ''' Détermination du vecteur donnant le nombre de trimestres comptabilisés comme chômage pour le RG '''
        unemp_trim = select_unemployment(table, code_regime)
        nb_trim = unemp_trim.sum(axis = 1)
        
        if step == 'month':
            return np.divide(nb_trim, 3).round(), unemp_trim
        else:
            assert step == 'year'
            return 4*nb_trim, unemp_trim
        
    table = table.isin(code_regime + [chomage])
    table = translate_frequency(table, input_frequency=input_step, output_frequency=input_step)
    nb_trim_chom, unemp_trim = _calculate_trim_unemployment(table, step = input_step, code_regime = code_regime)
    if output == 'table_unemployement':
        return nb_trim_chom, unemp_trim
    else:
        return nb_trim_chom

def sal_to_trimcot(sal_cot, salref, option='vector'):
    ''' A partir de la table des salaires annuels côtisés au sein du régime, on détermine le vecteur du nombre de trimestres côtisés jusqu'à la date mentionnée
    sal_cot : table ne contenant que les salaires annuels cotisés au sein du régime (lignes : individus / colonnes : date)
    salref : vecteur des salaires minimum (annuels) à comparer pour obtenir le nombre de trimestre
    last_year: dernière année (exclue) jusqu'à laquelle on déompte le nombre de trimestres'''
    sal_cot = sal_cot.fillna(0)
    nb_trim_cot = np.minimum(np.divide(sal_cot,salref).astype(int), 4)
    if option == 'table':
        return nb_trim_cot
    else :
        nb_trim_cot = nb_trim_cot.sum(axis=1)
        return nb_trim_cot
    
    
def calculate_SAM(sali, nb_years, time_step, plafond=None, revalorisation=None):
    ''' renvoie un vecteur des SAM 
    plaf : vecteur chronologique plafonnant les salaires (si abs pas de plafonnement)'''
    if time_step == 'month' :
        sali = sum_by_years(sali)
#     pdb.set_trace()
    def sum_sam(data):
        nb_sali = data[-1]
        data = np.sort(data[:-1])
        data = data[-nb_sali:]
        if nb_sali != 0 :
            sam = data.sum() / nb_sali
        else:
            sam = 0
        return sam

    # deux tables aient le même index (pd.DataFrame({'sali' : sali.index.values, 'nb_years': nb_years.index.values}).to_csv('testindex.csv'))
    assert max(sali.index) == max(nb_years.index)
    sali = sali.fillna(0) 
    if plafond is not None:
        #print sali.ix[id_test,:]
        assert sali.shape[1] == len(plafond)
        sali = np.minimum(sali, plafond) 
        #print sali.ix[id_test,:]
    if revalorisation is not None:
        assert sali.shape[1] == len(revalorisation)
        sali = np.multiply(sali,revalorisation)
        #print sali.ix[id_test,:]
    nb_sali = (sali != 0).sum(1)
    nb_years[nb_sali < nb_years] = nb_sali[nb_sali < nb_years]
    #print sali.ix[id_test]
    sali['nb_years'] = nb_years.values
    sam = sali.apply(sum_sam, 1)
    return sam

def nb_trim_surcote(trim_by_year, date_surcote):
    ''' Cette fonction renvoie le vecteur du nombre de trimestres surcotés à partir de :
    - la table du nombre de trimestre comptablisé au sein du régime par année
    - le vecteur des dates à partir desquelles les individus surcote (détermination sur cotisations tout régime confondu)
    TODO: Comptabilisation plus fine pour surcote en cours d'années'''
    if 'yearsurcote' in trim_by_year.columns:
        trim_by_year = trim_by_year.drop('yearsurcote', axis=1)
    yearmax = np.divide(max(trim_by_year.columns), 100)  

#     yearsurcote = [date.year for date in date_surcote]
    limit_index = np.array([yearmax - date.year + 1 for date in date_surcote])

    output = pd.Series(0, index=trim_by_year.index)
    ncol = trim_by_year.shape[1]
    #TODO: remove condition on ncol, it should not occur with a good use
    for limit in range(min(max(limit_index), ncol)):
        to_keep = limit_index > limit
        output[to_keep] += trim_by_year.iloc[to_keep, -(limit+1)]
            
    return output
