# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import sys
import datetime as dt
import time

from pandas import DataFrame

from Regimes.Fonction_publique import FonctionPublique
from Regimes.Regimes_complementaires_prive import AGIRC, ARRCO
from Regimes.Regimes_prives import RegimeGeneral, RegimeSocialIndependants
from time_array import TimeArray
from pension_data import PensionData
from utils_pension import build_naiss, load_param
from pension_functions import sum_from_dict, trim_maj_all
first_year_sal = 1949 
import cProfile

base_regimes = ['RegimeGeneral', 'FonctionPublique', 'RegimeSocialIndependants']
complementaire_regimes = ['ARRCO', 'AGIRC']
base_to_complementaire = {'RegimeGeneral': ['arrco', 'agirc'], 'FonctionPublique': []}

def sum_by_regime(trimesters_wages, to_other):
    for regime, dict_regime in to_other.iteritems():
        for type in dict_regime.keys():
            trimesters_wages[regime][type].update(dict_regime[type])
            
    trim_by_year_regime = {regime : sum_from_dict(trimesters_wages[regime]['trimesters']) for regime in trimesters_wages.keys()} 
    trim_by_year_tot = sum_from_dict(trim_by_year_regime)
    
    for regime in trimesters_wages.keys() :
        trimesters_wages[regime]['wages'].update({ 'regime' : sum_from_dict(trimesters_wages[regime]['wages'])})
        trimesters_wages[regime]['trimesters'].update({ 'regime' : sum_from_dict(trimesters_wages[regime]['trimesters'])})
    return trimesters_wages

def attribution_mda(trimesters_wages):
    ''' La Mda (attribuée par tous les régimes de base), ne peut être accordé par plus d'un régime. 
    Régle d'attribution : a cotisé au régime + si polypensionnés -> ordre d'attribution : RG, RSI, FP
    Rq : Pas beau mais temporaire, pour comparaison Destinie'''
    RG_cot = (trimesters_wages['RegimeGeneral']['trimesters']['regime'].sum(1) > 0)
    FP_cot = (trimesters_wages['FonctionPublique']['trimesters']['regime'].sum(1) > 0)
    RSI_cot = (trimesters_wages['RegimeSocialIndependants']['trimesters']['regime'].sum(1) > 0)
    trimesters_wages['RegimeGeneral']['maj']['DA'] = trimesters_wages['RegimeGeneral']['maj']['DA']*RG_cot
    trimesters_wages['RegimeSocialIndependants']['maj']['DA']= trimesters_wages['RegimeSocialIndependants']['maj']['DA']*RSI_cot*(1-RG_cot)
    trimesters_wages['RegimeSocialIndependants']['maj']['DA'] = trimesters_wages['RegimeSocialIndependants']['maj']['DA']*RSI_cot*(1-RG_cot)*(1-RSI_cot)
    return trimesters_wages
    
def update_all_regime(trimesters_wages):
    trim_by_year_tot = sum_from_dict({ 'regime' : trimesters_wages[regime]['trimesters']['regime'] for regime in trimesters_wages.keys()})
    trimesters_wages = attribution_mda(trimesters_wages)
    maj_tot = sum([sum(trimesters_wages[regime]['maj'].values()) for regime in trimesters_wages.keys()])
    trimesters_wages['all_regime'] = {'trimesters' : {'tot' : trim_by_year_tot}, 'maj' : {'tot' : maj_tot}}
    return trimesters_wages

def select_regime_base(trimesters_wages, code_regime_comp, correspondance):
    for base, comp in correspondance.iteritems():
        if code_regime_comp in comp:
            regime_base = base
    return trimesters_wages[regime_base]


def til_pension(sali, workstate, info_ind, time_step='year', yearsim=2009, yearleg=None, example=False):
    command = """run_pension(sali, workstate, info_ind, time_step, yearsim, yearleg, example)"""
    cProfile.runctx( command, globals(), locals(), filename="profile_pension" + str(yearsim))

