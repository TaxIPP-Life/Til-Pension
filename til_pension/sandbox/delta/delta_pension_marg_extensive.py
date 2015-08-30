# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import gc
from matching_patrimoine_eic.base.load_data import store_to_hdf
from til_pension.sandbox.eic.pensions_eic import compute_pensions_eic, load_eic_eir_data
from til_pension.sandbox.tri.compute_tri_vector import nominal_to_reel
from til_pension.sandbox.tri.compute_tri_marg import Survival, tri_marginal, net_marginal_tax
#TODO: create a separate file with generic functions
from delta_pension_intensive import wage_mean_lifecycle, wage_pss, delta_contributions_pensions, mask_vector_dates


def delta_workstate_year_start(data_initial, delta, year_start, cumulative):
    data = data_initial.copy()
    del data_initial
    gc.collect()
    if cumulative:
        data['salbrut'].columns = [int(col) for col in data['salbrut'].columns]
        year_max = max(data['salbrut'].columns) // 100
        col_to_change = [year * 100 + 1 for year in range(year_start, year_max)]
    else:
        col_to_change = [year_start * 100 + 1]
    data['salbrut'].loc[:, col_to_change] += delta
    return data


def delta_workstate_nb_years_from_findet(data_initial, delta, nb_years_from_findet, cumulative, percent = False):
    shape_ini = data_initial['workstate'].shape
    data = data_initial.copy()
    del data_initial
    gc.collect()
    info_ind = data['individus']
    dates_col = [int(col) for col in data['salbrut'].columns]
    year_start = info_ind['anaiss'] + info_ind['findet'] + nb_years_from_findet
    year_start = year_start * 100 + 1
    mask_delta = mask_vector_dates(dates_col, year_start.values, cumulative)
    assert mask_delta.shape == data['salbrut'].shape
    if not cumulative:
        assert (mask_delta.sum(1) <= 1).all()
    if percent:
        data['salbrut'] = data['salbrut'] * (1 + delta * mask_delta)
    else:
        ini = data['salbrut'].mean(1)
        data['salbrut'] += delta * mask_delta
        assert (ini - data['salbrut'].mean(1) <= delta).all()
    assert shape_ini == data['salbrut'].shape
    return data


def delta_workstate_age_start(data_initial, delta, age_start, workstates_equivalence, cumulative):
    data = data_initial.copy()
    del data_initial
    gc.collect()
    info_ind = data['individus']
    dates_col = [int(col) for col in data['salbrut'].columns]
    year_start = info_ind['anaiss'] + age_start
    year_start = year_start * 100 + 1
    mask_delta = mask_vector_dates(dates_col, year_start.values, cumulative)
    workstate = data['workstate']
    salbrut = data['salbrut']
    workstate[mask_delta] = workstate[mask_delta].replace(workstates_equivalence)
    data['workstate'] = workstate
    salbrut[mask_delta] = np.nan
    return data


def workstate_delta(data, year_start = None, from_findet = None, age_start = None):
    workstate = data['workstate']
    individus = data['individus']
    dates_col = [int(col) for col in data['salbrut'].columns]
    if year_start:
        return workstate[year_start]
    if from_findet:
        year_start = individus['anaiss'] + individus['findet'] + from_findet
        year_start = year_start * 100 + 1
        select = workstate * mask_vector_dates(dates_col, year_start.values, False)
        return select.max(axis=1)
    if age_start:
        year_start = individus['anaiss'] + age_start
        year_start = year_start * 100 + 1
        select = workstate * mask_vector_dates(dates_col, year_start.values, False)
        return select.max(axis=1)


def delta_workstate_career(path_file_h5_initial, delta,
                           year_start = None, from_findet = None, age_start = None,
                           cumulative = True, rename = False):
    assert sum([x is not None for x in [year_start, from_findet, age_start]]) == 1
    data = load_eic_eir_data(path_file_h5_initial, to_return=True)
    initial_shape = data['workstate'].shape
    if year_start:
        prefixe = 'y' + str(year_start)
        data_temp = delta_workstate_year_start(data, delta = 1,
                                               year_start = year_start, cumulative = cumulative)
    elif from_findet:
        prefixe = 'y' + str(from_findet)
        data_temp = delta_workstate_nb_years_from_findet(data, delta = 1,
                                                         nb_years_from_findet = from_findet,
                                                         cumulative = cumulative)
    elif age_start:
        prefixe = 'y' + str(age_start)
        data_temp = delta_workstate_age_start(data, delta = 1,
                                              age_start = age_start,
                                              cumulative = cumulative)
    assert initial_shape == data_temp['workstate'].shape
    assert initial_shape == data_temp['salbrut'].shape
    path_file_h5_temp = path_file_h5_initial[:-3] + '_temp.h5'
    store_to_hdf(data_temp, path_file_h5_temp)
    result_year_start = compute_pensions_eic(path_file_h5_temp, contribution = True)
    result_year_start.set_index('ident', inplace = True)
    result_year_start.loc[:, 'workstate'] = workstate_delta(data_temp,
                                                            year_start = year_start,
                                                            from_findet = from_findet,
                                                            age_start = age_start)
    result_year_start.reset_index(inplace=True)
    if rename:
        dates_contrib = [col for col in result_year_start.columns if col[:2] in ['19', '20']]
        renamed = dict([(date, 'contrib_' + prefixe + '_' + date) for date in dates_contrib])
        renamed.update({'pension': 'pension_' + str(prefixe)})
        result_year_start.rename(columns=renamed, inplace=True)
    return result_year_start


