# -*- coding:utf-8 -*-

import os
from numpy import array, maximum, minimum, divide, zeros, inf

from til_pension.regime import RegimeBase
from til_pension.trimesters_functions import nb_trim_surcote, nb_trim_decote, trim_cot_by_year_FP, nb_trim_bonif_5eme, trim_mda
from til_pension.regime import compare_destinie
code_chomage = 5

# TODO: clear wages and sal_regime

class FonctionPublique(RegimeBase):

    def __init__(self):
        RegimeBase.__init__(self)
        self.name = 'FP'
        self.code_regime = [5,6]
        self.param_name = 'public.fp'

        self.code_sedentaire = 6
        self.code_actif = 5


#     def get_trimesters_wages(self, data):
#         trimesters = dict()
#         wages = dict()
#         trim_maj = dict()
#         to_other = dict()
#         info_ind = data.info_ind
# 
#         trim_valide, sal_regime = trim_cot_by_year_FP(data, self.code_regime)
#         trim_to_RG, sal_to_RG = self.select_to_RG(data, trim_valide.copy(), sal_regime)
#         trimesters['cot'] = trim_valide - trim_to_RG
#         wages['cot'] = sal_regime - sal_to_RG
#         trim_cotises = trimesters['cot'].sum(axis=1)
#         P_mda = self.P.public.fp.mda
#         trim_maj['DA'] = trim_mda(info_ind, self.name, P_mda)*(trim_cotises>0)
#         trim_maj['5eme'] = nb_trim_bonif_5eme(trim_cotises)*(trim_cotises>0)
#         to_other['RG'] = {'trimesters': {'cot_FP' : trim_to_RG}, 'wages': {'sal_FP' : sal_to_RG}}
#         output = {'trimesters': trimesters, 'wages': wages, 'maj': trim_maj}
#         return output, to_other

    ### get_trimester_wages
    def trim_cot_by_year_regime(self, data):
        trim_valide, sal_regime = trim_cot_by_year_FP(data, self.code_regime)
        return trim_valide, sal_regime
    
    def FP_to_RG(self, data, trim_cot_by_year_regime):
        trim_to_RG, sal_to_RG = self.select_to_RG(data, trim_cot_by_year_regime[0].copy(), trim_cot_by_year_regime[1].copy())
        return trim_to_RG, sal_to_RG

    def wages(self, trim_cot_by_year_regime, FP_to_RG):
        return trim_cot_by_year_regime[1] - FP_to_RG[1]
    
    def trimesters(self, trim_cot_by_year_regime, FP_to_RG):
        # TODO: est-ce qu'on ne devrait pas vérifier que l'on a bien que des éléments positifs ou nuls ? 
        return trim_cot_by_year_regime[0] - FP_to_RG[0]
    
    def nb_trimesters(self, trimesters):
        return trimesters.sum(axis=1)
    
    def trim_maj_mda_ini(self, info_ind, nb_trimesters):
        P_mda = self.P.public.fp.mda
        return trim_mda(info_ind, self.name, P_mda)*(nb_trimesters > 0)   
    
    def trim_maj_mda_RG(self, regime='RG'):
        pass
    
    def trim_maj_mda_RSI(self, regime='RSI'):
        pass

    def trim_maj_mda(self, trim_maj_mda_ini, nb_trimesters, trim_maj_mda_RG, trim_maj_mda_RSI):
        ''' La Mda (attribuée par tous les régimes de base), ne peut être accordé par plus d'un régime.
        Régle d'attribution : a cotisé au régime + si polypensionnés -> ordre d'attribution : RG, RSI, FP
        Rq : Pas beau mais temporaire, pour comparaison Destinie'''
        if sum(trim_maj_mda_RG) + sum(trim_maj_mda_RSI) > 0: 
            return 0*trim_maj_mda_RG
        return trim_maj_mda_ini*(nb_trimesters > 0)   


    def trim_maj_5eme(self, nb_trimesters):
        return nb_trim_bonif_5eme(nb_trimesters)*(nb_trimesters>0)
 
    def trim_maj_ini(self, trim_maj_mda_ini, trim_maj_5eme):
        return trim_maj_mda_ini + trim_maj_5eme
    
    def trim_maj(self, trim_maj_mda, trim_maj_5eme):
        return trim_maj_mda + trim_maj_5eme
    
    ### coeff_proratisation
    def CP_5eme(self, nb_trimesters, trim_maj_5eme):
        N_CP = self.P.public.fp.plein.n_trim
        return minimum(divide(nb_trimesters + trim_maj_5eme, N_CP), 1)

    def CP_CPCM(self, nb_trimesters, trim_maj_mda_ini): # TODO: change to not ini ? 
        P = self.P.public.fp
        N_CP = P.plein.n_trim
        taux = P.plein.taux
        taux_bonif = P.taux_bonif
        return minimum(divide(maximum(nb_trimesters, N_CP) + trim_maj_mda_ini, N_CP), divide(taux_bonif, taux))    
    
    def coeff_proratisation_Destinie(self, nb_trimesters, trim_maj_mda_ini):  #TODO: should be trim maj ? 
        P = self.P.public.fp
        N_CP = P.plein.n_trim
        return minimum(divide(nb_trimesters + trim_maj_mda_ini, N_CP), 1)
        
    def coeff_proratisation(self, CP_5eme, CP_CPCM, coeff_proratisation_Destinie):  # TODO: remove coeff_proratisation_Destinie
        ''' on a le choix entre deux bonifications,
                chacune plafonnée à sa façon '''
        if compare_destinie == True:
            return coeff_proratisation_Destinie
        return maximum(CP_5eme, CP_CPCM)

    def age_min_retirement(self, data):
        P = self.P.public.fp
        trim_actif, _ = trim_cot_by_year_FP(data, self.code_actif)
        trim_actif = trim_actif.sum(axis=1)
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
        trim_cot = trim_by_year.sum(axis=1)
        last_fp = data.workstate.last_time_in(self.code_regime)
        to_RG_actif = (3*trim_cot < P.actif.N_min)*(last_fp == self.code_actif)
        to_RG_sedentaire = (3*trim_cot < P.sedentaire.N_min)*(last_fp == self.code_sedentaire)
        to_RG = (to_RG_actif + to_RG_sedentaire)
        trim_by_year[~to_RG,:] = 0
        sal_by_year[~to_RG,:] = 0
        return trim_by_year, sal_by_year


    def age_annulation_decote(self, data, age_min_retirement):
        ''' Détermination de l'âge d'annulation de la décote '''
        P = reduce(getattr, self.param_name.split('.'), self.P)

        if P.decote.taux == 0:
            # le dispositif n'existe pas encore
            return age_min_retirement
        else:
            age_max = self._build_age_max(data)
            age_annul = maximum(age_max - P.decote.age_null,0)
            age_annul[age_annul == 0] = 999
            return age_annul

    def trim_decote(self, data, trimesters_tot, trim_maj_enf_tot):
        ''' Détermination de la décote à appliquer aux pensions '''
        P = reduce(getattr, self.param_name.split('.'), self.P)
        if P.decote.nb_trim_max !=0:
            agem = data.info_ind['agem']
            trim_decote = nb_trim_decote(trimesters_tot, trim_maj_enf_tot, agem, P)
            return trim_decote
        else:
            return zeros(data.info_ind.shape[0])
    

    def surcote(self, data, trimesters, trimesters_tot, trim_maj_tot, date_start_surcote):
        ''' Détermination de la surcote à appliquer aux pensions '''
        P = reduce(getattr, self.param_name.split('.'), self.P)
        P_long = reduce(getattr, self.param_name.split('.'), self.P_longit)
        taux_surcote = P.surcote.taux
        plafond = P.surcote.nb_trim_max
        selected_date = P_long.surcote.dates
        trim_surcote = nb_trim_surcote(trimesters, selected_date, date_start_surcote)
        trim_surcote = minimum(trim_surcote, plafond)
        return taux_surcote*trim_surcote


    def salref(self, data):
        last_fp_idx = data.workstate.idx_last_time_in(self.code_regime)
        last_fp = zeros(data.sali.shape[0])
        last_fp[last_fp_idx[0]] = data.sali[last_fp_idx]
        taux_prime = array(data.info_ind['tauxprime'])
        P_long = reduce(getattr, self.param_name.split('.'), self.P_longit)
        P = reduce(getattr, self.param_name.split('.'), self.P)
        val_point = P_long.val_point
        val_point_last_fp = zeros(data.sali.shape[0])
        val_point_last_fp[last_fp_idx[0]] = array([val_point[date_last] for date_last in last_fp_idx[1]])
        val_point_t = P.val_point
        coeff_revalo = val_point_t/val_point_last_fp
        coeff_revalo[coeff_revalo== inf] = 0
        return last_fp*coeff_revalo/(1 + taux_prime)


    def plafond_pension(self, pension_brute, salref, cp, surcote):
        return pension_brute

    def minimum_pension(self, trim_regime, pension):
        return 0*pension
