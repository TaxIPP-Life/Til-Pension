# -*- coding:utf-8 -*-

from collections import defaultdict
import os
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0,parentdir) 

from numpy import maximum, minimum, array, nonzero, divide, transpose, zeros
from pandas import Series

from regime import RegimeBase, compare_destinie
from pension_functions import nb_trim_surcote
from utils_pension import print_multi_info_numpy, _info_numpy
from time_array import TimeArray

code_avpf = 8
code_chomage = 5

class FonctionPublique(RegimeBase):
    
    def __init__(self):
        RegimeBase.__init__(self)
        self.regime = 'FP'
        self.code_regime = [5,6]
        self.param_name = 'public.fp'
        
        self.code_sedentaire = 6
        self.code_actif = 5

    def get_trimesters_wages(self, data, to_check):
        trimesters = dict()
        wages = dict()
        trim_maj = dict()
        to_other = dict()
        
        workstate = data.workstate
        sali = data.sali
        info_ind = data.info_ind
                
        trim_valide = self.trim_cot_by_year(workstate)
        sal_regime = self.sali_in_regime(workstate, sali)
        trim_to_RG, sal_to_RG = self.select_to_RG(data, trim_valide, sal_regime)
        trimesters['cot'] = trim_valide.substract(trim_to_RG)
        wages['cot'] = sal_regime.substract(sal_to_RG)
        trim_maj['CPCM'] = self.nb_trim_bonif_CPCM(info_ind, trim_valide.sum())
        trim_maj['5eme'] = self.nb_trim_bonif_5eme(trim_valide.sum())
        to_other['RegimeGeneral'] = {'trimesters': {'cot_FP' : trim_to_RG}, 'wages': {'sal_FP' : sal_to_RG}}
        if to_check :
            to_check['DA_FP'] = (trimesters['cot'].sum()) // 4 #+ trimesters['maj_FP']) //4
        output = {'trimesters': trimesters, 'wages': wages, 'maj': trim_maj}
        return output, to_other
        
    def _age_min_retirement(self, workstate):
        P = self.P.public.fp
        trim_actif = self.trim_cot_by_year(workstate, self.code_actif).array.sum(1)
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
    def nb_trim_bonif_CPCM(self, info_ind, trim_cot):
        # TODO: autres bonifs : déportés politiques, campagnes militaires, services aériens, dépaysement 
        info_child = info_ind.loc[info_ind['sexe'] == 1, 'nb_born'] #Majoration attribuée aux mères uniquement
        bonif_enf = Series(0, index = info_ind.index)
        bonif_enf[info_child.index.values] = 4*info_child.values
        return array(bonif_enf*(trim_cot>0)) #+...

    def nb_trim_bonif_5eme(self, trim_cot):
        # TODO: Add bonification au cinquième pour les superactifs (policiers, surveillants pénitentiaires, contrôleurs aériens... à identifier grâce à workstate)
        super_actif = 0 # condition superactif à définir
        taux_5eme = 0.2
        bonif_5eme = minimum(trim_cot*taux_5eme, 5*4)
        return array(bonif_5eme*super_actif)
        
    def calculate_coeff_proratisation(self, info_ind, trimesters, trim_maj):
        ''' on a le choix entre deux bonifications, 
                chacune plafonnée à sa façon '''
        P = self.P.public.fp
        
        N_CP = P.plein.N_taux
        trim_regime = trimesters['regime'].sum(1)
        trim_bonif_5eme = trim_maj['5eme']
        CP_5eme = minimum(divide(trim_regime + trim_bonif_5eme, N_CP), 1)
        
        taux = P.plein.taux
        taux_bonif = P.taux_bonif
        trim_bonif_CPCM = trim_maj['CPCM']
        CP_CPCM = minimum(divide(maximum(trim_regime, N_CP) + trim_bonif_CPCM, N_CP), divide(taux_bonif, taux))
        
        return maximum(CP_5eme, CP_CPCM)

    def decote(self, data, trimesters, trim_maj):
        ''' Détermination de la décote à appliquer aux pensions '''
        yearleg = self.dateleg.year
        if yearleg < 2006:
            return zeros(data.info_ind.shape[0])
        else:
            P = reduce(getattr, self.param_name.split('.'), self.P)
            tx_decote = P.decote.taux
            age_annulation = P.decote.age_null
            N_taux = P.plein.N_taux
            agem = data.info_ind['agem']
            trim_decote_age = divide(age_annulation - agem, 3)
            trim_tot = trimesters['tot'].sum(1) + trim_maj['tot']
            trim_decote_cot = N_taux - trim_tot
            assert len(trim_decote_age) == len(trim_decote_cot)
            trim_decote = maximum(0, minimum(trim_decote_age, trim_decote_cot))
        return trim_decote*tx_decote
        
    def _calculate_surcote(self, trimesters, date_start_surcote, age):
        ''' Détermination de la surcote à appliquer aux pensions '''
        yearsim = self.dateleg.year
        if yearsim < 2004:
            return age*0
        else:
            P = reduce(getattr, self.param_name.split('.'), self.P)
            taux_surcote = P.surcote.taux
            nb_trim = nb_trim_surcote(trimesters['regime'], date_start_surcote)
            return taux_surcote*nb_trim

    def calculate_salref(self, data, regime):
        last_fp_idx = data.workstate.idx_last_time_in(self.code_regime)
        last_fp = zeros(data.sali.array.shape[0])
        last_fp[last_fp_idx[0]] = data.sali.array[last_fp_idx]
        return last_fp
    
    def plafond_pension(self, pension_brute, salref, cp, surcote):
        return pension_brute