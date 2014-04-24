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
from utils import years_to_months, months_to_years, substract_months, valbytranches, table_selected_dates, build_long_values, build_long_baremes
from pension_functions import calculate_SAM, nb_trim_surcote, sal_to_trimcot, unemployment_trimesters, workstate_selection

first_year_sal = 1949

class AGIRC(PensionSimulation):
    ''' L'Association générale des institutions de retraite des cadres gère le régime de retraite des cadres du secteur privé 
    de l’industrie, du commerce, des services et de l’agriculture. '''
    
    def __init__(self, workstate_table, sal_RG, param_regime, param_common, param_longitudinal):
        PensionSimulation.__init__(self)
        self.regime = 'agirc'
        self.code_cadre = 4
        self._P = param_regime
        self._Pcom = param_common
        self._Plongitudinal = param_longitudinal
        self.workstate  = workstate_table
        self.sali = sal_RG
        self.first_year = first_year_sal

class ARRCO(PensionSimulation):
    ''' L'association pour le régime de retraite complémentaire des salariés gère le régime de retraite complémentaire de l’ensemble 
    des salariés du secteur privé de l’industrie, du commerce, des services et de l’agriculture, cadres compris. '''
    def __init__(self, workstate_table, sal_RG, param_regime, param_common, param_longitudinal):
        PensionSimulation.__init__(self)
        self.regime = 'arrco'
        self.code_noncadre = 3
        self._P = param_regime
        self._Pcom = param_common
        self._Plongitudinal = param_longitudinal
        self.workstate  = workstate_table
        self.sali = sal_RG
        self.info_ind = None
        self.info_child_mother = None
        self.info_child_father = None
        self.first_year = first_year_sal
