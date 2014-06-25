# -*- coding: utf-8 -*-

from time_array import TimeArray
from numpy import zeros

def sum_from_dict(dictionnary, key='', plafond=None):
    ''' Somme les TimeArray contenus dans un dictionnaire et dont le nom contient la 'key' '''
    timearray_with_key = [trim for name, trim in dictionnary.items() if key in name]
    first = timearray_with_key[0]
    trim_tot = TimeArray(zeros(first.array.shape), first.dates)
    for timearray in timearray_with_key:
        trim_tot += timearray
    trim_tot = trim_tot.ceil(plaf=plafond)
    return trim_tot
    
def sum_by_regime(trimesters_wages, to_other):
    for regime, dict_regime in to_other.iteritems():
        for type in dict_regime.keys():
            trimesters_wages[regime][type].update(dict_regime[type])
    for regime in trimesters_wages.keys() :
        trimesters_wages[regime]['wages'].update({ 'regime' : sum_from_dict(trimesters_wages[regime]['wages'])})
        trimesters_wages[regime]['trimesters'].update({ 'regime' : sum_from_dict(trimesters_wages[regime]['trimesters'])})
    return trimesters_wages

def attribution_mda(trimesters_wages):
    ''' La Mda (attribuée par tous les régimes de base), ne peut être accordé par plus d'un régime. 
    Régle d'attribution : a cotisé au régime + si polypensionnés -> ordre d'attribution : RG, RSI, FP
    Rq : Pas beau mais temporaire, pour comparaison Destinie'''
    #devrait peut-être remonter dans PensionLegislation
    RG_cot = (trimesters_wages['RG']['trimesters']['regime'].sum(1) > 0)
    FP_cot = (trimesters_wages['FP']['trimesters']['regime'].sum(1) > 0)
    RSI_cot = (trimesters_wages['RSI']['trimesters']['regime'].sum(1) > 0)
    trimesters_wages['RG']['maj']['DA'] = trimesters_wages['RG']['maj']['DA']*RG_cot
    trimesters_wages['RSI']['maj']['DA']= trimesters_wages['RSI']['maj']['DA']*RSI_cot*(1-RG_cot)
    trimesters_wages['FP']['maj']['DA'] = trimesters_wages['FP']['maj']['DA']*FP_cot*(1-RG_cot)*(1-RSI_cot)
    return trimesters_wages
    
def update_all_regime(trimesters_wages, dict_to_check):
    #devrait peut-être remonter dans PensionLegislation
    trim_by_year_tot = sum_from_dict({ regime : trimesters_wages[regime]['trimesters']['regime'] for regime in trimesters_wages.keys()})
    trimesters_wages = attribution_mda(trimesters_wages)
    maj_tot = sum([sum(trimesters_wages[regime]['maj'].values()) for regime in trimesters_wages.keys()])
    enf_tot = sum([trimesters_wages[regime]['maj']['DA'] for regime in trimesters_wages.keys()])
    trimesters_wages['all_regime'] = {'trimesters' : {'tot' : trim_by_year_tot}, 'maj' : {'tot' : maj_tot, 'enf':enf_tot}}
    if dict_to_check is not None:
        for regime in ['RG', 'FP', 'RSI']:
            dict_to_check['DA_' + regime] = (trimesters_wages[regime]['trimesters']['regime'].sum(1) + sum(trimesters_wages[regime]['maj'].values()))/4
    return trimesters_wages

