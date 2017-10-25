# -*- coding: utf-8 -*-
"""
Created on Mon Oct 23 09:51:12 2017

@author: s.rabate
"""

# -*- coding: utf-8 -*-

import pandas as pd

import matplotlib.pyplot as plt
from til_pension.sandbox.compare.CONFIG_compare import pensipp_comparison_path
from til_pension.simulation import PensionSimulation
from til_pension.pension_legislation import PensionParam, PensionLegislation
from til_pension.sandbox.compare.load_pensipp import load_pensipp_data, load_pensipp_result
from til_pension.sandbox.compare.load_nber import load_from_csv, selection_for_simul
from til_pension.sandbox.nber.CONFIG_nber import data_path
#from til_pension.sandbox.nber.load_data_nber import load_from_csv
#from til_pension.sandbox.nber.CONFIG_nber import data_path


first_year_sal = 1949
yearsim = 2005
years = range(1983, 2010)

#def compute_pension(data_path, years):
data = load_from_csv(data_path)
columns = ['60','61', '62', '63','64', '65', '66', '67']
results = pd.DataFrame(index=data.info_ind.index, columns=columns)
results = results.merge(data.info_ind.ix[ : , ['sexe', 'versant', 'type', 't_naiss']], left_index = True,  right_index = True)

for generation in range(1920, 1955):
    print("Individuals of generation {}".format(generation))
    # Selection:
    subdata = load_from_csv(data_path)
    select_id_depart = (subdata.info_ind.loc[:,'t_naiss']+1900 == generation)
    id_selected = select_id_depart[select_id_depart == True].index
    ix_selected = [int(ident) - 1 for ident in id_selected]
    subdata.sali = subdata.sali[ix_selected, :]
    subdata.workstate = subdata.workstate[ix_selected, :]
    subdata.info_ind = subdata.info_ind.iloc[ix_selected,:]
    for age in range (60, 68):
        print("Age =  {}".format(age))
        yearsim = max(1983, generation + age)
        subdata.info_ind.loc[:,'agem'] =  (yearsim - pd.DatetimeIndex(subdata.info_ind['naiss']).year)*12
        data_bounded = subdata.selected_dates(first=1949, last=yearsim)
        param = PensionParam(yearsim, data_bounded)
        legislation = PensionLegislation(param)
        simul_til = PensionSimulation(data_bounded, legislation)
        simul_til.set_config()
        result_til_year = dict()
        P = simul_til.legislation.P
        results.loc[ix_selected , str(age)] = simul_til.calculate('pension', 'all')


# Sorties
selection = (results.t_naiss >= 49) & (results.t_naiss <= 54) &  (results.type == 1)  & (results.sexe == 1)  & (results.versant == 1)
subresults = results.loc[selection, ]         

x = ['60','61', '62', '63','64', '65']
plt.plot(x, subresults.iloc[0, 0:6],
         x, subresults.iloc[1, 0:6],
         x, subresults.iloc[2, 0:6],
         x, subresults.iloc[3, 0:6],
         x, subresults.iloc[4, 0:6],
         x, subresults.iloc[5, 0:6])


        
#        for regime in ['FP', 'RG', 'RSI']:
#            print(regime)    
#            trim_regime = simul_til.calculate('nb_trimesters', regime)
#            for varname in ['coeff_proratisation', 'DA', 'decote', 'n_trim', 'salref', 'surcote', 'taux', 'pension']:
#                print(varname)
#                if varname == 'coeff_proratisation':
#                    result_til_year['CP_' + regime] = simul_til.calculate(varname, regime)*(trim_regime > 0)
#                elif varname == 'decote':
#                    param_name = simul_til.get_regime(regime).param_name
#                    taux_plein = reduce(getattr, param_name.split('.'), P).plein.taux
#                    calc = simul_til.calculate(varname, regime)
#                    result_til_year[varname + '_' + regime] = taux_plein*calc*(trim_regime > 0)
#                else:
#                    if varname != 'n_trim':
#                        calc = simul_til.calculate(varname, regime)
#                        result_til_year[varname + '_' + regime] = calc*(trim_regime > 0)
#                    else:
#                        result_til_year[varname + '_' + regime] = simul_til.calculate(varname, regime)
#        for regime in ['agirc', 'arrco']:
#            for varname in ['coefficient_age', 'nb_points', 'pension']:
#                if varname == 'coefficient_age':
#                    result_til_year['coeff_age_' + regime] = simul_til.calculate(varname, regime)
#                if varname == 'nombre_points':
#                    result_til_year['nb_points_' + regime] = simul_til.calculate(varname, regime)
#                else:
#                    result_til_year[varname + '_' + regime] = simul_til.calculate(varname, regime)
        
        
        


