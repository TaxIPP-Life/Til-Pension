# -*- coding: utf-8 -*-

'''
Created on 30 mai 2014

@author: aeidelman
'''
from numpy import minimum, array, nonzero, divide, transpose, zeros, isnan, around, multiply, greater, where
from pandas import Series
from regime import compare_destinie
from time_array import TimeArray

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
        trim_service.array = multiply(trim_service.array,4)
    if frequency_init == 'month':
        #from month to trimester
        trim_service.array = divide(trim_service.array,3)
    return trim_service, sali_in_regime(workstate, sali, code)


def trim_ass_by_year(data, code, compare_destinie):
    ''' 
    Comptabilisation des périodes assimilées à des durées d'assurance
    Pour l"instant juste chômage workstate == 5 (considéré comme indemnisé) 
    qui succède directement à une période de côtisation au RG workstate == [3,4]
    '''
    workstate = data.workstate
    
    unemp_trim = workstate.select_code_after_period(code, code_chomage)
    if workstate.frequency == 'month':
        month_by_year_unemp = unemp_trim.translate_frequency('year', method='sum')
        trim_by_year_chom = TimeArray(divide(month_by_year_unemp, 3), workstate.dates)  
    else:
        assert workstate.frequency == 'year'
        trim_by_year_chom =  TimeArray(multiply(unemp_trim, 4), workstate.dates)
    
    trim_by_year_ass = trim_by_year_chom #+...
    if compare_destinie:
        trim_by_year_ass.array = (workstate.isin([code_chomage, code_preretraite])).array*4
    return trim_by_year_ass, None

#TODO: remove ? 
def validation_trimestre(data, code, salref, frequency='year', name=''):  
    ''' FP Nombre de trimestres côtisés pour le régime général par année 
    ref : code de la sécurité sociale, article R351-9
    '''
    name_sal = 'sali_' + name
    name_trim = 'trim_' + name
        
    # Selection des salaires à prendre en compte dans le décompte (mois où il y a eu côtisation au régime)
    data_validation = data.translate_frequency(output_frequency=frequency, method='sum')
    workstate = data_validation.workstate
    sal = data_validation.sali
    #selection des données du régime
    wk_selection = workstate.isin(code)
    sal_selection = TimeArray(wk_selection.array*sal.array, sal.dates, name=name_sal)
    # applique le bareme de legislation sur les salaires
    plafond = 4
    sal_annuel = sal_selection.array
    sal_annuel[isnan(sal_annuel)] = 0
    division = divide(sal_annuel, salref).astype(int)
    trim_cot_by_year = TimeArray(minimum(division, plafond), sal.dates, name=name_trim)
    return trim_cot_by_year, sal_selection
    
def imput_sali_avpf(data, code, P_longit, compare_destinie):
    #TODO: move to an other place
    data_avpf = data.selected_regime(code)
    sali_avpf = data_avpf.sali
    if sali_avpf.array.all() == 0:
        # TODO: frquency warning, cette manière de calculer les trimestres avpf ne fonctionne qu'avec des tables annuelles
        year_avpf = (data_avpf.workstate != 0)
        avpf = P_longit.common.avpf
        sali_avpf.array = 12*multiply(year_avpf, avpf)
        if compare_destinie == True:
            smic_long = P_longit.common.smic_proj
            sali_avpf.array = multiply(year_avpf, smic_long)
    return sali_avpf


def trim_mda(info_ind, name_regime, P): 
    ''' Majoration pour enfant : nombre de trimestres acquis'''
    child_mother = info_ind.loc[info_ind['sexe'] == 1, 'nb_enf_' + name_regime]
    if compare_destinie and name_regime != 'FP':
        child_mother = info_ind.loc[info_ind['sexe'] == 1, 'nb_enf']
    mda = Series(0, index=info_ind.index)
    # TODO: distinguer selon l'âge des enfants après 2003 
    # ligne suivante seulement if child_mother['age_enf'].min() > 16 :
    mda[child_mother.index.values] = P.trim_per_child*child_mother.values
    cond_enf_min = child_mother.values >= P.nb_enf_min
    mda.loc[~cond_enf_min] = 0
    #TODO:  Réforme de 2003 : min(1 trimestre à la naissance + 1 à chaque anniv, 8)
    return array(mda)

def nb_trim_bonif_5eme(trim):
    ''' FP '''
    #TODO: 5*4 ? d'ou ca vient ? 
    #TODO: Add bonification au cinquième pour les superactifs (policiers, surveillants pénitentiaires, contrôleurs aériens... à identifier grâce à workstate)
    super_actif = 0 # condition superactif à définir
    taux_5eme = 0.2
    bonif_5eme = minimum(trim*taux_5eme, 5*4)
    return array(bonif_5eme*super_actif)


def nb_trim_surcote(trim_by_year, selected_dates, date_start_surcote):
    ''' Cette fonction renvoie le vecteur numpy du nombre de trimestres surcotés entre la first_year_surcote et la last_year_surcote grâce à :
    - la table du nombre de trimestre comptablisé au sein du régime par année : trim_by_year.array
    - le vecteur des dates (format yyyymm) à partir desquelles les individus surcote (détermination sur cotisations tout régime confondu)
    '''
    assert trim_by_year.array.shape[1] == len(selected_dates)
    nb_trim = zeros(trim_by_year.array.shape[0])
    for i in range(len(selected_dates)):
        if selected_dates[i] == 1:
            date = trim_by_year.dates[i]
            to_keep = greater(date, date_start_surcote)
            nb_trim += trim_by_year.array[:,i]*to_keep
    return nb_trim

def nb_trim_decote(trimesters, trim_maj, agem, P):
    ''' Cette fonction renvoie le vecteur numpy du nombre de trimestres décotés 
    Lorsque les deux règles (d'âge et de nombre de trimestres cibles) jouent
    -> Ref : Article L351-1-2 : les bonifications de durée de services et majorations de durée d'assurance,
    à l'exclusion de celles accordées au titre des enfants et du handicap, ne sont pas prises en compte 
    dans la durée d'assurance tous régimes confondus pour apprécier la décote.
    '''
    age_annulation = array(P.decote.age_null)
    plafond = array(P.decote.nb_trim_max)
    n_trim = array(P.plein.n_trim)
    trim_decote_age = divide(age_annulation - agem, 3)
    
    trim_tot = trimesters['tot'].sum(1) + trim_maj['enf']
    trim_decote_cot = n_trim - trim_tot
    assert len(trim_decote_age) == len(trim_decote_cot)
    trim_plaf = minimum(minimum(trim_decote_age, trim_decote_cot), plafond)
    return array(trim_plaf*(trim_plaf>0))

