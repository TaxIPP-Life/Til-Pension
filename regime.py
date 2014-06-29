# -*- coding: utf-8 -*-
import logging as log

from datetime import date
from numpy import maximum, array, nan_to_num, greater, divide, around, zeros, minimum, multiply
from pandas import Series, DataFrame
from time_array import TimeArray
from datetil import DateTil

first_year_sal = 1949
compare_destinie = True 

        
class Regime(object):
    """
    A Simulation class tailored to compute pensions (deal with survey data )
    """
    descr = None
     
    def __init__(self):
        self.code_regime = None
        self.name = None
        self.param_name = None
    
        self.dates = None     
        self.time_step = None
        self.data_type = None
        self.dateleg = None
        
        self.P = None
        self.P_longit = None
        
    def set_config(self, **kwargs):
        """
        Configures the Regime
        """
        # Setting general attributes and getting the specific ones
        for key, val in kwargs.iteritems():
            if hasattr(self, key):
                setattr(self, key, val)
        if 'dateleg' in kwargs.keys():
            date = DateTil(kwargs['dateleg'])
            self.dateleg = date

    def surcote(self, data, trim_wage_regime, trim_wage_all):
        trimesters = trim_wage_all['trimesters']
        trim_maj = trim_wage_all['maj']
        agem = data.info_ind['agem']
        trim_by_year_tot = trimesters['tot']
        trim_maj = trim_maj['tot']
        age_start_surcote = self._age_min_retirement(data)
        date_start_surcote = self._date_start_surcote(trim_by_year_tot, trim_maj, agem, age_start_surcote)   
        return self._calculate_surcote(trim_wage_regime, trim_wage_all, date_start_surcote, agem)
    
    def _calculate_surcote(self, trimesters, date_start_surcote, age):
        #TODO: remove trim_by_year_tot from arguments
        raise NotImplementedError
    
    def _date_start_surcote(self, trim_by_year_tot, trim_maj, agem, age_start_surcote):
        ''' Détermine la date individuelle a partir de laquelle on atteint la surcote
        (a atteint l'âge légal de départ en retraite + côtisé le nombre de trimestres cible)
        Rq : pour l'instant on pourrait ne renvoyer que l'année'''
        
        #TODO: do something better with datesim
        datesim = self.dateleg.liam
        P = reduce(getattr, self.param_name.split('.'), self.P)
        if P.surcote.exist == 0:
            # Si pas de dispositif de surcote
            return [2100*100 + 1]*len(trim_maj)
        else:
            # 1. Construction de la matrice des booléens indiquant si l'année est surcotée selon critère trimestres
            n_trim = array(P.plein.n_trim)
            cumul_trim = trim_by_year_tot.array.cumsum(axis=1)
            trim_limit = array((n_trim - nan_to_num(trim_maj)))
            years_surcote_trim = greater(cumul_trim.T,trim_limit).T
            nb_years = years_surcote_trim.shape[1]
            
            # 2. Construction de la matrice des booléens indiquant si l'année est surcotée selon critère âge
            age_by_year = array([array(agem) - 12*i for i in reversed(range(nb_years))])
            years_surcote_age =  greater(age_by_year, array(age_start_surcote)).T
            
            # 3. Décompte du nombre d'années répondant aux deux critères
            years_surcote = years_surcote_trim*years_surcote_age
            nb_years_surcote = years_surcote.sum(axis=1)
            start_surcote = [datesim - nb_years*100 
                             if nb_years > 0 else 2100*100 + 1
                             for nb_years in nb_years_surcote]

            return start_surcote

    
    def date_start_taux_plein(self, data, trim_wage_all):
        ''' Détermine la date individuelle a partir de laquelle on atteint le taux plein
        condition date_surcote ou si atteint l'âge du taux plein
        Rq : pour l'instant on pourrait ne renvoyer que l'année'''
        agem = data.info_ind['agem']
        datesim = self.dateleg.liam
        age_taux_plein = self.age_annulation_decote(data)
        
        trim_by_year = trim_wage_all['trimesters']['tot']
        trim_maj = trim_wage_all['maj']['tot']
        # Condition sur l'âge -> automatique si on atteint l'âge du taux plein
        start_taux_plein_age = [ int(datesim - months//12*100 - months%12)
                                if months> 0 else 2100*100 + 1 
                                for months in (agem - age_taux_plein.replace(0,999)) ]
        # Condition sur les trimestres -> même que celle pour la surcote 
        age_start_surcote = self._age_min_retirement(data)
        start_taux_plein_trim = self._date_start_surcote(trim_by_year, trim_maj, agem, age_start_surcote)
        return minimum(start_taux_plein_age, start_taux_plein_trim)
    
    def calculate_taux(self, decote, surcote):
        ''' Détérmination du taux de liquidation à appliquer à la pension 
            La formule générale est taux pondéré par (1+surcote-decote)
            _surcote and _decote are called
            _date_start_surcote is a general method helping surcote
            '''
        
        P = reduce(getattr, self.param_name.split('.'), self.P)
        return P.plein.taux*(1 - decote + surcote)
    
    def calculate_coeff_proratisation(self):
        raise NotImplementedError
            
    def calculate_salref(self):
#         self.sal_regime = sali.array*_isin(self.workstate.array,self.code_regime)
        raise NotImplementedError

    def bonif_pension(self, data, trim_wage_reg, trim_wage_all, pension_reg, pension_all):
        pension = pension_reg + self.minimum_pension(trim_wage_reg, trim_wage_all, pension_reg, pension_all)
        # Remarque : la majoration de pension s'applique à la pension rapportée au maximum ou au minimum
        pension += self.majoration_pension(data, pension)
        pension = self.minimum_pension(trim_wage_reg, trim_wage_all, pension_reg, pension_all)
        return pension

class RegimeBase(Regime):
    

    def revenu_valides(self, workstate, sali, code=None): #sali, 
        ''' Cette fonction pertmet de calculer des nombres par trimesters
        TODO: gérer la comptabilisation des temps partiels quand variable présente'''
        assert isinstance(workstate, TimeArray)
        #assert isinstance(sali, TimeArray)
        if code is None:
            code = self.code_regime
        wk_selection = workstate.isin(self.code_regime)
        wk_selection.translate_frequency(output_frequency='month', inplace=True)
        #TODO: condition not assuming sali is in year
        sali.translate_frequency(output_frequency='month', inplace=True)
        sali.array = around(divide(sali.array, 12), decimals=3)
        trim = divide(wk_selection.array.sum(axis=1), 4).astype(int)
        return trim
    
    def get_trimester(self, workstate, sali):
        raise NotImplementedError
    
    def majoration_pension(self, data, pension):
        P = reduce(getattr, self.param_name.split('.'), self.P)
        nb_enf = data.info_ind['nb_enf']
        def _taux_enf(nb_enf, P):
            ''' Majoration pour avoir élevé trois enfants '''
            taux_3enf = P.maj_3enf.taux
            taux_supp = P.maj_3enf.taux_sup
            return taux_3enf*(nb_enf >= 3) + (taux_supp*maximum(nb_enf - 3, 0))
            
        maj_enf = _taux_enf(nb_enf, P)*pension
        return maj_enf
    
    def calculate_pension(self, data, trim_wage_regime, trim_wage_all, to_check=None):
        info_ind = data.info_ind
        name = self.name
        P = reduce(getattr, self.param_name.split('.'), self.P)
        trim_decote = self.trim_decote(data, trim_wage_all)
        decote = P.decote.taux*trim_decote
        surcote = self.surcote(data, trim_wage_regime, trim_wage_all)        
        taux = self.calculate_taux(decote, surcote)
        cp = self.calculate_coeff_proratisation(info_ind, trim_wage_regime, trim_wage_all)
        salref = self.calculate_salref(data, trim_wage_regime['wages'])
        
        pension_brute = cp*salref*taux
        pension = self.plafond_pension(pension_brute, salref, cp, surcote)
        # Remarque : la majoration de pension s'applique à la pension rapportée au maximum ou au minimum
        pension += self.majoration_pension(data, pension) # TODO: delete because in bonif_pension
        
        if to_check is not None:
            P = reduce(getattr, self.param_name.split('.'), self.P)
            taux_plein = P.plein.taux
            trimesters = trim_wage_regime['trimesters']
            trim_regime = trimesters['regime'].sum()
            to_check['decote_' + name] = taux_plein*decote*(trim_regime > 0)
            to_check['surcote_' + name] = taux_plein*surcote*(trim_regime > 0)
            to_check['CP_' + name] = cp*(trim_regime > 0)
            to_check['taux_' + name] = taux*(trim_regime>0)
            to_check['salref_' + name] = salref*(trim_regime>0)
            P = reduce(getattr, self.param_name.split('.'), self.P)
            to_check['n_trim_' + name] = P.plein.n_trim / 4
            if self.name == 'RG':
                to_check['N_CP_' + name] = P.prorat.n_trim / 4
        return pension.fillna(0), trim_decote

class RegimeComplementaires(Regime):
        
    def __init__(self):
        Regime.__init__(self)
        self.param_base = None
        
    def sali_for_regime(self, data):
        raise NotImplementedError
    
    def nombre_points(self, data):
        ''' Détermine le nombre de point à liquidation de la pension dans les régimes complémentaires (pour l'instant Ok pour ARRCO/AGIRC)
        Pour calculer ces points, il faut diviser la cotisation annuelle ouvrant des droits par le salaire de référence de l'année concernée 
        et multiplier par le taux d'acquisition des points'''
        sali_plaf = self.sali_for_regime(data)
        Plong_regime = getattr(self.P_longit.prive.complementaire,  self.name)
        salref = Plong_regime.sal_ref
        taux_cot = Plong_regime.taux_cot_moy
        assert len(salref) == sali_plaf.shape[1] == len(taux_cot)
        nb_points_by_year = zeros(sali_plaf.shape)
        for ix_year in range(sali_plaf.shape[1]):
            if salref[ix_year] > 0:
                nb_points_by_year[:,ix_year] = (taux_cot[ix_year].calc(sali_plaf[:,ix_year])/salref[ix_year])
        nb_points_by_year = nb_points_by_year.round(2)
        return nb_points_by_year
        
    def minimum_points(self, nb_points_by_year):
        ''' Application de la garantie minimum de points '''
        P = reduce(getattr, self.param_name.split('.'), self.P)
        gmp = P.gmp
        nb_points = maximum(nb_points_by_year, gmp)*(nb_points_by_year > 0)
        return nb_points.sum(1)
        
    def coefficient_age(self, agem, trim):
        ''' TODO: add surcote  pour avant 1955 '''
        P = reduce(getattr, self.param_name.split('.'), self.P)
        coef_mino = P.coef_mino
        age_annulation_decote = self.P.prive.RG.decote.age_null
        diff_age = divide(age_annulation_decote - agem, 12)*(age_annulation_decote > agem)
        coeff_min = Series(zeros(len(agem)), index=agem.index)
        for nb_annees, coef_mino in coef_mino._tranches:
            coeff_min += (diff_age == nb_annees)*coef_mino
        
        coeff_min += P.coeff_maj*diff_age    
        if P.cond_taux_plein == 1:
            # Dans ce cas, la minoration ne s'applique que si la durée de cotisation au régime général est inférieure à celle requise pour le taux plein
            n_trim = self.P.prive.RG.plein.n_trim
            coeff_min = coeff_min*(n_trim > trim) + (n_trim <= trim)
        return coeff_min
            
    def _majoration_enf(self, data, nb_points_by_year):
        ''' Application de la majoration pour enfants à charge. Deux types de majorations peuvent s'appliquer :
        ' pour enfant à charge au moment du départ en retraite
        - pour enfant nés et élevés en cours de carrière (majoration sur la totalité des droits acquis)
        C'est la plus avantageuse qui s'applique.'''
        P = reduce(getattr, self.param_name.split('.'), self.P)
        P_long = reduce(getattr, self.param_name.split('.'), self.P_longit).maj_enf
        nb_pac = array(data.info_ind['nb_pac'].copy())
        nb_born = array(data.info_ind['nb_enf'].copy())
        
        # 1- Calcul des points pour enfants à charge
        taux_pac = P.maj_enf.pac.taux
        points_pac = nb_points_by_year.sum(axis=1)*taux_pac*nb_pac
        
        # 2- Calcul des points pour enfants nés ou élevés
        points_born = zeros(len(nb_pac))
        nb_enf_maj =  zeros(len(nb_pac))
        for num_dispo in [0,1]:
            P_dispositif = getattr(P.maj_enf.born, 'dispositif' + str(num_dispo))
            selected_dates = getattr(P_long.born, 'dispositif' + str(num_dispo)).dates
            taux_dispositif = P_dispositif.taux
            nb_enf_min = P_dispositif.nb_enf_min
            nb_points_dates = multiply(nb_points_by_year,selected_dates).sum(1)
            nb_points_enf = nb_points_dates*taux_dispositif*(nb_born >= nb_enf_min)
            if hasattr(P_dispositif, 'taux_maj'):
                taux_maj = P_dispositif.taux_maj
                plaf_nb = P_dispositif.nb_enf_count
                nb_enf_maj = maximum(minimum(nb_born, plaf_nb) - nb_enf_min, 0)
                nb_points_enf += nb_enf_maj*taux_maj*nb_points_dates
                
            points_born += nb_points_enf
        # Retourne la situation la plus avantageuse
        val_point = P.val_point
        if compare_destinie:
            val_point = P.val_point_proj
        if compare_destinie:
            return points_born*val_point
        return maximum(points_born, points_pac)*val_point
    
    def majoration_pension(self, data, nb_points_by_year):
        maj_enf = self._majoration_enf(data, nb_points_by_year)
        return maj_enf
    
    def calculate_pension(self, data, trim_base, trim_wage_all, trim_decote_base, to_check=None):
        info_ind = data.info_ind
        name = self.name
        P = reduce(getattr, self.param_name.split('.'), self.P)
        nb_points_by_year = self.nombre_points(data)
        nb_points = nb_points_by_year.sum(axis=1)
        coeff_age = self.coefficient_age(info_ind['agem'], trim_base)
        val_point = P.val_point
        if compare_destinie:
            val_point = P.val_point_proj
        pension = self.minimum_points(nb_points_by_year)*val_point 
        P = reduce(getattr, self.param_name.split('.'), self.P)
        decote = trim_decote_base*P.taux_decote
        pension = pension + self.majoration_pension(data, nb_points_by_year)   
        pension = (1-decote)*pension
        if to_check is not None:
            to_check['nb_points_' + name] = nb_points
            to_check['coeff_age_' + name] = coeff_age
        return pension*coeff_age