#        result_til_year = pd.DataFrame(result_til_year, index=data_bounded.info_ind['index'])
#        id_year_in_initial = [ident for ident in result_til_year.index if ident in result_til.index]
#        assert (id_year_in_initial == result_til_year.index).all()
#        result_til.loc[result_til_year.index, :] = result_til_year
#        result_til.loc[result_til_year.index, 'yearliq'] = yearsim
#
#
#    to_compare = (result_til['yearliq']!= -1)
#    til_compare = result_til.loc[to_compare,:]
#    pensipp_compare = result_pensipp.loc[to_compare,:]
#    return til_compare, pensipp_compare , simul_til
#
#
#def compare(table1, table2, var_to_check_montant, var_to_check_taux, threshold):
#    var_not_implemented = {'til':[], 'pensipp':[]}
#
#    def _check_var(var, threshold, var_conflict):
#
#        if var not in table1.columns:
#            var_not_implemented['til'] += [var]
#        else:
#            var1 = table1[var].fillna(0)
#            if (var1 == 0).all():
#                var_not_implemented['til'] += [var]
#        if var not in table2.columns:
#            var_not_implemented['pensipp'] += [var]
#        else:
#            var2 = table2[var].fillna(0)
#            if (var2 == 0).all():
#                var_not_implemented['pensipp'] += [var]
#
#        conflict = ((var1.abs() - var2.abs()).abs() > threshold)
#        if conflict.any():
#            var_conflict += [var]
#            print (u"Le calcul de {} pose problème pour {} personne(s) sur {}: ".format(var, sum(conflict), len(var1)))
#            print (pd.DataFrame({
#                "TIL": var1[conflict],
#                "PENSIPP": var2[conflict],
#                "diff.": var1[conflict].abs() - var2[conflict].abs()
#                }).to_string())
#        return conflict
#
#    var_conflict = []
#
#    all_prob = dict()
#    for var in var_to_check_montant:
#        all_prob[var] = _check_var(var, threshold['montant'], var_conflict)
#    for var in var_to_check_taux:
#        all_prob[var] = _check_var(var, threshold['taux'], var_conflict)
#
#    no_conflict = [variable for variable in var_to_check_montant + var_to_check_taux
#                        if variable not in var_conflict + var_not_implemented.values()]
#    print( u"Avec un seuil de {}, le calcul est faux pour les variables suivantes : {} \n " +
#           u"Il est mal implémenté dans : \n - Til: {} \n - Pensipp : {}\n " +
#           u"Il ne pose aucun problème pour : {}").format(threshold, var_conflict,
#                                                          var_not_implemented['til'], var_not_implemented['pensipp'],
#                                                          no_conflict)
#    for var, prob in all_prob.iteritems():
#        if sum(prob) != 0:
#            print ('Pour ' + var + ', on a ' + str(sum(prob)) + ' différences')
#    return all_prob
#
#if __name__ == '__main__':
#
#    var_to_check_montant = [ u'pension_RG', u'salref_RG', u'DA_RG', u'DA_RSI',
#                            u'nb_points_arrco', u'nb_points_agirc', u'pension_arrco', u'pension_agirc',
#                            u'DA_FP', u'pension_FP',
#                            u'n_trim_RG', 'N_CP_RG', 'n_trim_FP', 'salref_FP']
#    var_to_check_taux = [u'taux_RG', u'decote_RG', u'CP_RG', u'surcote_RG',
#                         u'taux_FP', u'decote_FP', u'CP_FP', u'surcote_FP']
#    threshold = {'montant' : 1, 'taux' : 0.0005}
#    to_print = ({'FP':['calculate_coeff_proratisation']}, [17917,21310,28332,28607], True)
#
#    til_compare, pensipp_compare, simul_til = load_til_pensipp(pensipp_comparison_path, years = [2004], to_print=(None,None,True))
#    prob = compare(til_compare, pensipp_compare, var_to_check_montant, var_to_check_taux, threshold)#, to_print, new_data=False)
#
#    #surcote RG
#
#
#
#    voir = prob['pension_agirc']
#    simul_til.calculate('trim_decote', 'agirc')[voir.values]
#    simul_til.calculate('minimum_points', 'agirc')[voir.values]
#
##     import pdb
##     pdb.set_trace()
#
#     voir = prob['salref_RG']
#     simul_til.calculate('salref', 'RG')[voir.values]
#     simul_til.calculate('salref', 'RG')[voir.values]
#
#
#     tt = pensipp_compare
#     tt['taux_RG']
#     tt['decote_RG'] - tt['surcote_RG']
#
#     voir = prob['DA_RSI']
#     (simul_til.calculate('nb_trimesters', 'RSI'))[voir.values]
#     (simul_til.calculate('trim_maj', 'RSI'))[voir.values]
#     (simul_til.calculate('trim_maj_mda_ini', 'RSI'))[voir.values]
#
#     data = simul_til.data
#     info_ind = data.info_ind
#
#
#     import pdb
#     pdb.set_trace()


#    or to have a profiler :
#    import cProfile
#    import re
#    command = """compare_til_pensipp(input_pensipp, output_pensipp, var_to_check_montant, var_to_check_taux, threshold)"""
#    cProfile.runctx( command, globals(), locals(), filename="profile_run_compare")