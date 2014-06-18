# -*- coding: utf-8 -*-
import logging as log

from datetime import date
from numpy import maximum, array, nan_to_num, greater, divide, around, zeros, minimum
from utils_compar import print_info
from pandas import Series
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
        self.logger = None
        
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
        if self.logger and 'surcote' in self.logger.keys():
            print_info(list_vectors=[date_start_surcote, age_start_surcote],
                                    list_timearrays=[data.sali, data.workstate], 
                                    all_ident=data.info_ind.index,
                                    loglevel=self.logger['surcote'],
                                    label='surcote_' + self.name)           
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
    def nb_trim_decote(self, trimesters, trim_maj, agem):
        ''' Cette fonction renvoie le vecteur numpy du nombre de trimestres décotés 
        Lorsque les deux règles (d'âge et de nombre de trimestres cibles) jouent
        -> Ref : Article L351-1-2 : les bonifications de durée de services et majorations de durée d'assurance,
        à l'exclusion de celles accordées au titre des enfants et du handicap, ne sont pas prises en compte 
        dans la durée d'assurance tous régimes confondus pour apprécier la décote.
        '''
        P = reduce(getattr, self.param_name.split('.'), self.P)
        age_annulation = array(P.decote.age_null)
        plafond = array(P.decote.nb_trim_max)
        n_trim = array(P.plein.n_trim)
        trim_decote_age = divide(age_annulation - agem, 3)
        
        trim_tot = trimesters['tot'].sum(1) + trim_maj['enf']
        trim_decote_cot = n_trim - trim_tot
        assert len(trim_decote_age) == len(trim_decote_cot)
        trim_plaf = minimum(minimum(trim_decote_age, trim_decote_cot), plafond)
        return array(trim_plaf*(trim_plaf>0))
    
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
        name = self.name
        decote = self.decote(data, trim_wage_all)
        surcote = self.surcote(data, trim_wage_regime, trim_wage_all)        
        taux = self.calculate_taux(decote, surcote)
        cp = self.calculate_coeff_proratisation(info_ind, trim_wage_regime, trim_wage_all)
        salref = self.calculate_salref(data, trim_wage_regime['wages'])
        
        pension_brute = cp*salref*taux
        pension = self.plafond_pension(pension_brute, salref, cp, surcote)
        pension += self.minimum_pension(trim_wage_regime, pension)
        # Remarque : la majoration de pension s'applique à la pension rapportée au maximum ou au minimum
        pension += self.majoration_pension(data, pension)
        
        if to_check is not None:
            P = reduce(getattr, self.param_name.split('.'), self.P)
            taux_plein = P.plein.taux
            trimesters = trim_wage_regime['trimesters']
            trim_regime = trimesters['regime'].sum()
            to_check['decote_' + name] = taux_plein*decote*(trim_regime > 0)
            to_check['surcote_' + name] = taux_plein*surcote*(trim_regime > 0)
            to_check['CP_' + name] = cp
            to_check['taux_' + name] = taux*(trim_regime>0)
            to_check['salref_' + name] = salref
            P = reduce(getattr, self.param_name.split('.'), self.P)
            to_check['n_trim_' + name] = P.plein.n_trim // 4
            if self.name == 'RG':
                to_check['N_CP_' + name] = P.prorat.n_trim // 4
        return pension.fillna(0)


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
    
    def majoration_pension(self, data, pension):
        P = reduce(getattr, self.param_name.split('.'), self.P)
        nb_enf = data.info_ind['nb_born']
        
        def _taux_enf(nb_enf, P):
            ''' Majoration pour avoir élevé trois enfants '''
            taux_3enf = P.maj_3enf.taux
            taux_supp = P.maj_3enf.taux_sup
            return taux_3enf*(nb_enf == 3) + taux_supp*maximum(nb_enf - 3, 0)
            
        maj_enf = _taux_enf(nb_enf, P)*pension
        return maj_enf

