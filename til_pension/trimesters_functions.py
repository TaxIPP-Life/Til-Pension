# -*- coding: utf-8 -*-

'''
Created on 30 mai 2014

@author: aeidelman
'''
from numpy import minimum, divide, array, zeros, multiply, greater
from til_pension.regime import compare_destinie


def trimesters_in_code(data, code):
    workstate = data.workstate
    frequency_init = workstate.frequency
    in_code = workstate.isin(code)
    in_code.translate_frequency(output_frequency='year', method='sum', inplace=True)
    # number of trimesters
    if frequency_init == 'year':
        trim_in_code = multiply(in_code, 4)
    if frequency_init == 'month':
        trim_in_code = divide(in_code, 3)
    return trim_in_code


def trimesters_after_event(data, event, code):
    '''
    Comptabilisation des périodes assimilées à des durées d'assurance
    Pour l"instant juste chômage (considéré comme indemnisé)
    qui succède directement à une période de côtisation au RG workstate == [3,4]
    '''
    workstate = data.workstate
    frequency_init = workstate.frequency
    after_event = workstate.select_code_after_period(event, code)
    if frequency_init == 'month':
        month_after_event = after_event.translate_frequency('year', method='sum')
        trim_after_event = divide(month_after_event, 3)
    if frequency_init == 'year':
        trim_after_event = multiply(after_event, 4)
    return trim_after_event


def imput_sali_avpf(data, code, P_longit):
    # TODO: move to an other place
    data_avpf = data.selected_regime(code)
    sali_avpf = data_avpf.sali
    if (sali_avpf == 0).all():
        # TODO: frquency warning, cette manière de calculer les trimestres avpf
        # ne fonctionne qu'avec des tables annuelles
        year_avpf = (data_avpf.workstate != 0)
        avpf = P_longit.common.avpf
        sali_avpf = 12*multiply(year_avpf, avpf)
    return sali_avpf


def trim_mda(info_ind, name_regime, P):
    ''' Majoration pour enfant : nombre de trimestres acquis'''
    child_mother = info_ind['nb_enf_' + name_regime]
    if compare_destinie and name_regime != 'FP':
        child_mother = info_ind['nb_enf_all']
    # TODO: distinguer selon l'âge des enfants après 2003:  Réforme de 2003 :
    #       min(1 trimestre à la naissance + 1 à chaque anniv
    # ligne suivante seulement if child_mother['age_enf'].min() > 16 :
    mda = P.trim_per_child*child_mother
    cond_enf_min = child_mother >= P.nb_enf_min
    mda[~cond_enf_min] = 0
    mda[info_ind['sexe'] != 1] = 0
    return mda.values


def nb_trim_surcote(trim_by_year, selected_dates, date_start_surcote):
    ''' Cette fonction renvoie le vecteur numpy du nombre de trimestres surcotés
        entre la first_year_surcote et la last_year_surcote grâce à :
            - la table du nombre de trimestre comptablisé au sein du régime
              par année : trim_by_year
            - le vecteur des dates (format yyyymm) à partir desquelles les
              individus surcote (détermination sur cotisations tous régimes confondus)
    '''
    assert trim_by_year.shape[1] == len(selected_dates)
    nb_trim = zeros(trim_by_year.shape[0])
    for i in range(len(selected_dates)):
        if selected_dates[i] == 1:
            date = trim_by_year.dates[i]
            to_keep = greater(date, date_start_surcote)
            nb_trim += trim_by_year[:, i]*to_keep
    return nb_trim


def nb_trim_decote(trimesters, trim_maj_enf, agem, P):
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

    trim_tot = trimesters.sum(axis=1) + trim_maj_enf
    trim_decote_cot = n_trim - trim_tot
    assert len(trim_decote_age) == len(trim_decote_cot)
    trim_plaf = minimum(minimum(trim_decote_age, trim_decote_cot), plafond)
    return array(trim_plaf * (trim_plaf > 0))


def nb_trim_decote_from_external(trim_tot_ref, agem, P):
    ''' Cette fonction renvoie le vecteur numpy du nombre de trimestres décotés lorsqu'une
    source externe (ex: EIR) a permis de reconstitué le nombre de trimestres totaux pris comme référence
    '''
    age_annulation = array(P.decote.age_null)
    plafond = array(P.decote.nb_trim_max)
    n_trim = array(P.plein.n_trim)
    trim_decote_age = divide(age_annulation - agem, 3)
    trim_decote_cot = n_trim - trim_tot_ref
    assert len(trim_decote_age) == len(trim_decote_cot)
    trim_plaf = minimum(minimum(trim_decote_age, trim_decote_cot), plafond)
    return array(trim_plaf * (trim_plaf > 0))