def delta_flows(path_file_h5_initial, delta, survie,
                year_start = None, from_findet = None, age_start = None,
                cumulative = False, details = False):
    assert sum([x is not None for x in [year_start, from_findet, age_start]]) == 1
    result = delta_workstate_career(path_file_h5_initial, delta,
                                    year_start = year_start,
                                    from_findet = from_findet,
                                    age_start = age_start,
                                    cumulative = cumulative)
    for var in ['findet', 'naiss', 'year_dep', 'age', 'sexe', 'pension']:
        assert var in result.columns
        assert (result[var].isnull() == False).all()
    result.loc[:, 'pension_reel'] = nominal_to_reel(result['pension'], result['year_dep'])
    for var in ['findet', 'naiss', 'year_dep', 'age', 'sexe', 'pension']:
        assert var in result.columns
        assert (result[var].isnull() == False).all()
    if details:
        return result
    else:
        return result[['ident', 'pension', 'pension_reel', 'flowc_nominal', 'flowc_reel', 'flowc_moy_reel', 'sexe',
                       'workstate', 'year_dep', 'anaiss', 'findet', 'regime', 'pcs', 'p_wealth_reel_r0.03']]


def initial_flows(path_file_h5_initial):
    result_ini = compute_pensions_eic(path_file_h5_initial, contribution = True)
    result_ini.loc[:, 'pension_reel'] = nominal_to_reel(result_ini['pension'], result_ini['year_dep'])
    data_ini = load_eic_eir_data(path_file_h5_initial, to_return=True)
    w_m = wage_mean_lifecycle(data_ini['workstate'], data_ini['salbrut'])
    w_m = pd.DataFrame({'ident': w_m.index, 'w_m': w_m.values})
    result_ini = result_ini.merge(w_m, on='ident', how = 'left')
    return result_ini


def delta_multi_scenarios(path_file_h5_initial, delta, scenarios = dict(), marginal = False):
    ''' scenarios should be a dict with keys in (year_start , from_findet, age_start = None)
    and values the corresponding value the user wants to assign to this argument '''
    result_ini = initial_flows(path_file_h5_initial).reset_index(drop=True)
    results = [result_ini]
    to_keep = result_ini[['ident', 'regime']].copy()
    data_ini = load_eic_eir_data(path_file_h5_initial, to_return=True)
    salbrut = data_ini['salbrut']
    individus = data_ini['individus']
    survie = Survival()
    survie.load_tables()
    for scenario in scenarios:
        print '  Implemented scenario: {}'.format(scenario)
        col_to_keep = ['pension', 'flowc_nominal', 'flowc_reel', 'workstate', 'ident']
        result_temp = delta_flows(path_file_h5_initial, delta, survie, details = False, **scenario)
        result_temp.loc[:, 'pension_reel'] = nominal_to_reel(result_temp['pension'], result_temp['year_dep'])
        result_temp = pd.merge(result_temp, to_keep, on=['ident', 'regime'], how='right').reset_index(drop=True)
        print result_temp.shape, result_ini.shape
        if scenario['age_start']:
            nb_pss, nb_salref = wage_pss(salbrut, individus, scenario['age_start'])
            nb_pss = pd.DataFrame({'ident': nb_pss.index, 'nb_pss': nb_pss.values})
            nb_salref = pd.DataFrame({'ident': nb_salref.index, 'nb_salref': nb_salref.values})
            result_temp = result_temp.merge(nb_pss, on='ident', how = 'left')
            result_temp = result_temp.merge(nb_salref, on='ident', how = 'left')
        if marginal:
            delta_vars = delta_contributions_pensions(result_temp, result_ini)
            info_ind = result_temp[['year_dep', 'anaiss', 'findet', 'pcs', 'ident', 'sexe']]

            # net of tax rate
            for r in [0.02, 0.04, 0.06]:
                rate = (1 / (1 + r)) * np.ones(result_temp.shape[0])
                result_temp.loc[:, 'net_marginal_' + str(r)] = net_marginal_tax(rate, delta_vars,
                                                                                info_ind, survie,
                                                                                nominal = False, **scenario)

            # TRI marginaux
            tri_m = tri_marginal(delta_vars, info_ind, survie, nominal=False, **scenario)
            result_temp.loc[tri_m.index, 'delta_TRI'] = tri_m.values
            del delta_vars
            gc.collect()
            col_to_keep += ['delta_TRI', 'net_marginal_0.02', 'net_marginal_0.04', 'net_marginal_0.06', 'nb_pss', 'nb_salref']  # , 'delta_TRI_nom']
        result_temp = result_temp[col_to_keep]
        suffixe = '_' + scenario.keys()[0] + str(scenario.values()[0])
        to_rename = dict([(col, col + suffixe) for col in result_temp.columns
                  if col not in ['noind', 'regime', 'ident']])
        result_temp = result_temp.rename(columns=to_rename)
        results += [result_temp]
    to_return = pd.concat(results, axis=1)
    colist = list(to_return.columns)
    try:
        to_return = to_return.reindex_axis(sorted(to_return.columns), axis=1)
    except:
        for col in colist:
            if colist.count(col) > 1:
                print col
    return to_return

if __name__ == '__main__':
    test = False
    option_scenarios = 'age_start'
    if test:
        path_file_h5_initial = 'C:\\Users\\l.pauldelvaux\\Desktop\\MThesis\\Data\\test_modified.h5'
    else:
        path_file_h5_initial = 'C:\\Users\\l.pauldelvaux\\Desktop\\MThesis\\Data\\modified.h5'
    if option_scenarios in ['age_start', 'all']:
        scenarios_age_start = [{'age_start': age} for age in range(16, 66, 2)]
        age_start = delta_multi_scenarios(path_file_h5_initial, 1,
                                          scenarios = scenarios_age_start,
                                          marginal = True)

        age_start.to_csv('final_from_agestart_extensive.csv', sep=';', decimal='.')
        print " Le scénarios avec salaire additionnel selon l'âge a été sauvegardé"
