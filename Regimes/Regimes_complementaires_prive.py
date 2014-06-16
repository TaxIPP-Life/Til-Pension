# -*- coding:utf-8 -*-
import os

parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0,parentdir) 

from numpy import maximum, minimum, divide
from regime import RegimeComplementaires, compare_destinie


class AGIRC(RegimeComplementaires):
    ''' L'Association générale des institutions de retraite des cadres gère le régime de retraite des cadres du secteur privé 
    de l’industrie, du commerce, des services et de l’agriculture. '''
    
    def __init__(self):
        RegimeComplementaires.__init__(self)
        self.name = 'agirc'
        self.code_regime = [4]
        self.param_name = 'prive.complementaire.agirc'
        self.param_RG = 'prive.RG'
        self.code_cadre = 4
        
    def sali_for_regime(self, data):
        workstate = data.workstate
        sali = data.sali
        return sali.array*(workstate.isin(self.code_regime).array)
        
    def majoration_pension(self, data, nb_points, coeff_age):
        maj_enf = self._majoration_enf(data, nb_points, coeff_age)
        return maj_enf
        

class ARRCO(RegimeComplementaires):
    ''' L'association pour le régime de retraite complémentaire des salariés gère le régime de retraite complémentaire de l’ensemble 
    des salariés du secteur privé de l’industrie, du commerce, des services et de l’agriculture, cadres compris. '''
    def __init__(self):
        RegimeComplementaires.__init__(self)
        self.name = 'arrco'
        self.param_name = 'prive.complementaire.arrco'
        self.param_RG = 'prive.RG'
        self.code_regime = [3,4]
        self.code_noncadre = 3
        self.code_cadre = 4
        
    def sali_for_regime(self, data):
        '''plafonne le salaire des cadres à 1 pss pour qu'il ne pait que la prmeière tranche '''
        workstate = data.workstate
        sali = data.sali
        nb_pss=1
        cadre_selection = (workstate.array == self.code_cadre)
        noncadre_selection = (workstate.array == self.code_noncadre)
        sali = sali.array
        plaf_ss = self.P_longit.common.plaf_ss
        plaf_sali = minimum(sali, nb_pss*plaf_ss)
        return sali*noncadre_selection + plaf_sali*cadre_selection
        
    def majoration_pension(self, data, nb_points, coeff_age):
        P = reduce(getattr, self.param_name.split('.'), self.P)
        maj_enf = self._majoration_enf(data, nb_points, coeff_age)
        yearnaiss =  [date.year for date in data.info_ind['naiss']]
        if P.maj_enf.application_plaf == 1:
            plafond = P.maj_enf.plaf_pac
            majo_pac = minimum(maj_enf[(yearnaiss <= 1951)], plafond)
        return maj_enf