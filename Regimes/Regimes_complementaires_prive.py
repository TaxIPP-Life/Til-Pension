# -*- coding:utf-8 -*-
import os

parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0,parentdir) 

from numpy import maximum, minimum, divide
from regime import RegimeComplementaires


first_year_sal = 1949

class AGIRC(RegimeComplementaires):
    ''' L'Association générale des institutions de retraite des cadres gère le régime de retraite des cadres du secteur privé 
    de l’industrie, du commerce, des services et de l’agriculture. '''
    
    def __init__(self):
        RegimeComplementaires.__init__(self)
        self.regime = 'agirc'
        self.code_regime = [4]
        self.param_name = 'prive.complementaire.agirc'
        self.param_RG = 'prive.RG'
        self.code_cadre = 4
        self.info_ind = None
        self.info_child_mother = None
        self.info_child_father = None
        
    def plaf_sali(self, workstate, sali):
        return sali.array*(workstate.isin(self.code_regime).array)
        
    def majoration_enf(self, workstate, sali, nb_points, coeff_age, agem):
        ''' Application de la majoration pour enfants à charge. Deux types de majorations peuvent s'appliquer :
        ' pour enfant à charge au moment du départ en retraite
        - pour enfant nés et élevés en cours de carrière (majoration sur la totalité des droits acquis)
        C'est la plus avantageuse qui s'applique.'''
        P = reduce(getattr, self.param_name.split('.'), self.P)

        # Calcul des points pour enfants à charge
        taux_pac = P.maj_enf.pac
        nb_pac = self.info_ind['nb_pac']
        points_pac = nb_points*taux_pac*nb_pac
        
        # Calcul des points pour enfants nés ou élevés
        taux_born = P.maj_enf.born
        taux_born11 = P.maj_enf.born11
        nb_born = self.info_ind['nb_born']
        nb_points_11 = coeff_age*self.nombre_points(workstate, sali, last_year=2011)
        nb_points12_ = coeff_age*self.nombre_points(workstate, sali, first_year=2012) 
        points_born_11 = nb_points_11*(nb_born)*taux_born11
        points_born12_ = nb_points12_*taux_born
        points_born = (points_born_11 + points_born12_)*(nb_born >= 3)
        
        # Comparaison de la situation la plus avantageuse
        val_point = P.val_point
        majo_born = val_point*points_born
        majo_pac = val_point*points_pac
#        yearnaiss = self.datesim.year - divide(agem, 12)
#        if yearnaiss <= 1951:
#            plafond = P.maj_enf.plaf_pac
#            majo_pac = minimum(majo_pac, plafond)
        return maximum(majo_born, majo_pac)

class ARRCO(RegimeComplementaires):
    ''' L'association pour le régime de retraite complémentaire des salariés gère le régime de retraite complémentaire de l’ensemble 
    des salariés du secteur privé de l’industrie, du commerce, des services et de l’agriculture, cadres compris. '''
    def __init__(self):
        RegimeComplementaires.__init__(self)
        self.regime = 'arrco'
        self.param_name = 'prive.complementaire.arrco'
        self.param_RG = 'prive.RG'
        self.code_regime = [3,4]
        self.code_noncadre = 3
        self.code_cadre = 4
        
        self.info_child_mother = None
        self.info_child_father = None
        
    def plaf_sali(self, workstate, sali):
        '''plafonne le salaire des cadres à 1 pss pour qu'il ne pait que la prmeière tranche '''
        cadre_selection = (workstate.array == self.code_cadre)
        noncadre_selection = (workstate.array == self.code_noncadre)
        plaf_sali = self.plaf_sali_pss(sali) 
        return sali.array*noncadre_selection + plaf_sali*cadre_selection
        
    def majoration_enf(self, workstate, sali, nb_points, coeff_age, agem):
        ''' Application de la majoration pour enfants à charge. Deux types de majorations peuvent s'appliquer :
        - pour enfant à charge au moment du départ en retraite
        - pour enfant nés et élevés en cours de carrière (majoration sur la totalité des droits acquis)
        C'est la plus avantageuse qui s'applique.
        Rq : coeff age n'intervient pas effectivement dans cette fonction'''
        P = reduce(getattr, self.param_name.split('.'), self.P)

        # Calcul des points pour enfants à charge
        taux_pac = P.maj_enf.pac
        nb_pac = self.info_ind['nb_pac']
        points_pac = nb_points*taux_pac*(nb_pac)
        
        # Calcul des points pour enfants nés ou élevés
        taux_born11 = P.maj_enf.born11
        taux_born = P.maj_enf.born
        nb_born = self.info_ind['nb_born']
        nb_points_98 = self.nombre_points(workstate, sali, last_year=1998)
        nb_points9911 = self.nombre_points(workstate, sali, first_year=1999, last_year=2011) 
        nb_points12_ = self.nombre_points(workstate, sali, first_year=2012) 
        points_born = ((nb_points_98 + nb_points9911)*taux_born11  + nb_points12_*taux_born)*(nb_born >= 3)
        
        # Comparaison de la situation la plus avantageuse
        val_point = P.val_point
        majo_born = val_point*points_born
        majo_pac = val_point*points_pac
        yearnaiss = self.yearsim - divide(agem,12)
        if self.yearsim >= 2013:
            plafond = P.maj_enf.plaf_pac
            majo_pac = minimum(majo_pac[(yearnaiss <= 1951)], plafond)
        return maximum(majo_born, majo_pac)