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

    def get_trimesters_wages(self, workstate, sali, info_ind, to_check):
        trimesters = dict()
        wages = dict()
        
        trim_valide = self.trim_cot_by_year(workstate)
        trim_to_RG = self.trim_to_RG(workstate, sali, trim_valide)
        sal_regime = self.sali_in_regime(workstate, sali)
        sal_to_RG = self.sali_to_RG(workstate, sali, trim_to_RG)
        trimesters['cot_FP'] = trim_valide.substract(trim_to_RG)
        trimesters['cot_from_public_to_RG'] = trim_to_RG
        wages['cot_FP'] = sal_regime.substract(sal_to_RG)
        wages['from_public_to_RG'] = sal_to_RG
        trimesters['maj_FP'] = self.trim_bonif_CPCM(info_ind, trim_valide.sum()) + self.trim_bonif_5eme(trim_valide.sum())
        if to_check :
            to_check['DA_FP'] = (trimesters['cot_FP'].sum()) // 4 #+ trimesters['maj_FP']) //4
        return trimesters, wages
        
    def _age_min_retirement(self, workstate):
        P = self.P.public.fp
        trim_actif = self.trim_cot_by_year(workstate, self.code_actif).array.sum(1)
        # age_min = age_min_actif pour les fonctionnaires actif en fin de carrières ou carrière mixte ayant une durée de service actif suffisante
        age_min_s = P.sedentaire.age_min
        age_min_a = P.actif.age_min
        age_min = age_min_a*(trim_actif >= P.actif.N_min) + age_min_s*(trim_actif < P.actif.N_min)
        return age_min
    
    def _build_age_max(self, workstate, sali):
        P = self.P.public.fp
        last_fp = self._traitement(workstate, sali)
        actif = (last_fp == self.code_actif)
        sedentaire = (1 - actif)*(last_fp != 0)
        age_max_s = P.sedentaire.age_max
        age_max_a = P.actif.age_max
        age_max = actif*age_max_a + sedentaire*age_max_s
        return age_max

    def _traitement(self, workstate, sali, option='workstate'):
        ''' Détermine le workstate lors de la dernière cotisation au régime FP pour lui associer sa catégorie 
        output (option=workstate): 0 = non-fonctionnaire, 6 = fonc. sédentaire, 5 = fonc.actif (cf, construction de age_max)
        output (option=sali) : 0 si non-fonctionnaire, dernier salaire annuel sinon'''
        workstate = workstate.copy()
        wk_selection = workstate.isin(self.code_regime).array*workstate.array

        len_dates = wk_selection.shape[1]
        nrows = wk_selection.shape[0]
        output = zeros(nrows)
        for date in reversed(range(len_dates)):
            cond = wk_selection[:,date] != 0
            cond = cond & (output == 0)
            output[cond] = date
            
#             # some ideas to faster the calculation
#         len_dates = wk_selection.shape[1]
#         output = wk_selection.argmax(axis=1) 
#         obvious_case1 = (wk_selection.max(axis=1) == 0) | (wk_selection.max(axis=1) == min(self.code_regime)) #on a directement la valeur 
                                                                                                            # et avec argmac l'indice
