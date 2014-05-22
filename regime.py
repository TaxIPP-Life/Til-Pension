# -*- coding: utf-8 -*-

from numpy import maximum, minimum, array, nan_to_num, greater, divide, around, zeros
from pandas import Series
from time_array import TimeArray
from utils_pension import build_long_values, build_long_baremes, valbytranches
first_year_sal = 1949

class Regime(object):
    """
    A Simulation class tailored to compute pensions (deal with survey data )
    """
    descr = None
     
    def __init__(self):
        self.code_regime = None
        self.regime = None
        self.param_name = None
        
        self.info_ind = None
        self.dates = None
        
        self.time_step = None
        self.data_type = None
        self.first_year = None
        self.yearsim = None
        
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
                
    def _decote(self):
        raise NotImplementedError

    def _surcote(self, workstate, trim_by_year_tot, trim_maj, regime, age):
        datesim = 100*self.yearsim + 1
        age_start = self._age_start_surcote(workstate)
        date_start = self._date_taux_plein(trim_by_year_tot, trim_maj)
        date_start_surcote = [int(max(datesim - year_surcote*100, 
                                datesim - month_trim//12*100 - month_trim%12))
                        for year_surcote, month_trim in zip(date_start, age-age_start)]
        return self._calculate_surcote(self.yearsim, regime, date_start_surcote, age, trim_by_year_tot)
    
    def _calculate_surcote(self, yearsim, regime, date_start_surcote, age, trim_by_year_tot):
        #TODO: remove trim_by_year_tot from arguments
        raise NotImplementedError
    
    def _age_start_surcote(self, workstate):
        ''' retourne l'age à partir duquel les trimestres peuvent être 
             comptabilisés pour la surcote
             Note: ça a l'air simple en général, juste un paramètre mais
              pour la fonction publique il y a des grosses subtilités...
        '''
        raise NotImplementedError
    
    def _date_taux_plein(self, trim_by_year_tot, trim_maj):
        ''' Détermine la date individuelle a partir de laquelle il y a surcote 
        (a atteint l'âge légal de départ en retraite + côtisé le nombre de trimestres cible 
        Rq : pour l'instant on pourrait ne renvoyer que l'année'''
        
        P = reduce(getattr, self.param_name.split('.'), self.P)
        N_taux = valbytranches(P.plein.N_taux, self.info_ind)
        
        cumul_trim = trim_by_year_tot.array.cumsum(axis=1)
        trim_limit = array((N_taux - nan_to_num(trim_maj)))
        years_surcote = greater(cumul_trim.T,trim_limit)
        nb_years_surcote = years_surcote.sum(axis=0)
        return nb_years_surcote
       
    def calculate_taux(self, workstate, trim_by_year_tot, trim_maj_tot, regime, to_check=None):
        ''' Détérmination du taux de liquidation à appliquer à la pension 
            La formule générale est taux pondéré par (1+surcote-decote)
            _surcote and _decote are called
            _date_start_surcote is a general method helping surcote
            '''
        P = reduce(getattr, self.param_name.split('.'), self.P)
        trim_tot = trim_by_year_tot.array.sum(1)
        taux_plein = P.plein.taux
        agem = self.info_ind['agem']
        decote = self._decote(trim_tot, agem)
#         date_start_surcote = self._date_start_surcote(trim_by_year_tot, trim_maj_tot, agem)
        surcote = self._surcote(workstate, trim_by_year_tot, trim_maj_tot, regime, agem)
        if to_check is not None:
            to_check['taux_plein_' + self.regime] = taux_plein*(trim_tot > 0)
            to_check['decote_' + self.regime] = decote*(trim_tot > 0)*(trim_tot > 0)
            to_check['surcote_' + self.regime] = surcote*(trim_tot > 0)*(trim_tot > 0)
        return taux_plein*(1 - decote + surcote)
    
    def calculate_coeff_proratisation(self):
        raise NotImplementedError
            
    def calculate_salref(self):
#         self.sal_regime = sali.array*_isin(self.workstate.array,self.code_regime)
        raise NotImplementedError
    
    def calculate_pension(self, workstate, sali, trim_by_year_tot, trim_maj_tot, regime, to_check=None):
        reg = self.regime
        taux = self.calculate_taux(workstate, trim_by_year_tot, trim_maj_tot, regime, to_check)
        cp = self.calculate_coeff_proratisation(regime)
        salref = self.calculate_salref(workstate, sali, regime)
        if to_check is not None:
            to_check['CP_' + reg] = cp
            to_check['taux_' + reg] = taux*(regime['trim_tot']>0)
            to_check['salref_' + reg] = salref
        return cp*salref*taux


class RegimeBase(Regime):

    def nb_trim_valide(self, workstate, code=None, table=False): #sali,
        ''' Cette fonction pertmet de calculer des nombres par trimestres validés dans un régime
        validation au sein du régime = 'workstate' = code
        TODO: gérer la comptabilisation des temps partiels quand variable présente'''
        assert isinstance(workstate, TimeArray)
        if code is None:
            code = self.code_regime
        trim_service = workstate.isin(code)
        frequency_init = trim_service.frequency
        trim_service.translate_frequency(output_frequency='year', method='sum', inplace=True)
        if frequency_init == 'year':
            #from year to trimester
            trim_service.array = trim_service.array*4
        if frequency_init == 'month':
            #from month to trimester
            trim_service.array = divide(trim_service.array,3)
        self.trim_by_year = trim_service
        if table == True:
            return trim_service
        else:
            return trim_service.array.sum(1)

    def revenu_valides(self, workstate, sali, code=None): #sali, 
        ''' Cette fonction pertmet de calculer des nombres par trimestres
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
        
    def sali_for_regime(self, workstate, sali):
        raise NotImplementedError
    
    def nombre_points(self, workstate, sali, first_year=first_year_sal, last_year=None):
        ''' Détermine le nombre de point à liquidation de la pension dans les régimes complémentaires (pour l'instant Ok pour ARRCO/AGIRC)
        Pour calculer ces points, il faut diviser la cotisation annuelle ouvrant des droits par le salaire de référence de l'année concernée 
        et multiplier par le taux d'acquisition des points'''
        yearsim = self.yearsim
        last_year_sali = yearsim - 1
        sali_plaf = self.sali_for_regime(workstate, sali)
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
        P = reduce(getattr, self.param_name.split('.'), self.P)
        coef_mino = P.coef_mino
        age_annulation_decote = valbytranches(self.P.prive.RG.decote.age_null, self.info_ind) #TODO: change the param place
        N_taux = valbytranches(self.P.prive.RG.plein.N_taux, self.info_ind) #TODO: change the param place
        diff_age = maximum(divide(age_annulation_decote - agem, 12), 0)
        coeff_min = Series(zeros(len(agem)), index=agem.index)
        coeff_maj = Series(zeros(len(agem)), index=agem.index)
        for nb_annees, coef_mino in coef_mino._tranches:
            coeff_min += (diff_age == nb_annees)*coef_mino
        if self.yearsim <= 1955:
            maj_age = maximum(divide(agem - age_annulation_decote, 12), 0)
            coeff_maj = maj_age*0.05
            return coeff_min + coeff_maj
        elif  self.yearsim < 1983:
            return coeff_min
        elif self.yearsim >= 1983:
            # A partir de cette date, la minoration ne s'applique que si la durée de cotisation au régime général est inférieure à celle requise pour le taux plein
            return  coeff_min*(N_taux > trim) + (N_taux <= trim)        
    
    def majoration_enf(self):     
        raise NotImplementedError
    
    def calculate_pension(self, workstate, sali, trim_base, to_check=None):
        reg = self.regime
        P = reduce(getattr, self.param_name.split('.'), self.P)
        val_arrco = P.val_point 
        agem = self.info_ind['agem']
        nb_points = self.nombre_points(workstate, sali)
        coeff_age = self.coefficient_age(agem, trim_base)
        maj_enf = self.majoration_enf(workstate, sali, nb_points, coeff_age, agem)
        
        if to_check is not None:
            to_check['nb_points_' + reg] = nb_points
            to_check['coeff_age_' + reg] = coeff_age
            to_check['maj_' + reg] = maj_enf
        return val_arrco * nb_points * coeff_age + maj_enf