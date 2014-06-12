# -*- coding:utf-8 -*-

from collections import defaultdict
import os
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0,parentdir) 

from numpy import maximum, minimum, array, nonzero, divide, transpose, zeros
from pandas import Series

from regime import RegimeBase, compare_destinie
from trimesters_functions import nb_trim_surcote
from sandbox.utils_compar import print_multi_info_numpy, _info_numpy
from trimesters_functions import trim_cot_by_year_FP, nb_trim_bonif_5eme, trim_mda

code_chomage = 5

class FonctionPublique(RegimeBase):
    
    def __init__(self):
        RegimeBase.__init__(self)
        self.name = 'FP'
        self.code_regime = [5,6]
        self.param_name = 'public.fp'
        
        self.code_sedentaire = 6
        self.code_actif = 5

    def get_trimesters_wages(self, data):
        trimesters = dict()
        wages = dict()
        trim_maj = dict()
        to_other = dict()
    
        info_ind = data.info_ind
                
        trim_valide, sal_regime = trim_cot_by_year_FP(data, self.code_regime)
        trim_to_RG, sal_to_RG = self.select_to_RG(data, trim_valide.copy(), sal_regime)
        trimesters['cot'] = trim_valide.subtract(trim_to_RG)
        wages['cot'] = sal_regime.subtract(sal_to_RG)
        trim_cotises = trimesters['cot'].sum(1)
        P_mda = self.P.public.fp.mda
        trim_maj['DA'] = trim_mda(info_ind, P_mda)*(trim_cotises>0)
        trim_maj['5eme'] = nb_trim_bonif_5eme(trim_cotises)*(trim_cotises>0)
        to_other['RegimeGeneral'] = {'trimesters': {'cot_FP' : trim_to_RG}, 'wages': {'sal_FP' : sal_to_RG}}
        output = {'trimesters': trimesters, 'wages': wages, 'maj': trim_maj}
        return output, to_other
        
    def _age_min_retirement(self, data):
        P = self.P.public.fp
        trim_actif, _ = trim_cot_by_year_FP(data, self.code_actif)
        trim_actif = trim_actif.array.sum(1)
        # age_min = age_min_actif pour les fonctionnaires actif en fin de carrières ou carrière mixte ayant une durée de service actif suffisante
        age_min_s = P.sedentaire.age_min
        age_min_a = P.actif.age_min
        age_min = age_min_a*(trim_actif >= P.actif.N_min) + age_min_s*(trim_actif < P.actif.N_min)
        return age_min
    
    def _build_age_max(self, data):
        P = self.P.public.fp
        last_fp = data.workstate.last_time_in(self.code_regime)
        actif = (last_fp == self.code_actif)
        sedentaire = (last_fp == self.code_sedentaire)
        age_max_s = P.sedentaire.age_max
        age_max_a = P.actif.age_max
        age_max = actif*age_max_a + sedentaire*age_max_s
        return age_max
    
             
    def select_to_RG(self, data, trim_by_year, sal_by_year):
        ''' Détermine le nombre de trimestres par année à rapporter au régime général
        output : trim_by_year_FP_to_RG '''
        P = reduce(getattr, self.param_name.split('.'), self.P)
        # N_min donné en mois
        workstate = data.workstate
        trim_cot = trim_by_year.sum(1)
        last_fp = data.workstate.last_time_in(self.code_regime)
        to_RG_actif = (3*trim_cot < P.actif.N_min)*(last_fp == self.code_actif)
        to_RG_sedentaire = (3*trim_cot < P.sedentaire.N_min)*(last_fp == self.code_sedentaire)
        to_RG = (to_RG_actif + to_RG_sedentaire)
        trim_by_year.array[~to_RG,:] = 0
        sal_by_year.array[~to_RG,:] = 0
        return trim_by_year, sal_by_year
        
    def calculate_coeff_proratisation(self, info_ind, trim_wage_regime, trim_wage_all):
        ''' on a le choix entre deux bonifications, 
                chacune plafonnée à sa façon '''
        P = self.P.public.fp
        trimesters = trim_wage_regime['trimesters']
        trim_maj = trim_wage_regime['maj']
        N_CP = P.plein.n_trim
        trim_regime = trimesters['regime'].sum(1)
        trim_bonif_5eme = trim_maj['5eme']
        CP_5eme = minimum(divide(trim_regime + trim_bonif_5eme, N_CP), 1)
        
        taux = P.plein.taux
        taux_bonif = P.taux_bonif
        trim_bonif_CPCM = trim_maj['DA'] # CPCM
        CP_CPCM = minimum(divide(maximum(trim_regime, N_CP) + trim_bonif_CPCM, N_CP), divide(taux_bonif, taux))
        
        return maximum(CP_5eme, CP_CPCM)

    def decote(self, data, trim_wage_all):
        ''' Détermination de la décote à appliquer aux pensions '''
        trimesters = trim_wage_all['trimesters']
        trim_maj = trim_wage_all['maj']
        yearleg = self.dateleg.year
        if yearleg < 2006:
            return zeros(data.info_ind.shape[0])
        else:
            agem = data.info_ind['agem']
            trim_decote = self.nb_trim_decote(trimesters, trim_maj, agem)
            P = reduce(getattr, self.param_name.split('.'), self.P)
            return P.decote.taux*trim_decote
        
    def _calculate_surcote(self, trim_wage_regime, trim_wage_all, date_start_surcote, age):
        ''' Détermination de la surcote à appliquer aux pensions '''
        yearsim = self.dateleg.year
        trimesters = trim_wage_regime['trimesters']
        if yearsim < 2005:
            return age*0
        else:
            P = reduce(getattr, self.param_name.split('.'), self.P)
            taux_surcote = P.surcote.taux
            plafond = P.surcote.nb_trim_max
            trim_surcote = nb_trim_surcote(trimesters['regime'], date_start_surcote,
                                                  first_year_surcote=2004)
            trim_surcote = minimum(trim_surcote, plafond)
            return taux_surcote*trim_surcote
        
    def calculate_salref(self, data, regime):
        last_fp_idx = data.workstate.idx_last_time_in(self.code_regime)
        last_fp = zeros(data.sali.array.shape[0])
        last_fp[last_fp_idx[0]] = data.sali.array[last_fp_idx]
        return last_fp
    
    def plafond_pension(self, pension_brute, salref, cp, surcote):
        return pension_brute