class PensionSimulation(object):

    def __init__(self):
        self.yearsim = None
        self.data = None
        #TODO: base_to_complementaire n'est pas vraiment de la législation
        self.legislation = dict(base_regimes = ['RegimeGeneral', 'FonctionPublique', 'RegimeSocialIndependants'],
                                complementaire_regimes = ['ARRCO', 'AGIRC'],
                                base_to_complementaire = {'RegimeGeneral': ['arrco', 'agirc'], 'FonctionPublique': []}
                                )
        self.param = None
        
    def load_data_from_pieces(self, workstate, sali, info_ind):
        ''' generate data
            table are taken only since first_year_sal
            and until yearsim if yearsim is not None
            - workstate, sali: longitudinal array, or pandas DataFrame or TimeArray
            - info_ind : pandas DataFrame
            - yearsim: int
        '''
        if max(info_ind.loc[:,'sexe']) == 2:
            info_ind.loc[:,'sexe'] = info_ind.loc[:,'sexe'].replace(1,0)
            info_ind.loc[:,'sexe'] = info_ind.loc[:,'sexe'].replace(2,1)
        yearsim = sali.dates[-1]
        info_ind.loc[:,'naiss'] = build_naiss(info_ind.loc[:,'agem'], dt.date(yearsim,1,1))
        
        data = PensionData.from_arrays(workstate, sali, info_ind)
        data.selected_dates(first=first_year_sal, inplace=True)
        self.data = data
        
    def load_param(self, yearleg):
        ''' should run after having a data'''
        assert self.data is not None
        path_pension = 'C:\\Til-Pension\\' #TODO: have it with os.path.etc..
        param_file = path_pension + 'France\\param.xml' #TODO: Amelioration
        date_param = str(yearleg)+ '-05-01' #TODO: change for -01-01 ?
        date_param = dt.datetime.strptime(date_param ,"%Y-%m-%d").date()
        P, P_longit = load_param(param_file, self.data.info_ind, date_param)
        self.param = P, P_longit
        self.yearleg = yearleg
        
    def evaluate(self, time_step='year', to_check=False):
        if self.param is None:
            raise Exception("you should give parameter to PensionData before to evaluate")
        dict_to_check = dict()
        P = self.param[0]
        P_longit = self.param[1]
        #TODO: remove yearleg
        config = {'dateleg' : self.yearleg, 'P': P, 'P_longit': P_longit,
                  'time_step': time_step}
        
        data = self.data
        leg = self.legislation
        base_regimes = leg['base_regimes']
        complementaire_regimes = leg['complementaire_regimes']
        base_to_complementaire = leg['base_to_complementaire']
        ### get trimesters (only TimeArray with trim by year), wages (only TimeArray with wage by year) and trim_maj (only vector of majoration): 
        trimesters_wages = dict()
        to_other = dict()
        for reg_name in base_regimes:
            reg = eval(reg_name + '()')
            reg.set_config(**config)
            trimesters_wages_regime, to_other_regime = reg.get_trimesters_wages(data)
            trimesters_wages[reg_name] = trimesters_wages_regime
            to_other.update(to_other_regime)
            
        trimesters_wages = sum_by_regime(trimesters_wages, to_other)
        trimesters_wages = update_all_regime(trimesters_wages)
        
        for reg_name in base_regimes:
            reg = eval(reg_name + '()')
            reg.set_config(**config)
            pension_reg = reg.calculate_pension(data, trimesters_wages[reg_name], trimesters_wages['all_regime'], dict_to_check)
            if to_check == True:
                dict_to_check['pension_' + reg.regime] = pension_reg
    
        for reg_name in complementaire_regimes:
            reg = eval(reg_name + '()')
            reg.set_config(**config)
            regime_base = select_regime_base(trimesters_wages, reg.regime, base_to_complementaire)
            pension_reg = reg.calculate_pension(data, regime_base['trimesters'], dict_to_check)
            if to_check == True:
                dict_to_check['pension_' + reg.regime] = pension_reg
    
        if to_check == True:
            #pd.DataFrame(to_check).to_csv('resultat2004.csv')
            return pd.DataFrame(dict_to_check)
        else:
            return pension_reg # TODO: define the output        
        
             
    def main(self, sali, workstate, info_ind, yearleg, yearsim=None, time_step='year', to_check=False):
        self.load_data_from_pieces(sali, workstate, info_ind, yearsim)
        self.load_param(yearleg)
        self.evaluate()
        

