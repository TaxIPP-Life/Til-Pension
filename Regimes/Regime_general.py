# -*- coding:utf-8 -*-
import math
from datetime import datetime

import os
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0,parentdir) 
from time_array import TimeArray

from numpy import maximum, minimum, array, divide, zeros, multiply
from pandas import Series

from regime import RegimeBase, compare_destinie
from utils_pension import build_long_values, build_salref_bareme, _info_numpy, print_multi_info_numpy
from pension_functions import nb_trim_surcote, sal_to_trimcot, unemployment_trimesters

code_avpf = 8
code_chomage = 2
code_preretraite = 9
#first_year_sal = 1949
first_year_avpf = 1972


def date_(year, month, day):
    return datetime.date(year, month, day)

class RegimeGeneral(RegimeBase):
    
    def __init__(self):
        RegimeBase.__init__(self)
        self.regime = 'RG'
        self.code_regime = [3,4]
        self.param_name = 'prive.RG'
     
    def get_trimesters_wages(self, data, to_check=False):
        trimesters = dict()
        wages = dict()
        
        workstate = data.workstate
        sali = data.sali
        info_ind = data.info_ind
        
        trim_cot = self.trim_cot_by_year(data)
        trimesters['cot_RG']  = trim_cot
        wages['cot_RG'] = self.sali_for_regime(sali, trim_cot)
        
        trim_ass = self.trim_ass_by_year(workstate, trim_cot)
        trimesters['ass_RG'] = trim_ass
        
        sal_for_avpf = self.sali_avpf(data) # Allocation vieillesse des parents au foyer : nombre de trimestres attribués 
        salref = build_salref_bareme(self.P_longit.common, first_year_avpf, data.datesim.year)
        sal_avpf = sal_for_avpf.translate_frequency(output_frequency='year', method='sum')
        trim_avpf = sal_to_trimcot(sal_avpf, salref, plafond=4)
        trimesters['avpf_RG']  = trim_avpf    
        wages['avpf_RG'] = sal_for_avpf
        
        trimesters['maj_RG'] = self.nb_trim_maj(info_ind)

        if to_check is not None:
            to_check['DA_RG'] = ((trimesters['cot_RG'] + trimesters['ass_RG'] + trimesters['avpf_RG']).sum(1) 
                                 + trimesters['maj_RG'])/4
        return trimesters, wages
        
    def _age_min_retirement(self, workstate=None):
        P = reduce(getattr, self.param_name.split('.'), self.P)
        return P.age_min

    def trim_cot_by_year(self, data, table=False):
        ''' Nombre de trimestres côtisés pour le régime général par année 
        ref : code de la sécurité sociale, article R351-9
        '''
        # Selection des salaires à prendre en compte dans le décompte (mois où il y a eu côtisation au régime)
        
        workstate = data.workstate
        sali = data.sali
        
        first_year_sal = min(workstate.dates) // 100
        wk_selection = workstate.isin(self.code_regime)
        sal_selection = TimeArray(wk_selection.array*sali.array, sali.dates)
        sal_selection.translate_frequency(output_frequency='year', method='sum', inplace=True)
        salref = build_salref_bareme(self.P_longit.common, first_year_sal, data.datesim.year)
        trim_cot_by_year = sal_to_trimcot(sal_selection, salref, plafond=4)
        return trim_cot_by_year
    
    def sali_for_regime(self, sali, trim_cot_by_year):
        ''' Cette fonction renvoie le TimeArray ne contenant que les salaires annuelles 
        pour lesquels au moins un trimestre a été validé au RG '''
        sal_by_year = sali.translate_frequency(output_frequency='year')
        return TimeArray((trim_cot_by_year.array> 0)*sal_by_year.array, sal_by_year.dates, name='sal_RG')
    
    def trim_ass_by_year(self, workstate, nb_trim_cot):
        ''' 
        Comptabilisation des périodes assimilées à des durées d'assurance
        Pour l"instant juste chômage workstate == 5 (considéré comme indemnisé) 
        qui succède directement à une période de côtisation au RG workstate == [3,4]
        TODO: ne pas comptabiliser le chômage de début de carrière
        '''
        trim_by_year_chom = unemployment_trimesters(workstate, code_regime=self.code_regime)
        trim_by_year_ass = trim_by_year_chom #+...
        
        if compare_destinie == True:
            trim_by_year_ass.array = (workstate.isin([code_chomage, code_preretraite])).array*4
        return trim_by_year_ass
    
    def sali_avpf(self, data):
        ''' Allocation vieillesse des parents au foyer : salaires de remplacements imputés
        Si certains salaires son déjà attribués à des états d'avpf on les conserve (cf.Destinie) sinon on applique la règle d'imputation'''
        workstate = data.workstate
        sali = data.sali
        
        avpf_selection = workstate.isin([code_avpf]).selected_dates(first_year_avpf)
        sal_for_avpf = sali.selected_dates(first_year_avpf)
        sal_for_avpf.array = sal_for_avpf.array*avpf_selection.array
        if sal_for_avpf.array.all() == 0:
            # TODO: frquency warning, cette manière de calculer les trimestres avpf ne fonctionne qu'avec des tables annuelles
            avpf = build_long_values(param_long=self.P_longit.common.avpf, first_year=first_year_avpf, last_year=data.datesim.year)
            sal_for_avpf.array = multiply(avpf_selection.array, 12*avpf)    
            if compare_destinie == True:
                smic_long = build_long_values(param_long=self.P_longit.common.smic_proj, first_year=first_year_avpf, last_year=data.datesim.year) 
                sal_for_avpf.array = multiply(avpf_selection.array, smic_long)    
        return sal_for_avpf
        
    def nb_trim_maj(self, info_ind):
        ''' Trimestres majorants, cf http://vosdroits.service-public.fr/particuliers/F19643.xhtml
            pour l'instant uniquement la MDA 
             - Note: ces trimestres ne sont pas associés à une année, on 
              renvoit donc un vecteur'''
        
        def _trim_mda(info_ind): 
            ''' Majoration pour enfant à charge : nombre de trimestres acquis '''
            
            # Rq : cette majoration n'est applicable que pour les femmes dans le RG
            child_mother = info_ind.loc[info_ind['sexe'] == 1, 'nb_born']
            if child_mother is not None:
                yearleg = self.dateleg.year
                #TODO: remove pandas
                mda = Series(0, index=info_ind.index)
                # TODO: distinguer selon l'âge des enfants après 2003
                # ligne suivante seulement if child_mother['age_enf'].min() > 16 :
                P_mda = self.P.prive.RG.mda
                mda[child_mother.index.values] = P_mda.trim_per_child*child_mother.values
                cond_enf_min = child_mother.values >= P_mda.nb_enf_min
                mda.loc[~cond_enf_min] = 0
                #TODO:  Réforme de 2003 : min(1 trimestre à la naissance + 1 à chaque anniv, 8)
            return array(mda)
        
        return _trim_mda(info_ind)
    
    def calculate_salref(self, data, wages):
        ''' SAM : Calcul du salaire annuel moyen de référence : 
        notamment application du plafonnement à un PSS'''
        try:
            P = reduce(getattr, self.param_indep.split('.'), self.P)
        except:
            P = reduce(getattr, self.param_name.split('.'), self.P)
        nb_best_years_to_take = P.nb_years
        first_year_sal = min(data.workstate.dates) // 100
        yearsim = data.datesim.year
        plafond = build_long_values(param_long=self.P_longit.common.plaf_ss, first_year=first_year_sal, last_year=yearsim)
        revalo = build_long_values(param_long=self.P_longit.prive.RG.revalo, first_year=first_year_sal, last_year=yearsim)
     
        for i in range(1, len(revalo)) :
            revalo[:i] *= revalo[i]
            
        sal_regime = wages['regime']
        sal_regime.translate_frequency(output_frequency='year', method='sum', inplace=True)
        years_sali = (sal_regime.array != 0).sum(1)
        nb_best_years_to_take = array(nb_best_years_to_take)
        nb_best_years_to_take[years_sali < nb_best_years_to_take] = years_sali[years_sali < nb_best_years_to_take]    
            
        if plafond is not None:
            assert sal_regime.array.shape[1] == len(plafond)
            sal_regime.array = minimum(sal_regime.array, plafond) 
        if revalo is not None:
            assert sal_regime.array.shape[1] == len(revalo)
            sal_regime.array = multiply(sal_regime.array,revalo)
        salref = sal_regime.best_dates_mean(nb_best_years_to_take)
        return salref.round(2)
    
    def assurance_maj(self, trim_RG, trim_tot, agem):
        ''' Détermination de la durée d'assurance corrigée introduite par la réforme Boulin
        (majoration quand départ à la retraite après 65 ans) '''
        P = reduce(getattr, self.param_name.split('.'), self.P)
        yearleg = self.dateleg.year
        age_taux_plein = P.decote.age_null
        if yearleg < 1983:
            return trim_RG
        else:
            trim_majo = maximum(divide(agem - age_taux_plein, 3), 0)
            elig_majo = (trim_RG < P.N_CP)
            trim_corr = trim_RG*(1 + P.tx_maj*trim_majo*elig_majo)
            return trim_corr
        
    def calculate_coeff_proratisation(self, info_ind, trimesters):
        ''' Calcul du coefficient de proratisation '''
        P =  reduce(getattr, self.param_name.split('.'), self.P)
        yearleg = self.dateleg.year
        trim_regime = trimesters['by_year_regime'].sum()
        trim_tot = trimesters['by_year_tot'].sum(1) + trimesters['maj_tot']
        agem = info_ind['agem']
        trim_CP = self.assurance_maj(trim_regime, trim_tot, agem)
        
        if 1948 <= yearleg and yearleg < 1972: 
            trim_CP= trim_CP + (120 - trim_CP)/2
        #TODO: voir si on ne met pas cette disposition spécifique de la loi Boulin dans la déclaration des paramètres directement
        elif yearleg < 1973:
            trim_CP = min(trim_CP, 128)
        elif yearleg < 1974:
            trim_CP = min(trim_CP, 136)            
        elif yearleg < 1975:
            trim_CP = min(trim_CP, 144)   
        else:
            trim_CP = minimum(trim_CP, P.N_CP)
        CP = minimum(1, divide(trim_CP, P.N_CP))
        return CP
    
    def _decote(self, trim_tot, agem):
        ''' Détermination de la décote à appliquer aux pensions '''
        yearleg = self.dateleg.year
        P = reduce(getattr, self.param_name.split('.'), self.P)
        tx_decote = P.decote.taux
        age_annulation = P.decote.age_null
        N_taux =P.plein.N_taux
        if yearleg < 1983:
            trim_decote = max(divide(age_annulation - agem, 3), 0)
        else:
            decote_age = maximum(divide(age_annulation - agem, 3), 0)
            decote_cot = maximum(N_taux - trim_tot, 0)
            assert len(decote_age) == len(decote_cot)
            trim_decote = minimum(decote_age, decote_cot)
        return trim_decote*tx_decote
        
    def _calculate_surcote(self, trimesters, date_start_surcote, age):
        ''' Détermination de la surcote à appliquer aux pensions '''
        yearleg = self.dateleg.year
        P = reduce(getattr, self.param_name.split('.'), self.P)
        trim_by_year_RG = trimesters['by_year_regime']
        if 'maj' in trimesters.keys() :
            trim_maj = trimesters['maj']
        else:
            trim_maj = 0
        trim_by_year_tot = trimesters['by_year_tot']
        N_taux = P.plein.N_taux
      
        def _trimestre_surcote_0304(trim_by_year_RG, date_start_surcote, P):
            ''' surcote associée aux trimestres côtisés en 2003 
            TODO : structure pas approprié pour les réformes du type 'et si on surcotait avant 2003, ça donnerait quoi?'''
            taux_surcote = P.taux_4trim
            trim_selected = trim_by_year_RG.selected_dates(first=2003, last=2004)
            nb_trim = nb_trim_surcote(trim_selected, date_start_surcote)
            return taux_surcote*nb_trim
        
        def _trimestre_surcote_0408(trim_by_year_RG, trim_by_year_tot, trim_maj, date_start_surcote, age, P): 
            ''' Fonction permettant de déterminer la surcote associée des trimestres côtisés entre 2004 et 2008 
            4 premiers à 0.75%, les suivants à 1% ou plus de 65 ans à 1.25% '''
            taux_4trim = P.taux_4trim
            taux_5trim = P.taux_5trim
            taux_65 = P.taux_65
            trim_selected = trim_by_year_RG.selected_dates(first=2004, last=2009)
            #agemin = agem.copy()
            age_start_surcote = 65*12 
            date_start_surcote_65 = self._date_start_surcote(trim_by_year_tot, trim_maj, age, age_start_surcote)

            nb_trim_65 = nb_trim_surcote(trim_selected, date_start_surcote_65)
            nb_trim = nb_trim_surcote(trim_selected, date_start_surcote) 
            nb_trim = nb_trim - nb_trim_65
            return taux_65*nb_trim_65 + taux_4trim*maximum(minimum(nb_trim,4), 0) + taux_5trim*maximum(nb_trim - 4, 0)
        
        def _trimestre_surcote_after_09(trim_by_year_RG, trim_years, date_start_surcote, P):
            ''' surcote associée aux trimestres côtisés en et après 2009 '''
            taux_surcote = P.taux
            trim_selected = trim_by_year_RG.selected_dates(first=2009, last=None)
            nb_trim = nb_trim_surcote(trim_selected, date_start_surcote)
            return taux_surcote*nb_trim
            
        if yearleg < 2004:
            taux_surcote = P.surcote.taux_07
            trim_tot = self.trim_by_year.sum(axis=1)
            return maximum(trim_tot - N_taux, 0)*taux_surcote 
        elif yearleg < 2007:
            taux_surcote = P.surcote.taux_07
            trim_surcote = nb_trim_surcote(trim_by_year_RG, maximum(date_start_surcote, 100*2003 + 1))
            return trim_surcote*taux_surcote 
        elif yearleg < 2010:
            surcote_03 = _trimestre_surcote_0304(trim_by_year_RG, date_start_surcote, P.surcote)
            surcote_0408 = _trimestre_surcote_0408(trim_by_year_RG, trim_by_year_tot, trim_maj, date_start_surcote, age, P.surcote)
            return surcote_03 + surcote_0408
        else:
            surcote_03 = _trimestre_surcote_0304(trim_by_year_RG, date_start_surcote, P.surcote)
            surcote_0408 = _trimestre_surcote_0408(trim_by_year_RG, trim_by_year_tot, trim_maj, date_start_surcote, age, P.surcote)
            surcote_aft09 = _trimestre_surcote_after_09(trim_by_year_RG, date_start_surcote, P.surcote)
            return surcote_03 + surcote_0408 + surcote_aft09   
        
    def minimum_contributif(self, pension_RG, pension, trim_RG, trim_cot, trim):
        ''' MICO du régime général : allocation différentielle 
        RQ : ASPA et minimum vieillesse sont gérés par OF
        Il est attribué quels que soient les revenus dont dispose le retraité en plus de ses pensions : loyers, revenus du capital, activité professionnelle... 
        + mécanisme de répartition si cotisations à plusieurs régimes'''
        yearleg = self.dateleg.year
        P = reduce(getattr, self.param_name.split('.'), self.P)
        N_taux = P.plein.N_taux
        if yearleg < 2004:
            mico = P.mico.entier 
            # TODO: règle relativement complexe à implémenter de la limite de cumul (voir site CNAV)
            return  maximum(0, mico - pension_RG)*minimum(1, divide(trim_cot, P.N_CP))
        else:
            mico_entier = P.mico.entier
            mico_maj = P.mico.entier_maj
            RG_exclusif = ( pension_RG == pension) | (trim <= N_taux)
            mico_RG = mico_entier + minimum(1, divide(trim_cot, P.N_CP))*(mico_maj - mico_entier)
            mico =  mico_RG*( RG_exclusif + (1 - RG_exclusif)*divide(trim_RG, trim))
            return maximum(0, mico - pension_RG)
        
    def plafond_pension(self, pension_brute, salref, cp, surcote):
        ''' plafonnement à 50% du PSS 
        TODO: gérer les plus de 65 ans au 1er janvier 1983'''
        PSS = self.P.common.plaf_ss
        P = reduce(getattr, self.param_name.split('.'), self.P)
        taux_plein = P.plein.taux
        taux_PSS = P.plafond
        pension_surcote_RG = taux_plein*salref*cp*surcote
        return minimum(pension_brute - pension_surcote_RG, taux_PSS*PSS) + pension_surcote_RG
        
            