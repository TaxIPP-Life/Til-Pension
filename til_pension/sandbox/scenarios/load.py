# -*- coding: utf-8 -*-

import datetime as dt
from pandas import read_table, DataFrame
from numpy import zeros
from copy import deepcopy

from pension_data import PensionData
from time_array import TimeArray
from pension_functions import sum_by_regime, update_all_regime
from CONFIG_scenarios import data_scenarios_path
import pdb
from pdb import Pdb

#paramètres généraux
nb_scenarios = 260
dates = [100*x + 1 for x in range(1969,2010)]

def trim_isin(data, workstate, code):
    selection = data[[u'trimvalmat', u'trimval', u'trimcot', u'trimvalcho', u'trimvalg', u'trimcot2']].copy()
    selection.loc[~workstate.isin(code), :] = 0
    return selection

def load_case(i):
    file = data_scenarios_path + 'data' +str(i) + '.csv'
    data = read_table(file, sep=',')
    # print data.loc[40,'agedep'] c'est toujours 55 ! Inutile
    assert all((data['agirc']==1) == ((data['I_cnav']==1) & (data['agirc']==1)))
    ### question : comment gérer quand on a deux régimes ? CNAV et PUB par exemple
    workstate = 3*(data['I_cnav']==1) + (data['agirc']==1) + 7*(data['I_rsi']==1) + 5*(data['I_pub']==1) + (data['inactif']==1)
    #TODO: tenir compte de l'AVPF
    sali = data['revenu_tot'].values
    if all((data['remu_pub'] == 0) | (data['remu_priv'] == 0)) == False: #TODO: remove
        print 'probleme pour ' + str(i)
#         pdb.set_trace()
    sexe = data['sexi'][0] == 2
    nb_enf = data['nbenf'][0]
    
    # sort les valeurs des trimestres
    trim_RG = trim_isin(data, workstate, [3,4])
    trim_FP = trim_isin(data, workstate, [5,6])
    trim_RSI = trim_isin(data, workstate, [7])
    trim = data[[u'trimvalmat', u'trimval', u'trimcot', u'trimvalcho', u'trimvalg', u'trimcot2']]
    if not all(trim_FP.sum(axis=0) + trim_RG.sum(axis=0) + trim_RSI.sum(axis=0) == trim.sum(axis=0)):
        print 'on a perdu des trimestres dans la bataille pour le scenario ' + str(i)

    return workstate, sali, sexe, nb_enf, trim_FP, trim_RG, trim_RSI


sali = zeros((nb_scenarios,len(dates)))
workstate = zeros((nb_scenarios,len(dates)))

info_ind = DataFrame(index=range(nb_scenarios), 
                     columns=['agem','naiss','sexe','nb_enf',
                                'nb_pac','nb_enf_FP','nb_enf_RG','nb_enf_RSI',
                                'tauxprime'])
agem = (2009-1954 + 0.5)*12
naiss = dt.date(1954, 6, 1)
info_ind['agem'] = agem
info_ind['naiss'] = naiss
info_ind['tauxprime'] = 0

trim_types = ['trimvalmat', 'trimval', 'trimcot', 'trimvalcho', 'trimvalg', 'trimcot2']
trim_variables = ['cot', 'regime', 'avpf', 'ass', 'cot_FP']
trimester = dict()
for regime in ['RG', 'FP', 'RSI']:
    trimester[regime] = dict()
    for val in trim_variables:
        trimester[regime][val] = zeros((nb_scenarios,len(dates)))

        
for i in range(nb_scenarios):
    work_i, sali_i, sexe, nb_enf, trim_FP, trim_RG, trim_RSI = load_case(i+1) # Attention déclage dans la numérotaiton qui ne commence pas à zeros
    sali[i,:] = sali_i
    workstate[i,:] = work_i
    info_ind.loc[i,['sexe','nb_enf','nb_pac',
                    'nb_enf_RG','nb_enf_RSI','nb_enf_FP']] = [sexe, nb_enf, nb_enf,
                                                                           nb_enf, nb_enf, nb_enf]
    for regime in ['RG', 'FP', 'RSI']:
        trim = 1*eval('trim_' + regime)
        trimester[regime]['cot'][i,:] = trim['trimcot']
        trimester[regime]['regime'][i,:] = trim['trimcot2']
        trimester[regime]['avpf'][i,:] = trim['trimvalmat']
        trimester[regime]['ass'][i,:] = trim['trimvalcho']

#TODO: know why nbenf is often NaN and not 0.
info_ind.fillna(0, inplace=True)
data = PensionData.from_arrays(workstate, sali, info_ind, dates)


from pension_legislation import PensionParam, PensionLegislation
from simulation import PensionSimulation

param = PensionParam(201001, data)
legislation = PensionLegislation(param)
simulation = PensionSimulation(data, legislation)
trim = simulation.profile_evaluate(output='trimesters_wages')
result_til_year = simulation.profile_evaluate(to_check=True)
print simulation.profile_evaluate(to_check=True)

new = deepcopy(simulation.trimesters_wages)
for regime in ['RG', 'FP', 'RSI']:
    for key in new[regime]['trimesters'].keys():
        new[regime]['trimesters'][key] = TimeArray(trimester[regime][key], dates)
new.pop('all_regime')
new = sum_by_regime(new, {})
new = update_all_regime(new)

simulation.trimesters_wages = new
simulation.pensions = {}
test = simulation.evaluate(to_check=True)
init = result_til_year[test.columns]
pdb.set_trace()
(test == init).all()
test['pension_tot'], init['pension_tot']
    
