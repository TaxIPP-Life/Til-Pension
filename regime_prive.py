# -*- coding:utf-8 -*-

from datetime import datetime

import os
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0,parentdir) 

from numpy import minimum, maximum, array, divide, multiply

from regime import RegimeBase
from trimesters_functions import nb_trim_surcote, nb_trim_decote

def date_(year, month, day):
    return datetime.date(year, month, day)

class RegimePrive(RegimeBase):
    
    def __init__(self):
        RegimeBase.__init__(self)
        self.param_name = 'prive.RG' #TODO: move P.prive.RG used in the subclass RegimePrive in P.prive
        self.param_name_bis = None

    def _age_min_retirement(self, data=None):
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
    
    def trim_decote(self, data, trim_wage_all):
        ''' Détermination de la décote à appliquer aux pensions '''
        trimesters = trim_wage_all['trimesters']
        trim_maj = trim_wage_all['maj']
        P = reduce(getattr, self.param_name.split('.'), self.P)
        agem = data.info_ind['agem']
        if P.decote.dispositif == 1:
            age_annulation = P.decote.age_null
            trim_decote = max(divide(age_annulation - agem, 3), 0)
        elif P.decote.dispositif == 2:
            trim_decote = nb_trim_decote(trimesters, trim_maj, agem, P)
        return trim_decote

    def age_annulation_decote(self, data):
        ''' Détermination de l'âge d'annularion de la décote '''
        P = reduce(getattr, self.param_name.split('.'), self.P)
        return P.decote.age_null
        
    def calculate_coeff_proratisation(self, info_ind, trim_wage_regime, trim_wage_all):
        ''' Calcul du coefficient de proratisation '''
        
        def _assurance_corrigee(trim_regime, agem):
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
                trim_majo = divide(agem - age_taux_plein, 3)*(agem > age_taux_plein)
                elig_majo = (trim_regime < P.prorat.n_trim)
                correction = trim_regime*P.tx_maj*trim_majo*elig_majo
                return trim_regime + correction
            else:
                return trim_regime

        P =  reduce(getattr, self.param_name.split('.'), self.P)
        trim_regime = trim_wage_regime['trimesters']['regime'].sum(1) 
        trim_regime_maj = sum(trim_wage_regime['maj'].values())
        agem = info_ind['agem']
        trim_regime = trim_regime_maj + trim_regime  # _assurance_corrigee(trim_regime, agem) 
        #disposition pour montée en charge de la loi Boulin (ne s'applique qu'entre 72 et 74) :
        if P.prorat.application_plaf == 1:
            trim_regime = minimum(trim_regime, P.prorat.plaf) 
        CP = minimum(1, divide(trim_regime, P.prorat.n_trim))
        return CP
        
    def _calculate_surcote(self, trim_wage_regime, trim_wage_all, date_start_surcote, age):
        ''' Détermination de la surcote à appliquer aux pensions.'''
        P = reduce(getattr, self.param_name.split('.'), self.P)
        P_long = reduce(getattr, self.param_name.split('.'), self.P_longit)
        trim_by_year_RG = trim_wage_regime['trimesters']['regime']
        trim_by_year_tot = trim_wage_all['trimesters']['tot']

        # dispositif de type 0
        n_trim = P.plein.n_trim
        trim_tot = trim_by_year_tot.sum(axis=1)
        surcote = P.surcote.dispositif0.taux*(trim_tot - n_trim)*(trim_tot > n_trim)# = 0 après 1983
                 
        # dispositif de type 1
        if P.surcote.dispositif1.taux > 0: 
            trick = P.surcote.dispositif1.date_trick
            trick = str(int(trick))
            selected_dates = getattr(P_long.surcote.dispositif1, 'dates' + trick)
            if sum(selected_dates) > 0 :
                surcote += P.surcote.dispositif1.taux*nb_trim_surcote(trim_by_year_RG, selected_dates, date_start_surcote)
        
        # dispositif de type 2
        P2 = P.surcote.dispositif2
        if P2.taux0 > 0:
            selected_dates = P_long.surcote.dispositif2.dates
            basic_trim = nb_trim_surcote(trim_by_year_RG, selected_dates, date_start_surcote)
            maj_age_trim = nb_trim_surcote(trim_by_year_RG, selected_dates, 12*P2.age_majoration)
#             date_start_surcote_65 = self._date_start_surcote(trim_by_year_tot, trim_maj, age, age_start_surcote) #TODO: why it doesn't equal date_start_surcote ?
            basic_trim = basic_trim - maj_age_trim
            trim_with_majo = (basic_trim - P2.trim_majoration)*((basic_trim - P2.trim_majoration) >= 0)
            basic_trim = basic_trim - trim_with_majo
            surcote += P2.taux0*basic_trim + P2.taux_maj_trim*trim_with_majo + P2.taux_maj_age*maj_age_trim
            
        return surcote  
        
    def minimum_pension(self, trim_wages_reg, trim_wages_all, pension_reg, pension_all):
        ''' MICO du régime général : allocation différentielle
        RQ : ASPA et minimum vieillesse sont gérés par OF
        Il est attribué quels que soient les revenus dont dispose le retraité en plus de ses pensions : loyers, revenus du capital, activité professionnelle...
        + mécanisme de répartition si cotisations à plusieurs régimes
        TODO: coder toutes les évolutions et rebondissements 2004/2008'''
        P = reduce(getattr, self.param_name.split('.'), self.P)
        # pension_RG, pension, trim_RG, trim_cot, trim
        trimesters = trim_wages_reg['trimesters']
        trim_regime = trimesters['regime'].sum() + sum(trim_wages_reg['maj'].values())
        coeff = minimum(1, divide(trim_regime, P.prorat.n_trim))
        if P.mico.dispositif == 0:
            # Avant le 1er janvier 1983, comparé à l'AVTS
            min_pension = self.P.common.avts
            return maximum(min_pension - pension_reg,0)*coeff
        elif P.mico.dispositif == 1:
            # TODO: Voir comment gérer la limite de cumul relativement complexe (Doc n°5 du COR)
            mico = P.mico.entier
            return maximum(mico - pension_reg,0)*coeff
        elif P.mico.dispositif == 2:
            # A partir du 1er janvier 2004 les périodes cotisées interviennent (+ dispositif transitoire de 2004)
            nb_trim = P.prorat.n_trim
            trim_regime = trimesters['regime'].sum() #+ sum(trim_wages_regime['maj'].values())
            trim_cot_regime = sum(trimesters[key].sum() for key in trimesters.keys() if 'cot' in key)
            mico_entier = P.mico.entier*minimum(divide(trim_regime, nb_trim), 1)
            maj = (P.mico.entier_maj - P.mico.entier)*divide(trim_cot_regime, nb_trim)
            mico = mico_entier + maj*(trim_cot_regime >= P.mico.trim_min)
            return (mico - pension_reg)*(mico > pension_reg)*(pension_reg>0)

        
    def plafond_pension(self, pension_brute, salref, cp, surcote):
        ''' plafonnement à 50% du PSS 
        TODO: gérer les plus de 65 ans au 1er janvier 1983'''
        PSS = self.P.common.plaf_ss
        P = reduce(getattr, self.param_name.split('.'), self.P)
        taux_plein = P.plein.taux
        taux_PSS = P.plafond
        pension_surcote_RG = taux_plein*salref*cp*surcote
        return minimum(pension_brute - pension_surcote_RG, taux_PSS*PSS) + pension_surcote_RG

