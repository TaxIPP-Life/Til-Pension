# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import gc
from functools import partial
from matching_patrimoine_eic.base.load_data import store_to_hdf
from til_pension.sandbox.eic.pensions_eic import compute_pensions_eic, load_eic_eir_data
from til_pension.sandbox.tri.compute_TRI import flow_contributions, flow_pensions


def mask_vector_dates(dates_col, vector_dates):
    to_compare = np.ones(shape = (len(vector_dates), len(dates_col))) * dates_col
    mask = np.greater_equal(to_compare.transpose(), vector_dates).transpose()
    return mask.astype(int)


def delta_salbrut_year_start(data_initial, delta, year_start, cumulative):
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


def delta_salbrut_nb_years_from_findet(data_initial, delta, nb_years_from_findet, cumulative):
    data = data_initial.copy()
    del data_initial
    gc.collect()
    info_ind = data['individus']
    dates_col = [int(col) for col in data['salbrut'].columns]
    year_start = info_ind['anaiss'] + info_ind['findet'] + nb_years_from_findet
    year_start = year_start * 100 + 1
    mask_delta = mask_vector_dates(dates_col, year_start.values)
    data['salbrut'].loc[:, :] = data['salbrut'].values * (1 + delta * mask_delta)
    return data


def delta_salbrut_age_start(data_initial, delta, age_start, cumulative):
    data = data_initial.copy()
    del data_initial
    gc.collect()
    info_ind = data['individus']
    dates_col = [int(col) for col in data['salbrut'].columns]
    year_start = info_ind['anaiss'] + age_start
    year_start = year_start * 100 + 1
    mask_delta = mask_vector_dates(dates_col, year_start.values)
    data['salbrut'].loc[:, :] = data['salbrut'].values * (1 + delta * mask_delta)
    return data


def delta_salbrut_throught_career(path_file_h5_initial, delta,
                                  year_start = None, nb_years_from_findet = None, age_start = None,
                                  cumulative = True, rename = False):
    assert sum([x is not None for x in [year_start, nb_years_from_findet, age_start]]) == 1
    data = load_eic_eir_data(path_file_h5_initial, to_return=True)
    if year_start:
        prefixe = 'y' + str(year_start)
        data_temp = delta_salbrut_year_start(data, delta = 1,
                                             year_start = year_start, cumulative = cumulative)
    elif nb_years_from_findet:
        prefixe = 'y' + str(nb_years_from_findet)
        data_temp = delta_salbrut_nb_years_from_findet(data, delta = 1,
                                             nb_years_from_findet = nb_years_from_findet,
                                             cumulative = cumulative)
    elif age_start:
        prefixe = 'y' + str(age_start)
        data_temp = delta_salbrut_age_start(data, delta = 1,
                                    age_start = age_start,
                                    cumulative = cumulative)
    path_file_h5_temp = path_file_h5_initial[:-3] + '_temp.h5'
    store_to_hdf(data_temp, path_file_h5_temp)
    result_year_start = compute_pensions_eic(path_file_h5_temp, contribution = True)
    if rename:
        dates_contrib = [col for col in result_year_start.columns if col[:2] in ['19', '20']]
        renamed = dict([(date, 'contrib_' + prefixe + '_' + date) for date in dates_contrib])
        renamed.update({'pension': 'pension_start_delta_' + str(prefixe)})
        result_year_start.rename(columns=renamed, inplace=True)
    return result_year_start


def add_flows(result):
    result.loc[:, 'death'] = (result['year_dep'] - (result['age'] - 60) + 22).astype(float)
    result.loc[:, 'flow_contrib_nominal'] = result.apply(partial(flow_contributions, vector = False), axis=1)
    result.loc[:, 'flow_contrib_reel'] = result.apply(partial(flow_contributions, vector = False, nominal=False),
                                                      axis=1)
    result.loc[:, 'flow_pension_nominal'] = result.apply(partial(flow_pensions, vector = False), axis=1)
    result.loc[:, 'flow_pension_reel'] = result.apply(partial(flow_pensions, vector = False, nominal=False), axis=1)
    return result


def initial_flows(path_file_h5_initial):
    result_ini = compute_pensions_eic(path_file_h5_initial, contribution = True)
    result_ini = add_flows(result)
    return result_ini


def delta_flows(path_file_h5_initial, delta,
                year_start = None, nb_years_from_findet = None, age_start = None,
                cumulative = True, details = False):
    assert sum([x is not None for x in [year_start, nb_years_from_findet, age_start]]) == 1
    result = delta_salbrut_throught_career(path_file_h5_initial, delta,
                                  year_start = year_start,
                                  nb_years_from_findet = nb_years_from_findet,
                                  age_start = age_start,
                                  cumulative = cumulative)
    result = add_flows(result)
    if details:
        return result
    else:
        return result[['ident', 'pension', 'flow_contrib_nominal', 'flow_contrib_reel',
                       'flow_pension_nominal', 'flow_pension_reel']]


def delta_multi_scenarios(path_file_h5_initial, delta, scenarios = dict()):
    ''' scenarios should be a dict with keys in (year_start , nb_years_from_findet, age_start = None)
    and values the corresponding value the user wants to assign to this argument '''
    result = dict()
    result['ini'] = initial_flows(path_file_h5_initial)
    for scenario in scenarios:
        result_temp = delta_flows(path_file_h5_initial, delta, **scenario)
        suffixe = '_' + scenario.keys()[0] + str(scenario.values()[0])
        to_rename = dict([(col, col + suffixe) for col in result_temp.columns
                          if col not in ['noind', 'regime']])
        result_temp = result_temp.rename(columns=to_rename)
        result[suffixe] = result_temp
    to_return = pd.concat(result.values(), axis=1)
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
    if test:
        path_file_h5_initial = 'C:\\Users\\l.pauldelvaux\\Desktop\\MThesis\\Data\\test_final.h5'
    else:
        path_file_h5_initial = 'C:\\Users\\l.pauldelvaux\\Desktop\\MThesis\\Data\\final.h5'
    result = delta_salbrut_throught_career(path_file_h5_initial,
                                           nb_years_from_findet=10,
                                           delta=1, cumulative=True)
    scenarios_age_start = [{'age_start': 25},
                           {'age_start': 35},
                            {'age_start': 45}]
    scenarios_findet = [{'nb_years_from_findet': nb_y} for nb_y in range(5, 45, 5)]
    findet = delta_multi_scenarios(path_file_h5_initial, 1,
                                 scenarios = scenarios_findet)
    findet.to_csv('final_from_findet.csv', sep=';')
