# -*- coding:utf-8 -*-
import math
from datetime import datetime

import os
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0,parentdir) 
from time_array import TimeArray

from numpy import maximum, minimum, array, divide, zeros, multiply
from pandas import Series

from regime import RegimeBase, compare_destinie
from utils_pension import _info_numpy, print_multi_info_numpy
from trimesters_functions import nb_trim_surcote

def date_(year, month, day):
    return datetime.date(year, month, day)

class RegimePrive(RegimeBase):
    
    def __init__(self):
        RegimeBase.__init__(self)
        self.param_name = 'prive.RG' #TODO: move P.prive.RG used in the subclass RegimePrive in P.prive
        self.param_name_bis = None

    def _age_min_retirement(self, workstate=None):
        P = reduce(getattr, self.param_name.split('.'), self.P)
        return P.age_min
    
    def calculate_salref(self, data, wages):
        ''' SAM : Calcul du salaire annuel moyen de référence : 
        notamment application du plafonnement à un PSS'''
        P = reduce(getattr, self.param_name_bis.split('.'), self.P)
        nb_best_years_to_take = P.nb_years
        plafond = self.P_longit.common.plaf_ss
        revalo = self.P_longit.prive.RG.revalo 

        import pdb
        pdb.set_trace()
        for i in range(1, len(revalo)) :
            revalo[:i] *= revalo[i]
            
        sal_regime = wages['regime']
        sal_regime.translate_frequency(output_frequency='year', method='sum', inplace=True)
        years_sali = (sal_regime.array != 0).sum(1)
        nb_best_years_to_take = array(nb_best_years_to_take)
        nb_best_years_to_take[years_sali < nb_best_years_to_take] = years_sali[years_sali < nb_best_years_to_take]    
            
        if plafond is not None:
            print sal_regime.array.shape[1], len(plafond)
            assert sal_regime.array.shape[1] == len(plafond)
            sal_regime.array = minimum(sal_regime.array, plafond) 
        if revalo is not None:
            assert sal_regime.array.shape[1] == len(revalo)
            sal_regime.array = multiply(sal_regime.array,revalo)
        salref = sal_regime.best_dates_mean(nb_best_years_to_take)
        return salref.round(2)
    
    def assurance_maj(self, trim_RG, trim_tot, agem):
        ''' Détermination de la durée d'assurance corrigée introduite par la réforme Boulin
        (majoration quand départ à la retraite après 65 ans) '''
        P = reduce(getattr, self.param_name.split('.'), self.P)
        yearleg = self.dateleg.year
        age_taux_plein = P.decote.age_null
        if yearleg < 1983:
            return trim_RG
        else:
            trim_majo = maximum(divide(agem - age_taux_plein, 3), 0)
            elig_majo = (trim_RG < P.N_CP)
            trim_corr = trim_RG*(1 + P.tx_maj*trim_majo*elig_majo)
            return trim_corr
        
    def calculate_coeff_proratisation(self, info_ind, trim_wage_regime, trim_wage_all):
        ''' Calcul du coefficient de proratisation '''
        P =  reduce(getattr, self.param_name.split('.'), self.P)
        yearleg = self.dateleg.year
        trim_regime = trim_wage_regime['trimesters']['regime'].sum(1) + trim_wage_regime['maj']['DA']
        trim_tot = trim_wage_all['trimesters']['tot'].sum(1) + trim_wage_all['maj']['tot']
        agem = info_ind['agem']
        if compare_destinie:
            trim_CP = trim_regime 
        else:
            trim_CP = self.assurance_maj(trim_regime, trim_tot, agem)
        if 1948 <= yearleg and yearleg < 1972: 
            trim_CP= trim_CP + (120 - trim_CP)/2
        #TODO: voir si on ne met pas cette disposition spécifique de la loi Boulin dans la déclaration des paramètres directement
        elif yearleg < 1973:
            trim_CP = min(trim_CP, 128)
        elif yearleg < 1974:
            trim_CP = min(trim_CP, 136)            
        elif yearleg < 1975:
            trim_CP = min(trim_CP, 144)   
        else:
            trim_CP = minimum(trim_CP, P.N_CP)
        CP = minimum(1, divide(trim_CP, P.N_CP))
        return CP
    
    def decote(self, data, trim_wage_all):
        ''' Détermination de la décote à appliquer aux pensions '''
        yearleg = self.dateleg.year
        trimesters = trim_wage_all['trimesters']
        trim_maj = trim_wage_all['maj']
        P = reduce(getattr, self.param_name.split('.'), self.P)
        agem = data.info_ind['agem']
        if yearleg < 1983:
            age_annulation = P.decote.age_null
            trim_decote = max(divide(age_annulation - agem, 3), 0)
        else:
            trim_decote = self.nb_trim_decote(trimesters, trim_maj, agem)
        return P.decote.taux*trim_decote
        
    def _calculate_surcote(self, trim_wage_regime, trim_wage_all, date_start_surcote, age):
        ''' Détermination de la surcote à appliquer aux pensions.'''
        yearleg = self.dateleg.year
        P = reduce(getattr, self.param_name.split('.'), self.P)
        trim_by_year_RG = trim_wage_regime['trimesters']['regime']
        if 'maj' in trim_wage_regime.keys() :
            trim_maj = trim_wage_regime['maj']['DA']
        else:
            trim_maj = 0
        trim_by_year_tot = trim_wage_all['trimesters']['tot']
        n_trim = P.plein.n_trim
        
        def _trimestre_surcote_0408(trim_by_year_regime, trim_by_year_tot, trim_maj, date_start_surcote, age, P): 
            ''' Fonction permettant de déterminer la surcote associée des trimestres côtisés entre 2004 et 2008 
            4 premiers à 0.75%, les suivants à 1% ou si plus de 65 ans à 1.25% '''
            taux_4trim = P.taux_4trim
            taux_5trim = P.taux_5trim
            taux_65 = P.taux_65
            age_start_surcote = 65*12 
            date_start_surcote_65 = self._date_start_surcote(trim_by_year_tot, trim_maj, age, age_start_surcote)
            nb_trim_65 = nb_trim_surcote(trim_by_year_regime, date_start_surcote_65,
                                         first_year_surcote=2004, last_year_surcote=2009)
            nb_trim = nb_trim_surcote(trim_by_year_regime, date_start_surcote,
                                         first_year_surcote=2004, last_year_surcote=2009)
            nb_trim = nb_trim - nb_trim_65
            return taux_65*nb_trim_65 + taux_4trim*maximum(minimum(nb_trim,4), 0) + taux_5trim*maximum(nb_trim - 4, 0)
            
        if yearleg < 2004:
            taux_surcote = P.surcote.taux_07
            trim_tot = self.trim_by_year.sum(axis=1)
            return maximum(trim_tot - n_trim, 0)*taux_surcote 
        elif yearleg < 2007:
            return P.surcote.taux_07*nb_trim_surcote(trim_by_year_RG, date_start_surcote,
                                                     first_year_surcote=2003)
        elif yearleg < 2010:
            surcote_03 = P.surcote.taux_4trim*nb_trim_surcote(trim_by_year_RG, date_start_surcote,
                                                              first_year_surcote=2003, last_year_surcote=2004)
            surcote_0408 = _trimestre_surcote_0408(trim_by_year_RG, trim_by_year_tot, trim_maj, date_start_surcote, age, P.surcote)
            return surcote_03 + surcote_0408
        else:
            surcote_03 = P.surcote.taux_4trim*nb_trim_surcote(trim_by_year_RG, date_start_surcote,
                                                              first_year_surcote=2003, last_year_surcote=2004)
            surcote_0408 = _trimestre_surcote_0408(trim_by_year_RG, trim_by_year_tot, trim_maj, date_start_surcote, age, P.surcote)
            surcote_aft09 = P.surcote.taux*nb_trim_surcote(trim_by_year_RG, date_start_surcote,
                                                           first_year_surcote=2009)
            return surcote_03 + surcote_0408 + surcote_aft09   
        
    def minimum_contributif(self, pension_RG, pension, trim_RG, trim_cot, trim):
        ''' MICO du régime général : allocation différentielle 
        RQ : ASPA et minimum vieillesse sont gérés par OF
        Il est attribué quels que soient les revenus dont dispose le retraité en plus de ses pensions : loyers, revenus du capital, activité professionnelle... 
        + mécanisme de répartition si cotisations à plusieurs régimes'''
        yearleg = self.dateleg.year
        P = reduce(getattr, self.param_name.split('.'), self.P)
        n_trim = P.plein.n_trim
        if yearleg < 2004:
            mico = P.mico.entier 
            # TODO: règle relativement complexe à implémenter de la limite de cumul (voir site CNAV)
            return  maximum(0, mico - pension_RG)*minimum(1, divide(trim_cot, P.N_CP))
        else:
            mico_entier = P.mico.entier
            mico_maj = P.mico.entier_maj
            RG_exclusif = ( pension_RG == pension) | (trim <= n_trim)
            mico_RG = mico_entier + minimum(1, divide(trim_cot, P.N_CP))*(mico_maj - mico_entier)
            mico =  mico_RG*( RG_exclusif + (1 - RG_exclusif)*divide(trim_RG, trim))
            return maximum(0, mico - pension_RG)
        
    def plafond_pension(self, pension_brute, salref, cp, surcote):
        ''' plafonnement à 50% du PSS 
        TODO: gérer les plus de 65 ans au 1er janvier 1983'''
        PSS = self.P.common.plaf_ss
        P = reduce(getattr, self.param_name.split('.'), self.P)
        taux_plein = P.plein.taux
        taux_PSS = P.plafond
        pension_surcote_RG = taux_plein*salref*cp*surcote
        return minimum(pension_brute - pension_surcote_RG, taux_PSS*PSS) + pension_surcote_RG
        
            