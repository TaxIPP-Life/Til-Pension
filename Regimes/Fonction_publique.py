# -*- coding:utf-8 -*-
import math
import numpy as np

import os
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0,parentdir) 
from time_array import TimeArray
from SimulPension import PensionSimulation
from utils_pension import _isin, build_long_values, valbytranches, table_selected_dates
from pension_functions import calculate_SAM, sal_to_trimcot, unemployment_trimesters
code_avpf = 8
code_chomage = 5
first_year_sal = 1949
compare_destinie = True 


class FonctionPublique(PensionSimulation):
    
    def __init__(self, param_regime, param_common, param_longitudinal):
        PensionSimulation.__init__(self)
        self.regime = 'FP'
        self.code_regime = [5,6]
        self.code_sedentaire = 6
        self.code_actif = 5
        
        self._P = param_regime
        self._Pcom = param_common
        self._Plongitudinal = param_longitudinal
        
        self.workstate  = None
        self.sali = None
        self.info_ind = None
        self.info_child_mother = None
        self.info_child_father = None
        self.time_step = None
        self.format_table = 'numpy' #format des tables 'sali' et 'workstate'
        
    def trim_service(self):
        ''' Cette fonction pertmet de calculer la durée de service dans FP
        TODO: gérer la comptabilisation des temps partiels quand variable présente'''
        wk_selection = self.workstate._isin(self.code_regime)
        wk_selection.translate_frequency(output_frequency='month', inplace=True)
        wk_selection_actif = self.workstate._isin(self.code_actif)
        wk_selection_actif.translate_frequency(output_frequency='month')
        # TODO: condition not assuming sali is in year
        sali = self.sali
        sali.translate_frequency(output_frequency='month', inplace=True, method='divide')
        sal_selection = TimeArray(wk_selection.array*sali.array, sali.dates) 
        trim_service = np.divide(wk_selection.array.sum(axis=1), 4).astype(int)
        trim_actif = np.divide(wk_selection_actif.array.sum(axis=1), 4).astype(int)
        self.sal_FP = sal_selection
        return trim_service, trim_actif
 
    def build_age_ref(self, trim_actif):
        P = self._P
        # age_min = age_min_actif pour les fonctionnaires actif en fin de carrières ou carrière mixte ayant une durée de service actif suffisante
        age_min_s = valbytranches(P.sedentaire.age_min, self.info_ind)
        age_min_a = valbytranches(P.actif.age_min, self.info_ind)
        age_min = age_min_a*(trim_actif >= P.actif.N_min) + age_min_s*(trim_actif < P.actif.N_min)
        self._P.age_min_vec = age_min
        
        # age limite = age limite associée à la catégorie de l’emploi exercé en dernier lieu
        last_wk = self.workstate.array[:,-1]
        fp = _isin(last_wk, self.code_regime)
        actif = (last_wk == self.code_actif)
        sedentaire = fp*(1 - actif)
        age_max_s = valbytranches(P.sedentaire.age_max, self.info_ind)
        age_max_a = valbytranches(P.actif.age_max, self.info_ind)
        age_max = actif*age_max_a + sedentaire*age_max_s
        self._P.age_max_vec = age_max