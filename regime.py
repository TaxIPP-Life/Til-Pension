# -*- coding: utf-8 -*-
from datetime import date
from numpy import maximum, array, nan_to_num, greater, divide, around, zeros, minimum
from pandas import Series
from time_array import TimeArray
from datetil import DateTil
from utils_pension import build_long_values, build_long_baremes
first_year_sal = 1949
compare_destinie = True 

        
class Regime(object):
    """
    A Simulation class tailored to compute pensions (deal with survey data )
    """
    descr = None
     
    def __init__(self):
        self.code_regime = None
        self.regime = None
        self.param_name = None
    
        self.dates = None     
        self.time_step = None
        self.data_type = None
        self.first_year = None
        self.dateleg = None
        self.index = None
        
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

    def decote(self):
        raise NotImplementedError

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
        n_trim = array(P.plein.n_trim)
        cumul_trim = trim_by_year_tot.array.cumsum(axis=1)
        trim_limit = array((n_trim - nan_to_num(trim_maj)))
        years_surcote_trim = greater(cumul_trim.T,trim_limit)
        nb_years_surcote_trim = years_surcote_trim.sum(axis=0)
        start_surcote = [int(datesim - year_surcote*100)
                            if month_trim > 0 else 2100*100 + 1
                            for year_surcote, month_trim in zip(nb_years_surcote_trim, agem - age_start_surcote)]
        return start_surcote

    
    def _date_start_taux_plein(self, trim_by_year_tot, trim_maj, agem):
        ''' Détermine la date individuelle a partir de laquelle on atteint le taux plein
        condition date_surcote ou si atteint l'âge du taux plein
        Rq : pour l'instant on pourrait ne renvoyer que l'année'''
        datesim = self.dateleg.liam
        P = reduce(getattr, self.param_name.split('.'), self.P)
        age_taux_plein = P.decote.age_null
        
        # Condition sur l'âge -> automatique si on atteint l'âge du taux plein
        start_taux_plein_age = [ int(datesim - months//12*100 - months%12)
                                if months> 0 else 2100*100 + 1
                                for months in (agem - age_taux_plein) ]
        # Condition sur les trimestres -> même que celle pour la surcote
        start_taux_plein_trim = self._date_start_surcote(trim_by_year_tot, trim_maj, agem)
        return minimum(start_taux_plein_age, start_taux_plein_trim)
    
#     def sali_in_regime(self, workstate, sali):
#         ''' Cette fonction renvoie le TimeArray ne contenant que les salaires validés avec workstate == code_regime'''
#         wk_selection = workstate.isin(self.code_regime).array
#         return TimeArray(wk_selection*sali.array, sali.dates, 'sal_regime')
    
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
    
    def calculate_pension(self, data, trim_wage_regime, trim_wage_all, to_check=None):
        info_ind = data.info_ind
        reg = self.regime
        decote = self.decote(data, trim_wage_all)
        surcote = self.surcote(data, trim_wage_regime, trim_wage_all)        
        taux = self.calculate_taux(decote, surcote)
        cp = self.calculate_coeff_proratisation(info_ind, trim_wage_regime, trim_wage_all)
        salref = self.calculate_salref(data, trim_wage_regime['wages'])
        pension_brute = cp*salref*taux
        pension = self.plafond_pension(pension_brute, salref, cp, surcote)
        if to_check is not None:
            trimesters = trim_wage_regime['trimesters']
            trim_regime = trimesters['regime'].sum()
            to_check['decote_' + self.regime] = decote*(trim_regime > 0)
            to_check['surcote_' + self.regime] = surcote*(trim_regime > 0)
            to_check['CP_' + reg] = cp
            to_check['taux_' + reg] = taux*(trim_regime>0)
            to_check['salref_' + reg] = salref
            P = reduce(getattr, self.param_name.split('.'), self.P)
            to_check['n_trim_' + reg] = P.plein.n_trim // 4
            try:
                to_check['N_CP_' + reg] = P.N_CP // 4
            except:
                pass
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
        sal_selection = TimeArray(wk_selection.array*sali.array, sali.dates)
        trim = divide(wk_selection.array.sum(axis=1), 4).astype(int)
        return trim
    
    def get_trimester(self, workstate, sali):
        raise NotImplementedError
    

class RegimeComplementaires(Regime):
        
    def sali_for_regime(self, data):
        raise NotImplementedError
    
    def nombre_points(self, data, first_year=first_year_sal, last_year=None):
        ''' Détermine le nombre de point à liquidation de la pension dans les régimes complémentaires (pour l'instant Ok pour ARRCO/AGIRC)
        Pour calculer ces points, il faut diviser la cotisation annuelle ouvrant des droits par le salaire de référence de l'année concernée 
        et multiplier par le taux d'acquisition des points'''
        workstate = data.workstate
        sali = data.sali
        
        yearsim = data.datesim.year
        last_year_sali = yearsim - 1
        sali_plaf = self.sali_for_regime(data)
        if last_year == None:
            last_year = last_year_sali
        regime = self.regime
        P = reduce(getattr, self.param_name.split('.'), self.P)
        Plong = self.P_longit.prive.complementaire.__dict__[regime]
        salref = build_long_values(Plong.sal_ref, first_year=first_year_sal, last_year=yearsim)
        plaf_ss = self.P_longit.common.plaf_ss
        pss = build_long_values(plaf_ss, first_year=first_year_sal, last_year=yearsim)    
        taux_cot = build_long_baremes(Plong.taux_cot_moy, first_year=first_year_sal, last_year=yearsim, scale=pss)
        assert len(salref) == sali_plaf.shape[1] == len(taux_cot)
        nb_points = zeros(sali_plaf.shape[0])
        if last_year_sali < first_year:
            return nb_points
        for year in range(first_year, min(last_year_sali, last_year) + 1):
            ix_year = year - first_year
            points_acquis = divide(taux_cot[year].calc(sali_plaf[:,ix_year]), salref[year-first_year_sal]).round(2) 
            gmp = P.gmp
            #print year, taux_cot[year], sali.ix[1926 ,year *100 + 1], salref[year-first_year_sal]
            #print 'result', Series(points_acquis, index=sali.index).ix[1926]
            nb_points += maximum(points_acquis, gmp)*(points_acquis > 0)
        return nb_points
 
    def coefficient_age(self, agem, trim):
        ''' TODO: add surcote  pour avant 1955 '''
        yearleg = self.dateleg.year
        P = reduce(getattr, self.param_name.split('.'), self.P)
        coef_mino = P.coef_mino
        age_annulation_decote = self.P.prive.RG.decote.age_null
        n_trim = self.P.prive.RG.plein.n_trim
        diff_age = maximum(divide(age_annulation_decote - agem, 12), 0)
        coeff_min = Series(zeros(len(agem)), index=agem.index)
        coeff_maj = Series(zeros(len(agem)), index=agem.index)
        for nb_annees, coef_mino in coef_mino._tranches:
            coeff_min += (diff_age == nb_annees)*coef_mino
        if yearleg <= 1955:
            maj_age = maximum(divide(agem - age_annulation_decote, 12), 0)
            coeff_maj = maj_age*0.05
            return coeff_min + coeff_maj
        elif yearleg < 1983:
            return coeff_min
        elif yearleg >= 1983:
            # A partir de cette date, la minoration ne s'applique que si la durée de cotisation au régime général est inférieure à celle requise pour le taux plein
            return  coeff_min*(n_trim > trim) + (n_trim <= trim)        
    
    def majoration_enf(self):     
        raise NotImplementedError
    
    def calculate_pension(self, data, trim_base, to_check=None):
        workstate = data.workstate
        sali = data.sali
        info_ind = data.info_ind
        
        reg = self.regime
        P = reduce(getattr, self.param_name.split('.'), self.P)
        val_arrco = P.val_point 
        nb_points = self.nombre_points(data)
        coeff_age = self.coefficient_age(info_ind['agem'], trim_base)
        maj_enf = self.majoration_enf(data, nb_points, coeff_age)
        
        if to_check is not None:
            to_check['nb_points_' + reg] = nb_points
            to_check['coeff_age_' + reg] = coeff_age
            to_check['maj_' + reg] = maj_enf
        return val_arrco*nb_points*coeff_age + maj_enf