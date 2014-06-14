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
from sandbox.utils_compar import print_multi_info_numpy, _info_numpy
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

        revalo = array(revalo)
        for i in range(1, len(revalo)) :
            revalo[:i] *= revalo[i]
            
        sal_regime = wages['regime']
        sal_regime.translate_frequency(output_frequency='year', method='sum', inplace=True)
        years_sali = (sal_regime.array != 0).sum(1)
        nb_best_years_to_take = array(nb_best_years_to_take)
        nb_best_years_to_take[years_sali < nb_best_years_to_take] = years_sali[years_sali < nb_best_years_to_take]    
            
        if plafond is not None:
            assert sal_regime.array.shape[1] == len(plafond)
            sal_regime.array = minimum(sal_regime.array, plafond) 
        if revalo is not None:
            assert sal_regime.array.shape[1] == len(revalo)
            sal_regime.array = multiply(sal_regime.array,revalo)
        salref = sal_regime.best_dates_mean(nb_best_years_to_take)
        return salref.round(2)
    
    def calculate_coeff_proratisation(self, info_ind, trim_wage_regime, trim_wage_all):
        ''' Calcul du coefficient de proratisation '''
        
        def _assurance_corrigee(trim_regime, trim_tot, agem):
            ''' 
            Deux types de corrections :
            - correction de 1948-1982
            - Détermination de la durée d'assurance corrigée introduite par la réforme Boulin
            (majoration quand départ à la retraite après 65 ans) à partir de 1983'''
            P = reduce(getattr, self.param_name.split('.'), self.P)
            
            if P.prorat.dispositif == 1:
                correction = (P.prorat.n_trim - trim_regime)/2
                return trim_regime + correction
            elif P.prorat.dispositif == 2:
                age_taux_plein = P.decote.age_null
                trim_majo = maximum(divide(agem - age_taux_plein, 3), 0)
                elig_majo = (trim_regime < P.prorat.n_trim)
                correction = trim_regime*P.tx_maj*trim_majo*elig_majo
                return trim_regime + correction
            else:
                return trim_regime

        P =  reduce(getattr, self.param_name.split('.'), self.P)
        trim_regime = trim_wage_regime['trimesters']['regime'].sum(1) + trim_wage_regime['maj']['DA']
        trim_tot = trim_wage_all['trimesters']['tot'].sum(1) + trim_wage_all['maj']['tot']

        agem = info_ind['agem']
        trim_CP = _assurance_corrigee(trim_regime, trim_tot, agem)
        #disposition pour montée en charge de la loi Boulin (ne s'applique qu'entre 72 et 74) :
        if P.prorat.application_plaf == 1:
            trim_CP = minimum(trim_CP, P.prorat.plaf) 
        CP = minimum(1, divide(trim_CP, P.prorat.n_trim))
        return CP
    
    def decote(self, data, trim_wage_all):
        ''' Détermination de la décote à appliquer aux pensions '''
        trimesters = trim_wage_all['trimesters']
        trim_maj = trim_wage_all['maj']
        P = reduce(getattr, self.param_name.split('.'), self.P)
        agem = data.info_ind['agem']
        if P.decote.dispositif == 1:
            age_annulation = P.decote.age_null
            trim_decote = max(divide(age_annulation - agem, 3), 0)
        elif P.decote.dispositif == 2:
            trim_decote = self.nb_trim_decote(trimesters, trim_maj, agem)
        return array(P.decote.taux)*trim_decote
        
    def _calculate_surcote(self, trim_wage_regime, trim_wage_all, date_start_surcote, age):
        ''' Détermination de la surcote à appliquer aux pensions.'''
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
            taux_4trim = P.taux_2a
            taux_5trim = P.taux_2b
            taux_65 = P.taux_2age
            age_start_surcote = 65*12 
            date_start_surcote_65 = self._date_start_surcote(trim_by_year_tot, trim_maj, age, age_start_surcote)
            
            
            nb_trim_65 = nb_trim_surcote(trim_by_year_regime, date_start_surcote_65,
                                         first_year_surcote=2004, last_year_surcote=2009)
            nb_trim = nb_trim_surcote(trim_by_year_regime, date_start_surcote,
                                         first_year_surcote=2004, last_year_surcote=2009)
            nb_trim = nb_trim - nb_trim_65
            return taux_65*nb_trim_65 + taux_4trim*maximum(minimum(nb_trim,4), 0) + taux_5trim*maximum(nb_trim - 4, 0)
            
        trim_tot = trim_by_year_tot.sum(axis=1)
         
        surcote = P.surcote.taux_0*maximum(trim_tot - n_trim, 0) # = 0 après 1983
        
        elif P.surcote.dispositif >= 1:
               surcote = P.surcote.taux_1*nb_trim_surcote(trim_by_year_RG, date_start_surcote, first_year_surcote=2003)
            or surcote = P.surcote.taux_1*nb_trim_surcote(trim_by_year_RG, date_start_surcote,
                                                          first_year_surcote=2003, last_year_surcote=2004)
        if P.surcote.dispositif >= 2:
            taux_4trim = P.taux_2a
            taux_5trim = P.taux_2b
            taux_65 = P.taux_2age
            age_start_surcote = 65*12 
            date_start_surcote_65 = self._date_start_surcote(trim_by_year_tot, trim_maj, age, age_start_surcote)
            
            
            nb_trim_65 = nb_trim_surcote(trim_by_year_regime, date_start_surcote_65,
                                         first_year_surcote=2004, last_year_surcote=2009)
            nb_trim = nb_trim_surcote(trim_by_year_regime, date_start_surcote,
                                         first_year_surcote=2004, last_year_surcote=2009)
            nb_trim = nb_trim - nb_trim_65
            dispositif = taux_65*nb_trim_65 + taux_4trim*maximum(minimum(nb_trim,4), 0) + taux_5trim*maximum(nb_trim - 4, 0)
            surcote += dispositif
            
        if P.surcote.dispositif == 3:
            surcote += P.surcote.taux_3*nb_trim_surcote(trim_by_year_RG, date_start_surcote,
                                                       first_year_surcote=2009)
        return surcote  
        
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
        
            