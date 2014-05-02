# -*- coding:utf-8 -*-
import math
import numpy as np
import pandas as pd

from pandas import DataFrame
from datetime import datetime
from dateutil.relativedelta import relativedelta

import os
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0,parentdir) 
from SimulPension import PensionSimulation
from utils import years_to_months, months_to_years, substract_months, valbytranches, table_selected_dates, build_long_values
from pension_functions import calculate_SAM, nb_trim_surcote, sal_to_trimcot, unemployment_trimesters, translate_frequency

code_avpf = 8
code_chomage = 5
first_year_sal = 1949
compare_destinie = True 


class FonctionPublique(PensionSimulation):
    
    def __init__(self, param_regime, param_common, param_longitudinal):
        PensionSimulation.__init__(self)
        self.regime = 'FP'
        self.code_regime = [5,6]
        
        self._P = param_regime
        self._Pcom = param_common
        self._Plongitudinal = param_longitudinal
        
        self.workstate  = None
        self.sali = None
        self.info_ind = None
        self.info_child_mother = None
        self.info_child_father = None
        self.time_step = None

        
    def trim_service(self):
        ''' Cette fonction pertmet de calculer la durée de service dans FP
        TODO: gérer la comptabilisation des temps partiels quand variable présente'''
        wk_selection = self.workstate.isin(self.code_regime)
        wk_selection = translate_frequency(wk_selection, input_frequency=self.time_step, output_step='month')
        sal_selection = wk_selection * years_to_months(self.sali, division = True) 
        trim_service = np.divide(wk_selection.sum(axis=1), 4)
        self.sal_FP = sal_selection
        return trim_service
 
    