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

def sal_to_trimcot(sal, salref, plafond):
    ''' A partir de la table des salaires côtisés au sein du régime, on détermine le vecteur du nombre de trimestres côtisés
    sal_cot : table ne contenant que les salaires annuels cotisés au sein du régime (lignes : individus / colonnes : date)
    salref : vecteur des salaires minimum (annuels) à comparer pour obtenir le nombre de trimestres '''
    sal_ = sal.translate_frequency(output_frequency='year', method='sum')
    sal_annuel = sal_.array
    sal_annuel[isnan(sal_annuel)] = 0
    division = divide(sal_annuel, salref).astype(int)
    nb_trim_cot = minimum(division, plafond) 
    return TimeArray(nb_trim_cot, sal_.dates)

def sali_in_regime(sali, workstate, code):
    ''' Cette fonction renvoie le TimeArray ne contenant que les salaires validés avec workstate == code_regime'''
    wk_selection = workstate.isin(code).array
    return TimeArray(wk_selection*sali.array, sali.dates)

def trim_cot_by_year_FP(workstate, code):
    ''' Cette fonction pertmet de calculer des nombres par trimesters validés dans un régime
    validation au sein du régime = 'workstate' = code
    TODO: gérer la comptabilisation des temps partiels quand variable présente'''
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
    return trim_service

def trim_ass_by_year(workstate, nb_trim_cot, code, compare_destinie):
    ''' 
    Comptabilisation des périodes assimilées à des durées d'assurance
    Pour l"instant juste chômage workstate == 5 (considéré comme indemnisé) 
    qui succède directement à une période de côtisation au RG workstate == [3,4]
    TODO: ne pas comptabiliser le chômage de début de carrière
    '''
    trim_by_year_chom = unemployment_trimesters(workstate, code_regime=code)
    trim_by_year_ass = trim_by_year_chom #+...
    if compare_destinie:
        trim_by_year_ass.array = (workstate.isin([code_chomage, code_preretraite])).array*4
    return trim_by_year_ass

#TODO: remove ? 
def revenu_valides(workstate, sali, code): #sali, 
    ''' Cette fonction pertmet de calculer des nombres par trimesters
    TODO: gérer la comptabilisation des temps partiels quand variable présente'''
    assert isinstance(workstate, TimeArray)
    #assert isinstance(sali, TimeArray)
    wk_selection = workstate.isin(code)
    wk_selection.translate_frequency(output_frequency='month', inplace=True)
    #TODO: condition not assuming sali is in year
    sali.translate_frequency(output_frequency='month', inplace=True)
    sali.array = around(divide(sali.array, 12), decimals=3)
    sal_selection = TimeArray(wk_selection.array*sali.array, sali.dates)
    trim = divide(wk_selection.array.sum(axis=1), 4).astype(int)
    return trim

def trim_cot_by_year_prive(data, code, salref):
    ''' FP Nombre de trimestres côtisés pour le régime général par année 
    ref : code de la sécurité sociale, article R351-9
    '''
    # Selection des salaires à prendre en compte dans le décompte (mois où il y a eu côtisation au régime)
    workstate = data.workstate
    sali = data.sali
    wk_selection = workstate.isin(code)
    sal_selection = TimeArray(wk_selection.array*sali.array, sali.dates)
    trim_cot_by_year = sal_to_trimcot(sal_selection, salref, plafond=4)
    return trim_cot_by_year
    
def sali_avpf(data, code, P_longit, compare_destinie):
    ''' Allocation vieillesse des parents au foyer (Regime general)
         - selectionne les revenus correspondant au periode d'AVPF
         - imputes des salaires de remplacements (quand non présents)
    '''
    workstate = data.workstate
    sali = data.sali
    avpf_selection = workstate.isin([code]).selected_dates(first_year_avpf)
    sal_for_avpf = sali.selected_dates(first_year_avpf)
    sal_for_avpf.array = sal_for_avpf.array*avpf_selection.array
    if sal_for_avpf.array.all() == 0:
        # TODO: frquency warning, cette manière de calculer les trimestres avpf ne fonctionne qu'avec des tables annuelles
        avpf = build_long_values(param_long=P_longit.common.avpf, first_year=first_year_avpf, last_year=data.datesim.year)
        sal_for_avpf.array = multiply(avpf_selection.array, 12*avpf)
        if compare_destinie == True:
            smic_long = build_long_values(param_long=P_longit.common.smic_proj, first_year=first_year_avpf, last_year=data.datesim.year) 
            sal_for_avpf.array = multiply(avpf_selection.array, smic_long)    
    return sal_for_avpf


def trim_mda(info_ind, P, yearleg): 
    ''' Majoration pour enfant à charge : nombre de trimestres acquis (Régime Général)'''
    # Rq : cette majoration n'est applicable que pour les femmes dans le RG
    child_mother = info_ind.loc[info_ind['sexe'] == 1, 'nb_born']
    if child_mother is not None:
        #TODO: remove pandas
        mda = Series(0, index=info_ind.index)
        # TODO: distinguer selon l'âge des enfants après 2003
        # ligne suivante seulement if child_mother['age_enf'].min() > 16 :
        P_mda = P.prive.RG.mda
        mda[child_mother.index.values] = P_mda.trim_per_child*child_mother.values
        cond_enf_min = child_mother.values >= P_mda.nb_enf_min
        mda.loc[~cond_enf_min] = 0
        #TODO:  Réforme de 2003 : min(1 trimestre à la naissance + 1 à chaque anniv, 8)
    return array(mda)

def nb_trim_bonif_CPCM(info_ind, trim_cot):
    ''' FP '''
    # TODO: autres bonifs : déportés politiques, campagnes militaires, services aériens, dépaysement 
    info_child = info_ind.loc[info_ind['sexe'] == 1, 'nb_born'] #Majoration attribuée aux mères uniquement
    bonif_enf = Series(0, index = info_ind.index)
    bonif_enf[info_child.index.values] = 4*info_child.values
    return array(bonif_enf*(trim_cot>0)) #+...

def nb_trim_bonif_5eme(trim_cot):
    ''' FP '''
    # TODO: Add bonification au cinquième pour les superactifs (policiers, surveillants pénitentiaires, contrôleurs aériens... à identifier grâce à workstate)
    super_actif = 0 # condition superactif à définir
    taux_5eme = 0.2
    bonif_5eme = minimum(trim_cot*taux_5eme, 5*4)
    return array(bonif_5eme*super_actif)

def nb_trim_mda(info_ind, trim_cot):
    # TODO: autres bonifs : déportés politiques, campagnes militaires, services aériens, dépaysement 
    info_child = info_ind.loc[info_ind['sexe'] == 1, 'nb_born'] #Majoration attribuée aux mères uniquement
    bonif_enf = Series(0, index = info_ind.index)
    bonif_enf[info_child.index.values] = 4*info_child.values
    return array(bonif_enf*(trim_cot>0)) #+...