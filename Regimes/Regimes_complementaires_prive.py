# -*- coding:utf-8 -*-
import numpy as np
import os

parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0,parentdir) 

from SimulPension import PensionSimulation
from time_array import TimeArray
from utils_pension import build_long_values

first_year_sal = 1949

class AGIRC(PensionSimulation):
    ''' L'Association générale des institutions de retraite des cadres gère le régime de retraite des cadres du secteur privé 
    de l’industrie, du commerce, des services et de l’agriculture. '''
    
    def __init__(self, param_regime, param_common, param_longitudinal):
        PensionSimulation.__init__(self)
        self.regime = 'agirc'
        self.code_regime = [4]
        
        self._P = param_regime
        self._Pcom = param_common
        self._Plongitudinal = param_longitudinal

        self.info_ind = None
        self.info_child_mother = None
        self.info_child_father = None
        
        
    def majoration_enf(self, nb_points, coeff_age, agem):
        ''' Application de la majoration pour enfants à charge. Deux types de majorations peuvent s'appliquer :
        ' pour enfant à charge au moment du départ en retraite
        - pour enfant nés et élevés en cours de carrière (majoration sur la totalité des droits acquis)
        C'est la plus avantageuse qui s'applique.'''
        P = self._P.complementaire.arrco
        
        # Calcul des points pour enfants à charge
        taux_pac = P.maj_enf.pac
        nb_pac = self.info_ind['nb_pac']
        points_pac = nb_points*taux_pac*nb_pac
        
        # Calcul des points pour enfants nés ou élevés
        taux_born = P.maj_enf.born
        taux_born11 = P.maj_enf.born11
        nb_born = self.info_ind['nb_born']
        nb_points_11 = coeff_age*self.nombre_points(last_year = 2011)
        nb_points12_ = coeff_age*self.nombre_points(first_year = 2012) 
        points_born_11 = nb_points_11*(nb_born)*taux_born11
        points_born12_ = nb_points12_*taux_born
        points_born = (points_born_11 + points_born12_)*(nb_born >= 3)
        
        # Comparaison de la situation la plus avantageuse
        val_point = P.val_point
        majo_born = val_point*points_born
        majo_pac = val_point*points_pac
#        yearnaiss = self.datesim.year - np.divide(agem, 12)
#        if yearnaiss <= 1951:
#            plafond = P.maj_enf.plaf_pac
#            majo_pac = np.minimum(majo_pac, plafond)
        return np.maximum(majo_born, majo_pac)

class ARRCO(PensionSimulation):
    ''' L'association pour le régime de retraite complémentaire des salariés gère le régime de retraite complémentaire de l’ensemble 
    des salariés du secteur privé de l’industrie, du commerce, des services et de l’agriculture, cadres compris. '''
    def __init__(self, param_regime, param_common, param_longitudinal):
        PensionSimulation.__init__(self)
        self.regime = 'arrco'
        self.code_regime = [3,4]
        self.code_noncadre = 3
        self.code_cadre = 4
        
        self._P = param_regime
        self._Pcom = param_common
        self._Plongitudinal = param_longitudinal
        
        self.info_child_mother = None
        self.info_child_father = None
        self.sal_regime = None
        
    def build_sal_regime(self):
        ''' Cette fonction plafonne les salaires des cadres 1 pss pour qu'il ne paye que la première tranche '''
        sal_regime = self.sali.copy()
        workstate = self.workstate.copy()
        cadre_selection = (workstate.array == self.code_cadre)
        noncadre_selection = (workstate.array == self.code_noncadre)
        yearsim = self.datesim.year
        plaf_ss = self._Plongitudinal.common.plaf_ss
        pss = build_long_values(plaf_ss, first_year=first_year_sal, last_year=yearsim)    
        sal_regime.array = sal_regime.array*noncadre_selection + np.minimum(sal_regime.array, pss)*cadre_selection
        self.sal_regime = sal_regime
        
    def majoration_enf(self, nb_points, agem):
        ''' Application de la majoration pour enfants à charge. Deux types de majorations peuvent s'appliquer :
        ' pour enfant à charge au moment du départ en retraite
        - pour enfant nés et élevés en cours de carrière (majoration sur la totalité des droits acquis)
        C'est la plus avantageuse qui s'applique.'''
        P = self._P.complementaire.arrco
        
        # Calcul des points pour enfants à charge
        taux_pac = P.maj_enf.pac
        nb_pac = self.info_ind['nb_pac']
        points_pac = nb_points*taux_pac*(nb_pac)
        
        # Calcul des points pour enfants nés ou élevés
        taux_born11 = P.maj_enf.born11
        taux_born = P.maj_enf.born
        nb_born = self.info_ind['nb_born']
        nb_points_98 = self.nombre_points(last_year = 1998)
        nb_points9911 = self.nombre_points(first_year = 1999, last_year = 2011) 
        nb_points12_ = self.nombre_points(first_year = 2012) 
        points_born = ((nb_points_98 + nb_points9911)*taux_born11  + nb_points12_*taux_born)*(nb_born >= 3)
        
        # Comparaison de la situation la plus avantageuse
        val_point = P.val_point
        majo_born = val_point*points_born
        majo_pac = val_point*points_pac
        yearnaiss = self.datesim.year - np.divide(agem,12)
        if self.datesim.year >= 2013:
            plafond = P.maj_enf.plaf_pac
            majo_pac = np.minimum(majo_pac[(yearnaiss <= 1951)], plafond)
        return np.maximum(majo_born, majo_pac)