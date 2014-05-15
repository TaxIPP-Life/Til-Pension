# -*- coding:utf-8 -*-
import math
import numpy as np
import pandas as pd
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
        
        trim_service_by_year = self.nb_trim_valide(code=self.code_regime, table=True)
        trim_service = self.nb_trim_valide(code=self.code_regime, table=False)
        trim_actif = self.nb_trim_valide(code=self.code_actif, table=False)
        self.trim_by_year = trim_service_by_year
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