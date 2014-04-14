# -*- coding:utf-8 -*-
import math
import numpy as np
import pandas as pd

from pandas import DataFrame
from datetime import datetime


import os
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0,parentdir) 
from SimulPension import PensionSimulation
from utils import years_to_months, months_to_years, substract_months, valbytranches
from pension_functions import  workstate_selection, unemployment_trimesters, calculate_trim_cot,  calculate_SAM

code_avpf = 8

def date_(year, month, day):
    return dt.datetime.date(year, month, day)


class Regime_general(PensionSimulation):
    
    def __init__(self, param_regime, param_common, param_longitudinal):
        PensionSimulation.__init__(self)
        self.regime = 'RG'
        self.code_regime = [3,4]
        
        self._P = param_regime
        self._Pcom = param_common
        self._Plongitudinal = param_longitudinal
        
        self.workstate  = None
        self.sali = None
        self.info_ind = None
        self.info_child_mother = None
        self.info_child_father = None
        self.time_step = None

    def load(self):
        
        def _build_table(table, yearsim):
            table = table.reindex_axis(sorted(table.columns), axis=1)
            date_end = (yearsim - 1 )* 100 + 1
            possible_dates = []
            for y in range(1949, yearsim): 
                possible_dates += [y * 100 + m for m in range(1,13)]
            selected_dates = set(table.columns).intersection(possible_dates)
            table = table.loc[:, selected_dates]
            table = table.reindex_axis(sorted(table.columns), axis=1)
            return table
                        
        def _build_salmin(smic,avts):
            '''
            salaire trimestriel de référence minimum
            Rq : Toute la série chronologique est exprimé en euros
            '''
            yearsim = self.datesim.year
            salmin = DataFrame( {'year' : range(1949, yearsim ), 'sal' : - np.ones(yearsim - 1949)} ) 
            avts_year = []
            smic_year = []
            for year in range(1949,1972):
                avts_old = avts_year
                avts_year = []
                for key in avts.keys():
                    if str(year) in key:
                        avts_year.append(key)
                if not avts_year:
                    avts_year = avts_old
                salmin.loc[salmin['year'] == year, 'sal'] = avts[avts_year[0]] 
                
            #TODO: Trancher si on calcule les droits à retraites en incluant le travail à l'année de simulation pour l'instant non (ex : si datesim = 2009 on considère la carrière en emploi jusqu'en 2008)
            for year in range(1972,yearsim):
                smic_old = smic_year
                smic_year = []
                for key in smic.keys():
                    if str(year) in key:
                        smic_year.append(key)
                if not smic_year:
                    smic_year = smic_old
                if year <= 2013 :
                    salmin.loc[salmin['year'] == year, 'sal'] = smic[smic_year[0]] * 200 
                    if year <= 2001 :
                        salmin.loc[salmin['year'] == year, 'sal'] = smic[smic_year[0]] * 200  / 6.5596
                else:
                    salmin.loc[salmin['year'] == year, 'sal'] = smic[smic_year[0]] * 150 
            return salmin['sal']
        
        def _build_naiss(agem, datesim):
            ''' Détermination de la date de naissance à partir de l'âge et de la date de simulation '''
            naiss = agem.apply(lambda x: substract_months(datesim, x))
            return naiss
        
        # Selection du déroulé de carrière qui nous intéresse (1949 -> année de simulation)
        # Rq : la selection peut se faire sur données mensuelles ou annuelles
        yearsim = self.datesim.year
        self.workstate = _build_table(self.workstate, yearsim)
        self.sali = _build_table(self.sali, yearsim)
        self.info_ind['naiss'] = _build_naiss(self.info_ind['agem'], self.datesim)
        # Salaires de référence (vecteur construit à partir des paramètres indiquant les salaires annuels de reférences)
        smic_long = self._Plongitudinal.common.smic
        avts_long = self._Plongitudinal.common.avts.montant
        self.salref = _build_salmin(smic_long, avts_long)
            
    def nb_trim_cot(self):
        ''' Nombre de trimestres côtisés pour le régime général 
        ref : code de la sécurité sociale, article R351-9
         '''
        # Selection des salaires à prendre en compte dans le décompte (mois où il y a eu côtisation au régime)
        wk_selection = workstate_selection(self.workstate, code_regime = self.code_regime, input_step = self.time_step, output_step = 'month')
        sal_selection = wk_selection * years_to_months(self.sali, division = True) 
        nb_trim_cot = calculate_trim_cot(months_to_years(sal_selection), self.salref)
        self.sal_RG = sal_selection
        return nb_trim_cot
        

    def nb_trim_ass(self):
        ''' Comptabilisation des périodes assimilées à des durées d'assurance
        Pour l"instant juste chômage workstate == 5 (considéré comme indemnisé) qui succède directement à une période de côtisation au RG workstate == [3,4]'''
        nb_trim_chom = unemployment_trimesters(self.workstate, code_regime = self.code_regime, input_step = self.time_step)
        nb_trim_ass = nb_trim_chom # TODO: + nb_trim_war + ....
        return nb_trim_ass
            
    def nb_trim_maj(self):
        ''' Trimestres majorants acquis au titre de la MDA, de l'assurance pour congé parental ou de l'AVPF '''
        
        def _mda(info_child, list_id, yearsim):
            ''' Majoration pour enfant à charge : nombre de trimestres acquis
            Rq : cette majoration n'est applicable que pour les femmes dans le RG'''
            mda = pd.DataFrame({'mda' : np.zeros(len(list_id))}, index = list_id)
            # TODO: distinguer selon l'âge des enfants après 2003
            # ligne suivante seulement if info_child['age_enf'].min() > 16 :
            info_child = info_child.groupby('id_parent')['nb_enf'].sum()
            if yearsim < 1972 :
                return mda
            elif yearsim <1975:
                # loi Boulin du 31 décembre 1971 
                mda.loc[info_child.index.values, 'mda'] = 4 * info_child.values
                mda.loc[mda['mda'] < 2, 'mda'] = 0
                return mda
            elif yearsim <2004:
                mda.loc[info_child.index.values, 'mda'] = 4 * info_child.values
                mda.loc[mda['mda'] < 2, 'mda'] = 0
                return mda
            else:
                # Réforme de 2003 : min(1 trimestre à la naissance + 1 à chaque anniv, 8)
                mda.loc[info_child.index.values, 'mda'] = 4 * info_child.values
                mda.loc[mda['mda'] < 2, 'mda'] = 0
                return mda['mda']
            
        def _avpf(workstate, sali, input_step):
            ''' Allocation vieillesse des parents au foyer : nombre de trimestres acquis'''
            avpf_selection = workstate_selection(workstate, code_regime = [code_avpf], input_step = input_step, output_step = 'month')
            sal_avpf = avpf_selection * years_to_months(sali, division = True) 
            nb_trim = calculate_trim_cot(months_to_years(sal_avpf), self.salref)
            return nb_trim
        
        # info_child est une DataFrame comportant trois colonnes : identifiant du parent, âge de l'enfant, nb d'enfants du parent ayant cet âge  
        info_child_mere = self.info_child_mother
        list_id = self.sali.index.values
        yearsim = self.datesim.year
        
        nb_trim_mda = _mda(info_child_mere, list_id, yearsim)
        nb_trim_avpf = _avpf(self.workstate, self.sali, self.time_step)
        return nb_trim_mda + nb_trim_avpf
    
    def SAM(self):
        nb_years = valbytranches(self._P.nb_sam, self.info_ind)
        SAM = calculate_SAM(self.sal_RG, nb_years, time_step = 'month')
        return SAM
    
    def assurance_maj(self, trim_RG, trim_tot, agem):
        ''' Détermination de la durée d'assurance corrigée (majoration quand départ à la retraite après 65 ans) introduite par la réforme Boulin '''
        P = self._P
        date = self.datesim

        if date.year < 1983:
            return trim_RG
        elif date.year < 2004 :
            trim_majo = np.maximum(0, math.ceil(agem/ 3 - 65 * 4))
            elig_majo = ( trim_RG < P.N_CP )
            trim_corr = trim_RG * ( 1 + P.tx_maj * trim_majo * elig_majo )
            return trim_corr
        else:
            trim_majo = np.maximum(0, np.ceil(agem/ 3 - 65 * 4))
            elig_majo = ( trim_tot < P.N_CP )
            trim_corr = trim_RG * ( 1 + P.tx_maj * trim_majo * elig_majo )
            return trim_corr  
        
    def calculate_CP(self, trim_RG):
        ''' Calcul du coefficient de proratisation '''
        P =  self._P
        yearsim = self.datesim.year
        N_CP = valbytranches(P.N_CP, self.info_ind)
              
        if 1948 <= yearsim and yearsim < 1972: 
            trim_RG = trim_RG + (120 - trim_RG)/2
        #TODO: voir si on ne met pas cette disposition spécifique de la loi Boulin dans la déclaration des paramètres directement
        elif yearsim < 1973:
            trim_RG = np.min(trim_RG, 128)
        elif yearsim < 1974:
            trim_RG = np.min(trim_RG, 136)            
        elif yearsim < 1975:
            trim_RG = np.min(trim_RG, 144)   
        else:
            trim_RG = np.minimum(N_CP, trim_RG)
        CP = np.minimum(1, trim_RG / N_CP)
        return CP
    
    def decote(self, trim_tot, agem):
        ''' Détermination de la décote à appliquer aux pensions '''
        yearsim = self.datesim.year
        P = self._P
        tx_decote = valbytranches(P.decote.taux, self.info_ind)
        print P.decote
        age_annulation = valbytranches(P.decote.age_null, self.info_ind)
        N_taux = valbytranches(P.plein.N_taux, self.info_ind)

        if yearsim < 1983:
            trim_decote = np.max(0, np.divide(age_annulation - agem, 4))
        else:
            #assert len(age_annulation) == len(agem)
            #assert len(N_taux) == len(trim_tot)
            decote_age = np.divide(age_annulation - agem, 4)
            decote_cot = N_taux - trim_tot
            assert len(decote_age) == len(decote_cot)

            trim_decote = np.maximum(0, np.minimum(decote_age, decote_cot))
        return trim_decote * tx_decote
        
        
    def surcote(self, trim_tot, agem):
        ''' Détermination de la surcote à appliquer aux pensions '''
        yearsim = self.datesim.year
        P = self._P
        tx_surcote = valbytranches(P.surcote.taux, self.info_ind)
        
        