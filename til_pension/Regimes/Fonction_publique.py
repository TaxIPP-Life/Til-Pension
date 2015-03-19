# -*- coding:utf-8 -*-

import os
from numpy import array, maximum, minimum, divide, zeros, inf

from til_pension.regime import RegimeBase
from til_pension.trimesters_functions import nb_trim_surcote, nb_trim_decote, trim_cot_by_year_FP, nb_trim_bonif_5eme, trim_mda
from til_pension.regime import compare_destinie

class FonctionPublique(RegimeBase):

    def __init__(self):
        RegimeBase.__init__(self)
        self.name = 'FP'
        self.code_regime = [5,6]
        self.param_name = 'public.fp'

        self.code_sedentaire = 6
        self.code_actif = 5

    def get_trimesters_wages(self, data, unactive=[]):
        trimesters = dict()
        wages = dict()
        trim_maj = dict()
        to_other = dict()

        info_ind = data.info_ind

        trim_valide, sal_regime = trim_cot_by_year_FP(data, self.code_regime)
        trim_to_RG, sal_to_RG = self.select_to_RG(data, trim_valide.copy(), sal_regime)
        trimesters['cot'] = trim_valide - trim_to_RG
        wages['cot'] = sal_regime - sal_to_RG
        trim_cotises = trimesters['cot'].sum(axis=1)
        P_mda = self.P.public.fp.mda
        trim_maj['DA'] = trim_mda(info_ind, self.name, P_mda)*(trim_cotises>0)
        trim_maj['5eme'] = nb_trim_bonif_5eme(trim_cotises)*(trim_cotises>0)
        to_other['RG'] = {'trimesters': {'cot_FP' : trim_to_RG}, 'wages': {'sal_FP' : sal_to_RG}}
        if 'trim_mda' in unactive:
            print "MDA désactivée"
            trim_maj['DA'] = 0*trim_maj['DA']
        output = {'trimesters': trimesters, 'wages': wages, 'maj': trim_maj}
        return output, to_other

    def _age_min_retirement(self, data):
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

    def calculate_coeff_proratisation(self, info_ind, trim_wage_regime, trim_wage_all):
        ''' on a le choix entre deux bonifications,
                chacune plafonnée à sa façon 
                Voir réforme 2004 et 2010 pour non-prise en compte de la mda dans prorat'''
        P = self.P.public.fp
        trimesters = trim_wage_regime['trimesters']
        trim_maj = trim_wage_regime['maj']
        N_CP = P.plein.n_trim
        trim_regime = trimesters['regime'].sum(axis=1)
        trim_bonif_5eme = trim_maj['5eme']
        CP_5eme = minimum(divide(trim_regime + trim_bonif_5eme, N_CP), 1)

        taux = P.plein.taux
        taux_bonif = P.taux_bonif
        trim_bonif_CPCM = trim_maj['DA'] # CPCM
        CP_CPCM = minimum(divide(maximum(trim_regime, N_CP) + trim_bonif_CPCM, N_CP), divide(taux_bonif, taux))
        if compare_destinie == True:
            return minimum(divide(trim_regime + trim_bonif_CPCM, N_CP),1)
        return maximum(CP_5eme, CP_CPCM)

    def age_annulation_decote(self, data):
        ''' Détermination de l'âge d'annulation de la décote '''
        P = reduce(getattr, self.param_name.split('.'), self.P)

        if P.decote.taux == 0:
            # le dispositif n'existe pas encore
            return self._age_min_retirement(data)
        else:
            age_max = self._build_age_max(data)
            age_annul = maximum(age_max - P.decote.age_null,0)
            age_annul[age_annul == 0] = 999
            return age_annul

    def trim_decote(self, data, trim_wage_all):
        ''' Détermination de la décote à appliquer aux pensions '''
        trimesters = trim_wage_all['trimesters']
        trim_maj = trim_wage_all['maj']
        P = reduce(getattr, self.param_name.split('.'), self.P)
        if P.decote.nb_trim_max !=0:
            agem = data.info_ind['agem']
            trim_decote = nb_trim_decote(trimesters, trim_maj, agem, P)
            return trim_decote
        else:
            return zeros(data.info_ind.shape[0])

    def _calculate_surcote(self, trim_wage_regime, trim_wage_all, date_start_surcote, age):
        ''' Détermination de la surcote à appliquer aux pensions '''
        trimesters = trim_wage_regime['trimesters']
        P = reduce(getattr, self.param_name.split('.'), self.P)
        P_long = reduce(getattr, self.param_name.split('.'), self.P_longit)
        taux_surcote = P.surcote.taux
        plafond = P.surcote.nb_trim_max
        selected_date = P_long.surcote.dates
        trim_surcote = nb_trim_surcote(trimesters['regime'], selected_date, date_start_surcote)
        trim_surcote = minimum(trim_surcote, plafond)
        return taux_surcote*trim_surcote

    def calculate_salref(self, data, wages_regime = None):
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


    def plafond_pension(self, pension_brute, pension_surcote):
        return pension_brute

    def minimum_pension(self, trim_wages_reg, trim_wages_all, pension_reg, pension_all):
        return 0*pension_reg
    
    def cotisations(self, data):
        ''' Calcul des cotisations passées par année'''
        sali = data.sali*data.workstate.isin(self.code_regime).astype(int)
        Pcot_regime = reduce(getattr, self.param_name.split('.'), self.P_cot) #getattr(self.P_longit.prive.complementaire,  self.name)
        taux_prime = array(data.info_ind['tauxprime'])
        taux_pat = Pcot_regime.cot_pat
        taux_sal = Pcot_regime.cot_sal
        assert len(taux_pat) == sali.shape[1] == len(taux_sal)
        cot_sal_by_year = zeros(sali.shape)
        cot_pat_by_year = zeros(sali.shape)
        for ix_year in range(sali.shape[1]):
            cot_sal_by_year[:,ix_year] = taux_sal[ix_year]*sali[:,ix_year]/(1+taux_prime)
            cot_pat_by_year[:,ix_year] = taux_pat[ix_year]*sali[:,ix_year]/(1+taux_prime)
        return {'sal': cot_sal_by_year, 'pat':cot_pat_by_year}
