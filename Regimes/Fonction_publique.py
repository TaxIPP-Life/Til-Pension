# -*- coding:utf-8 -*-

from collections import defaultdict
import os
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0,parentdir) 

from numpy import maximum, minimum, array, nonzero, divide, transpose, zeros
from pandas import Series

from regime import RegimeBase
from pension_functions import nb_trim_surcote
from time_array import TimeArray
from utils_pension import valbytranches

code_avpf = 8
code_chomage = 5
compare_destinie = True 


class FonctionPublique(RegimeBase):
    
    def __init__(self):
        RegimeBase.__init__(self)
        self.regime = 'FP'
        self.code_regime = [5,6]
        self.param_name = 'public.fp'
        
        self.code_sedentaire = 6
        self.code_actif = 5

    def get_trimester(self, workstate, sali, to_check, table=True):
        output = dict()
        trim_valide = self.nb_trim_valide(workstate, table=True)
        trim_by_year_to_RG = self.trim_to_RG(workstate, sali, trim_valide)
        output['trim_by_year_FP_to_RG'] = trim_by_year_to_RG
        output['sali_FP_to_RG'] = self.sali_to_RG(workstate, sali, trim_by_year_to_RG)
        output['trim_cot_FP'] = trim_valide.array.sum(1)
        output['actif_FP'] = self.nb_trim_valide(workstate, self.code_actif)
        output['trim_maj_FP'] = self.trim_bonif_CPCM(output['trim_cot_FP']) + self.trim_bonif_5eme(output['trim_cot_FP'])
        self.trim_actif = output['actif_FP'] 
        if to_check :
            to_check['trim_cot_FP'] = output['trim_cot_FP']
        if table == True:
            return output, {'FP': trim_valide}
        else:
            return output
        
    def _build_age_min(self, workstate):
        P = self.P.public.fp
        trim_actif = self.nb_trim_valide(workstate, self.code_actif)
        # age_min = age_min_actif pour les fonctionnaires actif en fin de carrières ou carrière mixte ayant une durée de service actif suffisante
        age_min_s = valbytranches(P.sedentaire.age_min, self.info_ind)
        age_min_a = valbytranches(P.actif.age_min, self.info_ind)
        age_min = age_min_a*(trim_actif >= P.actif.N_min) + age_min_s*(trim_actif < P.actif.N_min)
        return age_min
    
    def _build_age_max(self, workstate, sali):
        P = self.P.public.fp
        last_fp = self._traitement(workstate, sali)
        actif = (last_fp == self.code_actif)
        sedentaire = (1 - actif)*(last_fp != 0)
        age_max_s = valbytranches(P.sedentaire.age_max, self.info_ind)
        age_max_a = valbytranches(P.actif.age_max, self.info_ind)
        age_max = actif*age_max_a + sedentaire*age_max_s
        return age_max

    def _traitement(self, workstate, sali, option='workstate'):
        ''' Détermine le workstate lors de la dernière cotisation au régime FP pour lui associer sa catégorie 
        output (option=workstate): 0 = non-fonctionnaire, 6 = fonc. sédentaire, 5 = fonc.actif (cf, construction de age_max)
        output (option=sali) : 0 si non-fonctionnaire, dernier salaire annuel sinon'''
        workstate = workstate.copy()
        wk_selection = workstate.isin(self.code_regime).array*workstate.array.copy()
        index_selection = zip(nonzero(wk_selection)[0], nonzero(wk_selection)[1])
        groups = defaultdict(list)
        dict_by_rows = dict()
        for obj in index_selection:
            groups[obj[0]].append(obj[1])
            dict_by_rows.update(groups)
        index_row = [id_row for id_row in dict_by_rows.keys()]
        index_col = [max(id_cols) for id_cols in dict_by_rows.values()]
        #index = [(id_row, max(id_cols)) for id_row, id_cols in dict_by_rows.iteritems()]
        output = zeros(workstate.array.shape[0])
        if option == 'sali':
            output[index_row] = sali.array[(index_row, index_col)]
            return output
        else:
            output[index_row] = workstate.array[(index_row, index_col)]
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
        
    def trim_bonif_CPCM(self, trim_cot):
        # TODO: autres bonifs : déportés politiques, campagnes militaires, services aériens, dépaysement 
        info_child = self.info_ind.loc[self.info_ind['sexe'] == 1, 'nb_born'] #Majoration attribuée aux mères uniquement
        bonif_enf = Series(0, index = self.info_ind.index)
        bonif_enf[info_child.index.values] = 4*info_child.values
        return array(bonif_enf*(trim_cot>0)) #+...
    
    def trim_bonif_5eme(self, trim_cot):
        # TODO: Add bonification au cinquième pour les superactifs (policiers, surveillants pénitentiaires, contrôleurs aériens... à identifier grâce à workstate)
        super_actif = 0 # condition superactif à définir
        taux_5eme = 0.2
        bonif_5eme = minimum(trim_cot*taux_5eme, 5*4)
        return array(bonif_5eme*super_actif)
    
    def calculate_coeff_proratisation(self, regime):
        P = self.P.public.fp
        taux = P.plein.taux
        taux_bonif = P.taux_bonif
        N_CP = valbytranches(P.plein.N_taux, self.info_ind) 
        trim_regime = regime['trim_tot']
        trim_bonif_5eme = self.trim_bonif_5eme(trim_regime)
        CP_5eme = minimum(divide(trim_regime + trim_bonif_5eme, N_CP), 1)
        trim_bonif_CPCM = self.trim_bonif_CPCM(trim_regime)
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
                tx_decote = valbytranches(P.decote.taux, self.info_ind)
                age_annulation = valbytranches(P.decote.age_null, self.info_ind)
            except:
                import pdb
                pdb.set_trace()
            N_taux = valbytranches(P.plein.N_taux, self.info_ind)
            trim_decote_age = divide(age_annulation - agem, 3)
            trim_decote_cot = N_taux - trim_tot
            assert len(trim_decote_age) == len(trim_decote_cot)
            trim_decote = maximum(0, minimum(trim_decote_age, trim_decote_cot))
        return trim_decote*tx_decote
        
    def _surcote(self, trim_by_year_tot, regime, agem, date_surcote):
        ''' Détermination de la surcote à appliquer aux pensions '''
        yearsim = self.yearsim
        if yearsim < 2004:
            return agem*0
        else:
            P = reduce(getattr, self.param_name.split('.'), self.P)
            taux_surcote = P.surcote.taux
            nb_trim = nb_trim_surcote(regime['trim_by_year'], date_surcote)
            return taux_surcote*nb_trim

    def calculate_salref(self, workstate, sali, regime):
        return self._traitement(workstate, sali, option='sali')