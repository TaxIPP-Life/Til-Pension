# -*- coding: utf-8 -*-

import datetime as dt
from pandas import read_table, DataFrame
from numpy import zeros

from pension_data import PensionData
from CONFIG_scenarios import data_scenarios_path
import pdb


nb_scenarios = 260
dates = [100*x + 1 for x in range(1969,2010)]


sali = zeros((nb_scenarios,len(dates)))
workstate = zeros((nb_scenarios,len(dates)))
info_ind = DataFrame(index=range(nb_scenarios), 
                     columns=['agem','naiss','sexe','nb_enf',
                                'nb_pac','nb_enf_FP','nb_enf_RG','nb_enf_RSI',
                                'tauxprime'])

def load_case(i):
    file = data_scenarios_path + 'data' +str(i) + '.csv'
    data = read_table(file, sep=',')
    # print data.loc[40,'agedep'] c'est toujours 55 ! Inutile
    assert all((data['agirc']==1) == ((data['I_cnav']==1) & (data['agirc']==1)))
    workstate = 3*(data['I_cnav']==1) + (data['agirc']==1) + 7*(data['I_rsi']==1) + 5*(data['I_pub']==1) + (data['inactif']==1)
    #TODO: tenir compte de l'AVPF
    sali = data['revenu_tot'].values
    if all((data['remu_pub'] == 0) | (data['remu_priv'] == 0)) == False: #TODO: remove
        print 'probleme pour ' + str(i)
#         pdb.set_trace()
    sexe = data['sexi'][0] == 2
    nb_enf = data['nbenf'][0]
    return workstate, sali, sexe, nb_enf


agem = (2009-1954 + 0.5)*12
naiss = dt.date(1954, 6, 1)
info_ind['agem'] = agem
info_ind['naiss'] = naiss
info_ind['tauxprime'] = 0
for i in range(nb_scenarios):
    work_i, sali_i, sexe, nb_enf = load_case(i+1) # Attention déclage dans la numérotaiton qui ne commence pas à zeros
    sali[i,:] = sali_i
    workstate[i,:] = work_i
    info_ind.loc[i,['sexe','nb_enf','nb_pac',
                    'nb_enf_RG','nb_enf_RSI','nb_enf_FP']] = [sexe, nb_enf, nb_enf,
                                                                           nb_enf, nb_enf, nb_enf]

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

pdb.set_trace()
trim['FP']['trimesters']
trim['FP']['maj']

