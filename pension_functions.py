# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
from utils import interval_years, months_to_years
from datetime import datetime

chomage=2
avpf = 8
id_test = 21310 # 28332 #1882 #1851 #, 18255

def workstate_selection(table, code_regime=None, input_step='month', output_step='month', option='dummy'):
    ''' Input : monthly or yearly-table (lines: indiv, col: dates 'yyyymm') 
    Output : (0/1)-pandas matrix with 1 = indiv has worked at least one month during the civil year in this regime if yearly-table'''
    if not code_regime:
        raise Exception("Indiquer le code identifiant du régime")
        
    if input_step == output_step:
        selection = table.isin(code_regime).astype(int)
        table_code = table
    else: 
        year_start, year_end = interval_years(table)
        selected_dates = [100*year + 1 for year in range(year_start, year_end)]
        if output_step == 'month':
            selected_dates = [100*year + month + 1 for year in range(year_start, year_end) for month in range(12)]
        selection = pd.DataFrame(index = table.index, columns = selected_dates)
        table_code = pd.DataFrame(index = table.index, columns = selected_dates)
        for year in range(year_start, year_end) :
            code_selection = table[year * 100 + 1].isin(code_regime)
            table_code[year * 100 + 1] = table[year * 100 + 1]
            if input_step == 'month' and output_step == 'year': 
                for i in range(2,13):
                    date = year * 100 + i
                    code_selection = code_selection  * table[date].isin(code_regime)
                selection[year * 100 + 1] = code_selection.astype(int)
            elif input_step == 'year' and output_step == 'month':
                for i in range(1,13):
                    date = year * 100 + i
                    selection[date] = code_selection.astype(int) 
                    table_code[date] = table[year * 100 + 1]             
    if option == 'code':
        selection = table_code * selection
    return selection
    
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
            return 4 * nb_trim, unemp_trim
        
    table = workstate_selection(table, code_regime = code_regime + [chomage], input_step = input_step, output_step = input_step, option = 'code')
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
        sali = months_to_years(sali)

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
    
    def _trim_surcote(row, year_max = yearmax):
        year_surcote = row['yearsurcote']
        row.drop('yearsurcote', inplace = True)
        limit_index = year_max - year_surcote + 1
        if limit_index>0:
            nb_trim = np.array(row)[- limit_index :]
            return sum(nb_trim)
        else:
            return 0
        
    yearsurcote = [date.year for date in date_surcote]
    trim_by_year['yearsurcote'] = yearsurcote
    nb_trim_surcote = trim_by_year.apply(_trim_surcote, axis = 1)
    return nb_trim_surcote

def nb_pac(info_child, index):
    info_child['enf_pac'] = ( info_child['age_enf'] <= 18) * ( info_child['age_enf'] >= 0 )
    info = info_child.groupby(['id_parent', 'enf_pac']).size().reset_index()
    info = info.loc[info['enf_pac'] == True].drop('enf_pac', 1)
    info.columns = ['id_parent', 'nb_pac']
    info.index = info['id_parent']
    nb_pac= pd.Series(np.zeros(len(index)), index=index)
    nb_pac += info['nb_pac']
    return nb_pac.fillna(0)

def nb_born(info_child, index):
    info_child['enf_born'] =  ( info_child['age_enf'] >= 0 )
    info = info_child.groupby(['id_parent', 'enf_born']).size().reset_index()
    info = info.loc[info['enf_born'] == True].drop('enf_born', 1)
    info.columns = ['id_parent', 'nb_born']
    info.index = info['id_parent']
    nb_born= pd.Series(np.zeros(len(index)), index=index)
    nb_born += info['nb_born']
    return nb_born.fillna(0)