class RegimeComplementaires(Regime):
        
    def sali_for_regime(self, data):
        raise NotImplementedError
    
    def nombre_points(self, data, first_year=first_year_sal, last_year=None):
        ''' Détermine le nombre de point à liquidation de la pension dans les régimes complémentaires (pour l'instant Ok pour ARRCO/AGIRC)
        Pour calculer ces points, il faut diviser la cotisation annuelle ouvrant des droits par le salaire de référence de l'année concernée 
        et multiplier par le taux d'acquisition des points'''
        yearsim = data.last_date.year
        last_year_sali = yearsim - 1
        sali_plaf = self.sali_for_regime(data)
        if last_year == None:
            last_year = last_year_sali
        name = self.name
        P = reduce(getattr, self.param_name.split('.'), self.P)
        Plong_regime = getattr(self.P_longit.prive.complementaire, name)
        salref = Plong_regime.sal_ref
        taux_cot = Plong_regime.taux_cot_moy
        assert len(salref) == sali_plaf.shape[1] == len(taux_cot)
        nb_points = zeros(sali_plaf.shape[0])
        if last_year_sali < first_year:
            return nb_points
        for ix_year in range(min(last_year_sali, last_year) - first_year + 1):
            points_acquis = divide(taux_cot[ix_year].calc(sali_plaf[:,ix_year]), salref[ix_year]).round(2) 
            gmp = P.gmp
            #print year, taux_cot[year], sali.ix[1926 ,year *100 + 1], salref[year-first_year_sal]
            #print 'result', Series(points_acquis, index=sali.index).ix[1926]
            nb_points += maximum(points_acquis, gmp)*(points_acquis > 0)
        return nb_points
 
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
            
    def _majoration_enf(self, data, nb_points, coeff_age):
        ''' Application de la majoration pour enfants à charge. Deux types de majorations peuvent s'appliquer :
        ' pour enfant à charge au moment du départ en retraite
        - pour enfant nés et élevés en cours de carrière (majoration sur la totalité des droits acquis)
        C'est la plus avantageuse qui s'applique.'''
        P = reduce(getattr, self.param_name.split('.'), self.P)
        nb_pac = data.info_ind['nb_pac']
        nb_born = data.info_ind['nb_born']
        
        # Calcul des points pour enfants à charge
        taux_pac = P.maj_enf.pac
        points_pac = nb_points*taux_pac*nb_pac
        
        # Calcul des points pour enfants nés ou élevés
        taux_born = P.maj_enf.born
        taux_born11 = P.maj_enf.born11
        
        nb_points_11 = coeff_age*self.nombre_points(data, last_year=2011)
        nb_points12_ = coeff_age*self.nombre_points(data, first_year=2012) 
        points_born_11 = nb_points_11*(nb_born)*taux_born11
        points_born12_ = nb_points12_*taux_born
        points_born = (points_born_11 + points_born12_)*(nb_born >= 3)
        
        # Comparaison de la situation la plus avantageuse
        val_point = P.val_point
        majo_born = val_point*points_born
        majo_pac = val_point*points_pac

        return maximum(majo_born, majo_pac)
    
    def majoration_pension(self, data, nb_points, coeff_age):     
        raise NotImplementedError
    
    def calculate_pension(self, data, trim_base, to_check=None):
        workstate = data.workstate
        sali = data.sali
        info_ind = data.info_ind
        name = self.name
        P = reduce(getattr, self.param_name.split('.'), self.P)
        val_arrco = P.val_point 
        nb_points = self.nombre_points(data)
        coeff_age = self.coefficient_age(info_ind['agem'], trim_base)
        maj_enf = self.majoration_pension(data, nb_points, coeff_age)
        
        if to_check is not None:
            to_check['nb_points_' + name] = nb_points
            to_check['coeff_age_' + name] = coeff_age
            to_check['maj_' + name] = maj_enf
        pension = val_arrco*nb_points*coeff_age + maj_enf
        return pension.fillna(0)