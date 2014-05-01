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
from pension_functions import calculate_SAM, nb_trim_surcote, sal_to_trimcot, unemployment_trimesters, workstate_selection, nb_pac, nb_born

first_year_sal = 1949

class AGIRC(PensionSimulation):
    ''' L'Association générale des institutions de retraite des cadres gère le régime de retraite des cadres du secteur privé 
    de l’industrie, du commerce, des services et de l’agriculture. '''
    
    def __init__(self, workstate_table, sal_RG, param_regime, param_common, param_longitudinal):
        PensionSimulation.__init__(self)
        self.regime = 'agirc'
        self.code_regime = [4]
        self._P = param_regime
        self._Pcom = param_common
        self._Plongitudinal = param_longitudinal
        self.workstate  = workstate_table
        self.sal_regime = sal_RG
        self.first_year = first_year_sal
        self.info_ind = None
        self.info_child_mother = None
        self.info_child_father = None
        self.first_year = first_year_sal
        
    def majoration_enf(self, nb_points, coeff_age, agem):
        ''' Application de la majoration pour enfants à charge. Deux types de majorations peuvent s'appliquer :
        ' pour enfant à charge au moment du départ en retraite
        - pour enfant nés et élevés en cours de carrière (majoration sur la totalité des droits acquis)
        C'est la plus avantageuse qui s'applique.'''
        P = self._P.complementaire.arrco
        
        # Calcul des points pour enfants à charge
        taux_pac = P.maj_enf.pac
        nb_pac_mother = nb_pac(self.info_child_mother, nb_points.index)
        nb_pac_father = nb_pac(self.info_child_father, nb_points.index)
        points_pac = nb_points * taux_pac * (nb_pac_mother + nb_pac_father)
        
        # Calcul des points pour enfants nés ou élevés
        taux_born = P.maj_enf.born
        taux_born11 = P.maj_enf.born11
        nb_born_mother = nb_born(self.info_child_mother, nb_points.index)
        nb_born_father = nb_born(self.info_child_father, nb_points.index)
        nb_points_11 = coeff_age * self.nombre_points(last_year = 2011)
        nb_points12_ = coeff_age * self.nombre_points(first_year = 2012) 
        points_born_11 = nb_points_11 * (nb_born_mother + nb_born_father) * taux_born11
        points_born12_ =  nb_points12_ * taux_born
        points_born = (points_born_11 + points_born12_) * (nb_born_mother + nb_born_father >= 3)
        
        # Comparaison de la situation la plus avantageuse
        val_point = P.val_point
        majo_born = val_point * points_born
        majo_pac = val_point * points_pac
        yearnaiss = self.datesim.year - np.divide(agem,12)
#        if yearnaiss <= 1951:
#            plafond = P.maj_enf.plaf_pac
#            majo_pac = np.minimum(majo_pac, plafond)
        return np.maximum(majo_born, majo_pac)

class ARRCO(PensionSimulation):
    ''' L'association pour le régime de retraite complémentaire des salariés gère le régime de retraite complémentaire de l’ensemble 
    des salariés du secteur privé de l’industrie, du commerce, des services et de l’agriculture, cadres compris. '''
    def __init__(self, workstate_table, sal_RG, param_regime, param_common, param_longitudinal):
        PensionSimulation.__init__(self)
        self.regime = 'arrco'
        self.code_regime = [3,4]
        self.code_noncadre = 3
        self.code_cadre = 4
        self._P = param_regime
        self._Pcom = param_common
        self._Plongitudinal = param_longitudinal
        self.workstate  = workstate_table
        self.sal_regime = sal_RG
        self.info_ind = None
        self.info_child_mother = None
        self.info_child_father = None
        self.first_year = first_year_sal
        
    def build_sal_regime(self):
        ''' Cette fonction plafonne les salaires des cadres 1 pss pour qu'il ne paye que la première tranche '''
        sali = self.sal_regime
        cadre_selection = (self.workstate == self.code_cadre)
        noncadre_selection = (self.workstate == self.code_noncadre)
        yearsim = self.datesim.year
        
        plaf_ss = self._Plongitudinal.common.plaf_ss
        pss = build_long_values(plaf_ss, first_year=first_year_sal, last_year=yearsim)    
        self.sal_regime = sali * noncadre_selection + np.minimum(sali, pss) * cadre_selection
        
    def majoration_enf(self, nb_points, agem):
        ''' Application de la majoration pour enfants à charge. Deux types de majorations peuvent s'appliquer :
        ' pour enfant à charge au moment du départ en retraite
        - pour enfant nés et élevés en cours de carrière (majoration sur la totalité des droits acquis)
        C'est la plus avantageuse qui s'applique.'''
        P = self._P.complementaire.arrco
        
        # Calcul des points pour enfants à charge
        taux_pac = P.maj_enf.pac
        nb_pac_mother = nb_pac(self.info_child_mother, nb_points.index)
        nb_pac_father = nb_pac(self.info_child_father, nb_points.index)
        points_pac = nb_points * taux_pac * (nb_pac_mother + nb_pac_father)
        
        # Calcul des points pour enfants nés ou élevés
        taux_born11 = P.maj_enf.born11
        taux_born = P.maj_enf.born
        nb_born_mother = nb_born(self.info_child_mother, nb_points.index)
        nb_born_father = nb_born(self.info_child_father, nb_points.index)
        nb_points_98 = self.nombre_points(last_year = 1998)
        nb_points9911 = self.nombre_points(first_year = 1999, last_year = 2011) 
        nb_points12_ = self.nombre_points(first_year = 2012) 
        points_born = ((nb_points_98 + nb_points9911) * taux_born11  + nb_points12_ * taux_born) * (nb_born_mother + nb_born_father >= 3)
        
        # Comparaison de la situation la plus avantageuse
        val_point = P.val_point
        majo_born = val_point * points_born
        majo_pac = val_point * points_pac
        yearnaiss = self.datesim.year - np.divide(agem,12)
        if self.datesim.year >= 2013:
            plafond = P.maj_enf.plaf_pac
            majo_pac = np.minimum(majo_pac[(yearnaiss <= 1951)], plafond)
            print majo_pac
            #pd.Series(np.zeros(len(index)), index=index)
        return np.maximum(majo_born, majo_pac)