#         obvious_case2 = wk_selection[:,-1] != 0 # on sait que c'est le dernier
#         output[obvious_case2] = len_dates - 1 #-1 because it's the index of last column
#         
#         not_yet_selected = (~obvious_case1) & (~obvious_case2)
#         output[not_yet_selected] = -1 # si on réduit, on va peut-être plus vite
#         subset = wk_selection[not_yet_selected,:-1] #we know from obvious case2 condition that there are zero on last column
#         for date in reversed(range(len_dates-1)):
#             cond = subset[:,date] != 0
#             output[not_yet_selected[cond]] = date
        selected_output = output[output != 0]
        selected_rows = array(range(nrows))[output != 0]
        workstate.array[(selected_rows.tolist(), selected_output.tolist())]
        if option == 'sali':
            output[selected_rows.tolist()] = sali.array[(selected_rows.tolist(), selected_output.tolist())]
            return output
        else:
            output[selected_rows.tolist()] = workstate.array[(selected_rows.tolist(), selected_output.tolist())]
            return output
    
             
    def trim_to_RG(self, workstate, sali, trim_by_year):
        ''' Détermine le nombre de trimestres par année à rapporter au régime général
        output : trim_by_year_FP_to_RG '''
        P = reduce(getattr, self.param_name.split('.'), self.P)
        # N_min donné en mois
        trim_cot = trim_by_year.array.sum(1)
        last_fp = self._traitement(workstate, sali)
        to_RG_actif = (trim_cot*3 < P.actif.N_min)*(last_fp == self.code_actif)
        to_RG_sedentaire = (trim_cot*3 < P.sedentaire.N_min)*(last_fp == self.code_sedentaire)
        to_RG = (to_RG_actif + to_RG_sedentaire)
        workstate_array = transpose(trim_by_year.array.T*to_RG.T)
        return TimeArray(workstate_array, trim_by_year.dates)

    def sali_to_RG(self, workstate, sali, trim_by_year):
        ''' renvoie la table des salaires (même time_step que sali) qui basculent du RG à la FP 
        output: sali_FP_to_RG
        TODO: Gérer les redondances avec la fonction précédente'''
        P = reduce(getattr, self.param_name.split('.'), self.P)
        # N_min donné en mois
        trim_cot = trim_by_year.array.sum(1)
        last_fp = self._traitement(workstate, sali)
        to_RG_actif = (trim_cot*3 < P.actif.N_min)*(last_fp == self.code_actif)*(trim_cot>0)
        to_RG_sedentaire = (trim_cot*3 < P.sedentaire.N_min)*(last_fp == self.code_sedentaire)*(trim_cot>0)
        to_RG = (to_RG_actif + to_RG_sedentaire)
        sali_array = transpose((workstate.isin(self.code_regime).array*sali.array).T*to_RG.T)
        return TimeArray(sali_array, sali.dates)
        
    def trim_bonif_CPCM(self, info_ind, trim_cot):
        # TODO: autres bonifs : déportés politiques, campagnes militaires, services aériens, dépaysement 
        info_child = info_ind.loc[info_ind['sexe'] == 1, 'nb_born'] #Majoration attribuée aux mères uniquement
        bonif_enf = Series(0, index = info_ind.index)
        bonif_enf[info_child.index.values] = 4*info_child.values
        return array(bonif_enf*(trim_cot>0)) #+...
    
    def trim_bonif_5eme(self, trim_cot):
        # TODO: Add bonification au cinquième pour les superactifs (policiers, surveillants pénitentiaires, contrôleurs aériens... à identifier grâce à workstate)
        super_actif = 0 # condition superactif à définir
        taux_5eme = 0.2
        bonif_5eme = minimum(trim_cot*taux_5eme, 5*4)
        return array(bonif_5eme*super_actif)
    
    def calculate_coeff_proratisation(self, info_ind, trimesters):
        P = self.P.public.fp
        taux = P.plein.taux
        taux_bonif = P.taux_bonif
        N_CP = P.plein.N_taux
        trim_regime = trimesters['by_year_regime'].sum(1) +  trimesters['maj']
        trim_bonif_5eme = self.trim_bonif_5eme(trim_regime)
        CP_5eme = minimum(divide(trim_regime + trim_bonif_5eme, N_CP), 1)
        trim_bonif_CPCM = self.trim_bonif_CPCM(info_ind, trim_regime)
        CP_CPCM = minimum(divide(maximum(trim_regime, N_CP) + trim_bonif_CPCM, N_CP), divide(taux_bonif, taux))
        return maximum(CP_5eme, CP_CPCM)

    def _decote(self, trim_tot, agem):
        ''' Détermination de la décote à appliquer aux pensions '''
        yearsim = self.yearsim
        if yearsim < 2006:
            return agem*0
        else:
            P = reduce(getattr, self.param_name.split('.'), self.P)
            try:
                tx_decote = P.decote.taux
                age_annulation = P.decote.age_null
            except:
                import pdb
                pdb.set_trace()
            N_taux = P.plein.N_taux
            trim_decote_age = divide(age_annulation - agem, 3)
            trim_decote_cot = N_taux - trim_tot
            assert len(trim_decote_age) == len(trim_decote_cot)
            trim_decote = maximum(0, minimum(trim_decote_age, trim_decote_cot))
        return trim_decote*tx_decote
        
    def _calculate_surcote(self, trimesters, date_start_surcote, age):
        ''' Détermination de la surcote à appliquer aux pensions '''
        yearsim = self.yearsim
        if yearsim < 2004:
            return age*0
        else:
            P = reduce(getattr, self.param_name.split('.'), self.P)
            taux_surcote = P.surcote.taux
            nb_trim = nb_trim_surcote(trimesters['by_year_regime'], date_start_surcote)
            return taux_surcote*nb_trim

    def calculate_salref(self, workstate, sali, regime):
        return self._traitement(workstate, sali, option='sali')
    
    def plafond_pension(self, pension_brute, salref, cp, surcote):
        return pension_brute