# -*- coding: utf-8 -*-
#import bottleneck as bn
import numpy as np
import pandas as pd
import pdb

from utils_pension import _isin, sum_by_years, translate_frequency

chomage=2
avpf = 8
id_test = 21310 # 28332 #1882 #1851 #, 18255   

def select_unemployment(data, code_regime, option='dummy', data_type='numpy'):
    ''' Ne conserve que les périodes de chomage succédant directement à une période de cotisation au régime
    TODO: A améliorer car boucle for très moche
    Rq : on fait l'hypothèse que les personnes étant au chômage en t0 côtisent au RG '''
    if data_type == 'numpy':
        unemp = np.zeros((data.shape[0],data.shape[1]))
        unemp[:,0] = (data[:,0] == chomage)
        #unemp.loc[unemp[previous_col] == chomage, previous_col] = 1 -> A commenter si l'on ne veut pas comptabiliser les trimestres de chômage initiaux (Hypothèse)
        previous_chom_reg = np.in1d(data[:,:-1],code_regime + [chomage]).reshape(data[:,:-1].shape)
        unemp = (data[:,1:] == chomage)
        selected_chom = previous_chom_reg*unemp
        unemp = np.zeros((data.shape[0],data.shape[1]))
        unemp[:,1:] = selected_chom
        return unemp
    
    if data_type == 'pandas':
        data_col = data.columns[1:]
        previous_col = data.columns[0]
        unemp = data.copy().replace(code_regime, 0)
        #unemp.loc[unemp[previous_col] == chomage, previous_col] = 1 -> A commenter si l'on ne veut pas comptabiliser les trimestres de chômage initiaux (Hypothèse)
        for col in data_col:
            selected_chom = np.in1d(data[previous_col],code_regime + [chomage]) & (data[col] == chomage)
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
        
    table = _isin(table, code_regime + [chomage])
    table = translate_frequency(table, input_frequency=input_step, output_frequency=input_step)
    nb_trim_chom, unemp_trim = _calculate_trim_unemployment(table, step = input_step, code_regime = code_regime)
    if output == 'table_unemployement':
        return nb_trim_chom, unemp_trim
    else:
        return nb_trim_chom


def calculate_SAM(sali, nb_years_pd, time_step, plafond=None, revalorisation=None, data_type='numpy'):
    ''' renvoie un vecteur des SAM 
    plaf : vecteur chronologique plafonnant les salaires (si abs pas de plafonnement)'''
    
    nb_sali = (sali != 0).sum(1)
    nb_years = np.array(nb_years_pd)
    nb_years[nb_sali < nb_years] = nb_sali[nb_sali < nb_years]
    if data_type == 'pandas':
        assert max(sali.index) == max(nb_years.index)
        sali = sali.fillna(0) 
        sali = np.array(sali)
    if time_step == 'month' :
        sali = sum_by_years(sali)
    def sum_sam(data):
        nb_sali = data[-1]
        #data = -bn.partsort(-data, nb_sali)[:nb_sali]
        data = np.sort(data[:-1])
        data = data[-nb_sali:]
        if nb_sali == 0 :
            sam = 0
        else:
            sam = data.sum() / nb_sali
        return sam

    # deux tables aient le même index (pd.DataFrame({'sali': sali.index.values, 'nb_years': nb_years.index.values}).to_csv('testindex.csv'))

    if plafond is not None:
        assert sali.shape[1] == len(plafond)
        sali = np.minimum(sali, plafond) 
    if revalorisation is not None:
        assert sali.shape[1] == len(revalorisation)
        sali = np.multiply(sali,revalorisation)
    sali_sam = np.zeros((sali.shape[0],sali.shape[1]+1))
    sali_sam[:,:-1] = sali
    sali_sam[:,-1] = nb_years
    sam = np.apply_along_axis(sum_sam, axis=1, arr=sali_sam)
    #sali.apply(sum_sam, 1)
    return pd.Series(sam, index = nb_years_pd.index)

def nb_trim_surcote(trim_by_year, date_surcote):
    ''' Cette fonction renvoie le vecteur numpy du nombre de trimestres surcotés à partir de :
    - la table du nombre de trimestre comptablisé au sein du régime par année : trim_by_year.array
    - le vecteur des dates (format yyyymm) à partir desquelles les individus surcote (détermination sur cotisations tout régime confondu)
    '''
    yearmax = max(trim_by_year.dates)
    yearmin = min(date_surcote) 
    # Possible dates for surcote :
    dates_surcote = [date for date in trim_by_year.dates
                      if date >= yearmin]

    output = np.zeros(len(date_surcote))
    for date in dates_surcote:
        to_keep = np.where(np.greater(date, date_surcote))[0]
        ix_date = trim_by_year.dates.index(yearmax)
        if to_keep.any():
            output[to_keep] += trim_by_year.array[to_keep, ix_date]
    return output

def count_enf_pac(info_child, index):
    info_child['enf_pac'] = ( info_child['age_enf'] <= 18) * ( info_child['age_enf'] >= 0 )
    info = info_child.groupby(['id_parent', 'enf_pac']).size().reset_index()
    info = info.loc[info['enf_pac'] == True].drop('enf_pac', 1)
    info.columns = ['id_parent', 'nb_pac']
    info.index = info['id_parent']
    nb_pac= pd.Series(np.zeros(len(index)), index=index)
    nb_pac += info['nb_pac']
    return nb_pac.fillna(0)

def count_enf_born(info_child, index):
    info_child['enf_born'] =  ( info_child['age_enf'] >= 0 )
    info = info_child.groupby(['id_parent', 'enf_born']).size().reset_index()
    info = info.loc[info['enf_born'] == True].drop('enf_born', 1)
    info.columns = ['id_parent', 'nb_born']
    info.index = info['id_parent']
    nb_born= pd.Series(np.zeros(len(index)), index=index)
    nb_born += info['nb_born']
    return nb_born.fillna(0)
