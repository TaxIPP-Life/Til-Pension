# -*- coding:utf-8 -*-
import math
from datetime import datetime

import os
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0,parentdir) 
from time_array import TimeArray

from numpy import maximum, minimum, array, divide, zeros, multiply, ceil
from pandas import DataFrame

from regime import compare_destinie
from Regime_general import RegimeGeneral
from utils_pension import build_long_values, build_salref_bareme, _info_numpy, print_multi_info_numpy
from pension_functions import nb_trim_surcote, unemployment_trimesters

code_avpf = 8
code_chomage = 2
code_preretraite = 9
first_year_indep = 1972

class RegimeSocialIndependants(RegimeGeneral):
    
    def __init__(self):
        RegimeGeneral.__init__(self)
        self.regime = 'RSI'
        self.code_regime = [7]
        self.param_name = 'prive.RG'
        self.param_indep = 'indep.rsi'

    def get_trimesters_wages(self, data, to_check=False):
        trimesters = dict()
        wages = dict()
        
        workstate = data.workstate
        sali = data.sali
        
        reduce_data = data.selected_dates(first=first_year_indep)
        nb_trim_cot = self.trim_cot_by_year(reduce_data)
        trimesters['cot_RSI']  = nb_trim_cot
        nb_trim_ass = self.trim_ass_by_year(reduce_data.workstate, nb_trim_cot)
        trimesters['ass_RSI'] = nb_trim_ass
        wages['regime_RSI'] = self.sali_in_regime(sali, workstate)
        return trimesters, wages
    

        
            