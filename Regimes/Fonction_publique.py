# -*- coding:utf-8 -*-


import os
import numpy as np
import pandas as pd
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0,parentdir) 


from regime import RegimeBase
from utils_pension import valbytranches

code_avpf = 8
code_chomage = 5
compare_destinie = True 


class FonctionPublique(RegimeBase):
    
    def __init__(self):
        RegimeBase.__init__(self)
        self.regime = 'FP'
        self.code_regime = [5,6]
        self.param_name = 'fp'
        
        self.code_sedentaire = 6
        self.code_actif = 5

    def get_trimester(self, workstate, sali):
        output = {}
        output['trim_FP'] = self.nb_trim_valide(workstate)
        output['actif_FP'] = self.nb_trim_valide(workstate, self.code_actif)
        return output
 
    def build_age_ref(self, trim_actif, workstate):
        P = getattr(self.P, self.param_name)
        # age_min = age_min_actif pour les fonctionnaires actif en fin de carrières ou carrière mixte ayant une durée de service actif suffisante
        age_min_s = valbytranches(P.sedentaire.age_min, self.info_ind)
        age_min_a = valbytranches(P.actif.age_min, self.info_ind)
        age_min = age_min_a*(trim_actif >= P.actif.N_min) + age_min_s*(trim_actif < P.actif.N_min)
        P.age_min_vec = age_min


    def categorie(self):
        ''' Détermine le workstate lors de la dernière cotisation au régime FP pour lui associer sa catégorie 
        output : 0 = non-fonctionnaire, 1 = fonc. sédentaire, 2 = fonc.actif'''
        # TODO: Create selection() in TimeArray with non_zeros
        wk_selection = self.workstate.isin(self.code_regime)[0]*self.workstate.array.copy()
        #self.categorie = categorie
             
    def cot_to_RG(self, trim_service):
        ''' Détermine les cotisations à reporter au régime général '''
        P = self._P
        # N_min donné en mois
        to_RG_actif = (trim_service*3 < P.actif.N_min)
        to_RG_sedentaire = (trim_service*3 < P.sedentaire.N_min)
        
#     def build_age_ref(self, trim_actif):
#         P = self._P
#         # age_min = age_min_actif pour les fonctionnaires actif en fin de carrières ou carrière mixte ayant une durée de service actif suffisante
#         age_min_s = valbytranches(P.sedentaire.age_min, self.info_ind)
#         age_min_a = valbytranches(P.actif.age_min, self.info_ind)
#         age_min = age_min_a*(trim_actif >= P.actif.N_min) + age_min_s*(trim_actif < P.actif.N_min)
#         P.age_min_vec = age_min
#         
#         # age limite = age limite associée à la catégorie de l’emploi exercé en dernier lieu
#         last_wk = workstate.array[:,-1]
#         fp = _isin(last_wk, self.code_regime)
#         actif = (last_wk == self.code_actif)
#         sedentaire = fp*(1 - actif)
#         age_max_s = valbytranches(P.sedentaire.age_max, self.info_ind)
#         age_max_a = valbytranches(P.actif.age_max, self.info_ind)
#         age_max = actif*age_max_a + sedentaire*age_max_s
#         P.age_max_vec = age_max
#         self._P.age_max_vec = age_max # je suis complétement contre ça
        
    def trim_bonif_CPCM(self, trim_service):
        # TODO: autres bonifs : déportés politiques, campagnes militaires, services aériens, dépaysement 
        info_child = self.info_ind.loc[self.info_ind['sexe'] == 1, 'nb_born'] #Majoration attribuée aux mères uniquement
        bonif_enf = pd.Series(0, index = self.info_ind.index)
        bonif_enf[info_child.index.values] = 4*info_child.values
        return bonif_enf*(trim_service>0) #+...
    
    def trim_bonif_5eme(self, trim_service):
        # TODO: Add bonification au cinquième pour les superactifs (policiers, surveillants pénitentiaires, contrôleurs aériens... à identifier grâce à workstate)
        super_actif = 0 # condition superactif à définir
        taux_5eme = 0.2
        bonif_5eme = np.minimum(trim_service*taux_5eme, 5*4)
        return bonif_5eme*super_actif
    
    def CP(self, trim_service, trim_bonif_CPCM, trim_bonif_5eme):
        taux = self._P.plein.taux
        taux_bonif =  self._P.taux_bonif
        N_CP = valbytranches(self._P.plein.N_taux, self.info_ind) 
        CP_5eme = np.minimum(np.divide(trim_service + trim_bonif_5eme, N_CP), 1)
        CP_CPCM = np.minimum(np.divide(np.maximum(trim_service, N_CP) + trim_bonif_CPCM, N_CP), np.divide(taux_bonif, taux))
        return np.maximum(CP_5eme, CP_CPCM)
        