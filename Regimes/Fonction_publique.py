# -*- coding:utf-8 -*-
import math
import numpy as np

from datetime import datetime
from dateutil.relativedelta import relativedelta

import os
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0,parentdir) 
from regime import RegimeBase
from utils_pension import _isin, build_long_values, sum_by_years, substract_months, translate_frequency, valbytranches, table_selected_dates
from pension_functions import calculate_SAM, sal_to_trimcot, unemployment_trimesters
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
        
        # age limite = age limite associée à la catégorie de l’emploi exercé en dernier lieu
        last_wk = workstate.array[:,-1]
        fp = _isin(last_wk, self.code_regime)
        actif = (last_wk == self.code_actif)
        sedentaire = fp*(1 - actif)
        age_max_s = valbytranches(P.sedentaire.age_max, self.info_ind)
        age_max_a = valbytranches(P.actif.age_max, self.info_ind)
        age_max = actif*age_max_a + sedentaire*age_max_s
        P.age_max_vec = age_max