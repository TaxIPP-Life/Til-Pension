# -*- coding: utf-8 -*-

'''
Created on 30 mai 2014

@author: aeidelman
'''
from numpy import maximum, minimum, array, nonzero, divide, transpose, zeros, isnan, around, multiply
from pandas import Series

from pension_functions import unemployment_trimesters
from utils_pension import build_long_values, build_salref_bareme
from time_array import TimeArray

first_year_avpf = 1972
code_chomage = 2
code_preretraite = 9


def sali_in_regime(workstate, sali, code):
    ''' Cette fonction renvoie le TimeArray ne contenant que les salaires validés avec workstate == code_regime'''
    wk_selection = workstate.isin(code).array
    return TimeArray(wk_selection*sali.array, sali.dates)

def trim_cot_by_year_FP(data, code):
    ''' Cette fonction pertmet de calculer des nombres par trimesters validés dans un régime
    validation au sein du régime = 'workstate' = code
    TODO: gérer la comptabilisation des temps partiels quand variable présente'''
    workstate = data.workstate
    sali = data.sali
    trim_service = workstate.isin(code)
    frequency_init = trim_service.frequency
    trim_service.name = 'trim_cot'
    trim_service.translate_frequency(output_frequency='year', method='sum', inplace=True)
    if frequency_init == 'year':
        #from year to trimester
        trim_service.array = trim_service.array*4
    if frequency_init == 'month':
        #from month to trimester
        trim_service.array = divide(trim_service.array,3)
    return trim_service, sali_in_regime(workstate, sali, code)

def trim_ass_by_year(data, code, compare_destinie):
    ''' 
    Comptabilisation des périodes assimilées à des durées d'assurance
    Pour l"instant juste chômage workstate == 5 (considéré comme indemnisé) 
    qui succède directement à une période de côtisation au RG workstate == [3,4]
    TODO: ne pas comptabiliser le chômage de début de carrière
    '''
    workstate = data.workstate
    trim_by_year_chom = unemployment_trimesters(workstate, code_regime=code)
    trim_by_year_ass = trim_by_year_chom #+...
    if compare_destinie:
        trim_by_year_ass.array = (workstate.isin([code_chomage, code_preretraite])).array*4
    return trim_by_year_ass, None

#TODO: remove ? 
def validation_trimestre(data, code, salref, frequency='year'):  
    ''' FP Nombre de trimestres côtisés pour le régime général par année 
    ref : code de la sécurité sociale, article R351-9
    '''
    # Selection des salaires à prendre en compte dans le décompte (mois où il y a eu côtisation au régime)
    data.translate_frequency(output_frequency=frequency, method='sum')
    workstate = data.workstate
    sali = data.sali
    #selection des données du régime
    wk_selection = workstate.isin(code)
    sal_selection = TimeArray(wk_selection.array*sali.array, sali.dates, name='temp')
    # applique le bareme de legislation sur les salaires
    plafond=4
    sal_annuel = sal_selection.array
    sal_annuel[isnan(sal_annuel)] = 0
    division = divide(sal_annuel, salref).astype(int)
    trim_cot_by_year = TimeArray(minimum(division, plafond), sali.dates)
    return trim_cot_by_year, sal_selection
    
def imput_sali_avpf(data, code, P_longit, compare_destinie):
    #TODO: move to an other place
    workstate = data.workstate
    sali = data.sali
    avpf_selection = workstate.isin([code]).selected_dates(first_year_avpf)
    sal_for_avpf = sali.selected_dates(first_year_avpf)
    if sal_for_avpf.array.all() == 0:
        # TODO: frquency warning, cette manière de calculer les trimestres avpf ne fonctionne qu'avec des tables annuelles
        avpf = build_long_values(param_long=P_longit.common.avpf, first_year=first_year_avpf, last_year=data.datesim.year)
        sal_for_avpf.array = multiply(avpf_selection.array, 12*avpf)
        if compare_destinie == True:
            smic_long = build_long_values(param_long=P_longit.common.smic_proj, first_year=first_year_avpf, last_year=data.datesim.year) 
            sal_for_avpf.array = multiply(avpf_selection.array, smic_long)
    return sal_for_avpf


def trim_mda(info_ind, P): 
    ''' Majoration pour enfant à charge : nombre de trimestres acquis (Régime Général)'''
    # Rq : cette majoration n'est applicable que pour les femmes dans le RG
    child_mother = info_ind.loc[info_ind['sexe'] == 1, 'nb_born']
    if child_mother is not None:
        #TODO: remove pandas
        mda = Series(0, index=info_ind.index)
        # TODO: distinguer selon l'âge des enfants après 2003
        # ligne suivante seulement if child_mother['age_enf'].min() > 16 :
        mda[child_mother.index.values] = P.trim_per_child*child_mother.values
        cond_enf_min = child_mother.values >= P.nb_enf_min
        mda.loc[~cond_enf_min] = 0
        #TODO:  Réforme de 2003 : min(1 trimestre à la naissance + 1 à chaque anniv, 8)
    return array(mda)

def nb_trim_mda(info_ind):
    ''' FP '''
    # TODO: autres bonifs : déportés politiques, campagnes militaires, services aériens, dépaysement 
    info_child = info_ind.loc[info_ind['sexe'] == 1, 'nb_born'] #Majoration attribuée aux mères uniquement
    bonif_enf = Series(0, index = info_ind.index)
    bonif_enf[info_child.index.values] = 4*info_child.values
    return array(bonif_enf) 

def nb_trim_bonif_5eme(trim):
    ''' FP '''
    #TODO: 5*4 ? d'ou ca vient ? 
    #TODO: Add bonification au cinquième pour les superactifs (policiers, surveillants pénitentiaires, contrôleurs aériens... à identifier grâce à workstate)
    super_actif = 0 # condition superactif à définir
    taux_5eme = 0.2
    bonif_5eme = minimum(trim*taux_5eme, 5*4)
    return array(bonif_5eme*super_actif)

