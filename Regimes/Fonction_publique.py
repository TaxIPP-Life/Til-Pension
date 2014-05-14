# -*- coding:utf-8 -*-
import math
import numpy as np

from datetime import datetime
from dateutil.relativedelta import relativedelta

import os
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0,parentdir) 
from time_array import TimeArray
from SimulPension import PensionSimulation
from utils_pension import _isin, build_long_values, sum_by_years, substract_months, translate_frequency, valbytranches, table_selected_dates
from pension_functions import calculate_SAM, sal_to_trimcot, unemployment_trimesters
code_avpf = 8
code_chomage = 5
first_year_sal = 1949
compare_destinie = True 


class FonctionPublique(PensionSimulation):
    
    def __init__(self):
        PensionSimulation.__init__(self)
        self.regime = 'FP'
        self.code_regime = [5,6]
        self.param_name = 'fp'
        
        self.code_sedentaire = 6
        self.code_actif = 5
        

        
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
        wk_selection = TimeArray(_isin(self.workstate.array, self.code_regime), self.workstate.dates)
        wk_selection.array, wk_selection.dates = translate_frequency(wk_selection, input_frequency=self.time_step, output_frequency='month')
        wk_selection_actif = TimeArray(_isin(self.workstate.array,self.code_actif), self.workstate.dates)
        wk_selection_actif.array, wk_selection_actif.dates = translate_frequency(wk_selection_actif, input_frequency=self.time_step, output_frequency='month')
        # TODO: condition not assuming sali is in year
        sali = TimeArray(*translate_frequency(self.sali, input_frequency=self.time_step, output_frequency='month'))
        sali.array = np.around(np.divide(sali.array, 12), decimals=3)
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