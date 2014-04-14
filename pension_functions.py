# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
from utils import interval_years, months_to_years

chomage=2
avpf=8

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
    

def unemployment_trimesters(table, code_regime=None, input_step='month'):
    ''' Input : monthly or yearly-table (lines: indiv, col: dates 'yyyymm') 
    Output : vector with number of trimesters for unemployment'''
    if not code_regime:
        print "Indiquer le code identifiant du régime"
        
    def _select_unemployment(data, code_regime, option='dummy'):
        ''' Ne conserve que les périodes de chomage succédant directement à une période de cotisation au RG 
        TODO: A améliorer car boucle for très moche '''
        data_col = data.columns[1:]
        previous_col = data.columns[0]
        for col in data_col:
            data.loc[(data[previous_col] == 0) & (data[col] == chomage), col] = 0
            previous_col = col
        if option == 'code':
            data = data.replace(code_regime,0)
        else:
            assert option == 'dummy'
            data = data.isin([5]).astype(int)
        return data
    
    def _calculate_trim_unemployment(data, step, code_regime):
        ''' Détermination du vecteur donnant le nombre de trimestres comptabilisés comme chômage pour le RG '''
        unemp_trim = _select_unemployment(table, code_regime)
        nb_trim = unemp_trim.sum(axis = 1)
        
        if step == 'month':
            return np.divide(nb_trim, 3).round()
        else:
            assert step == 'year'
            return 4 * nb_trim
        
    table = workstate_selection(table, code_regime = code_regime + [chomage], input_step = input_step, output_step = input_step, option = 'code')
    nb_trim_chom = _calculate_trim_unemployment(table, step = input_step, code_regime = code_regime)
    return nb_trim_chom

def calculate_trim_cot(sal_cot, salref):
    ''' fonction de calcul effectif des trimestres d'assurance à partir d'une matrice contenant les salaires annuels cotisés au régime
    salcot : table ne contenant que les salaires annuels cotisés au sein du régime (lignes : individus / colonnes : date)
    salref : vecteur des salaires minimum (annuels) à comparer pour obtenir le nombre de trimestre'''
    sal_cot = sal_cot.fillna(0)
    nb_trim_cot = np.minimum(np.divide(sal_cot,salref).astype(int), 4)
    nb_trim_cot = nb_trim_cot.sum(axis=1)
    return nb_trim_cot
    
def calculate_SAM(sali, nb_years, time_step):
    ''' renvoie un vecteur des SAM '''
    if time_step == 'month' :
        sali = months_to_years(sali)
    
    def sum_sam(data):
        nb_sali = data[-1]
        data = np.sort(data[:-1])
        data = data[nb_sali:]
        if nb_sali != 0 :
            sam = data.sum() / nb_sali
        else:
            sam = 0
        return sam

    # deux tables aient le même index (pd.DataFrame({'sali' : sali.index.values, 'nb_years': nb_years.index.values}).to_csv('testindex.csv'))
    assert max(sali.index) == max(nb_years.index)
    sali = sali.fillna(0) 
    nb_sali = (sali != 0).sum(1)
    nb_years[nb_sali < nb_years] = nb_sali[nb_sali < nb_years]
    sali['nb_years'] = nb_years.values
    sam = sali.apply(sum_sam, 1)
    return sam
