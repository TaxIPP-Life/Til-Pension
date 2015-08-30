# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import gc
import pdb
from functools import partial
from matching_patrimoine_eic.base.load_data import store_to_hdf
from til_pension.sandbox.eic.pensions_eic import compute_pensions_eic, load_eic_eir_data
from til_pension.sandbox.tri.compute_TRI import flow_pensions
from til_pension.sandbox.tri.compute_tri_vector import tri, flow_contributions_mat, nominal_to_reel
from til_pension.sandbox.tri.compute_tri_marg import Survival


def mask_vector_dates(dates_col, vector_dates, cumulative):
    to_compare = np.ones(shape = (len(vector_dates), len(dates_col))) * dates_col
    if cumulative:
        mask = np.greater_equal(to_compare.transpose(), vector_dates).transpose()
    else:
        mask = np.equal(to_compare.transpose(), vector_dates).transpose()
    return mask.astype(int)


def delta_contributions_pensions(table, table_ref):
    ''' This function returns a dataframe with the same structure than the initial ones
    but replace contributions and pensions by the differences '''
    dates_contrib = [col for col in table_ref.columns if str(col)[0:2] in ['19', '20']]
    ref = table_ref.copy()
    df = table.copy()
    del table_ref, table
    df.loc[:, dates_contrib] = df.loc[:, dates_contrib].values - ref.loc[:, dates_contrib].values
    gc.collect()
    for var in ['pension', 'pension_reel']:
        df_ini = df[var].copy()
        df.loc[:, var] = df.loc[:, var].fillna(0) - ref.loc[:, var].fillna(0)
        try:
            assert (df[var] >= - 1).all()
        except:
            print len(df.loc[df[var] < - 1, var])
            print df.loc[df[var] < - 1, var]
            print df_ini.loc[df[var] < - 1]
            print ref.loc[df[var] < - 1, var]
            pdb.set_trace()
            assert (df[var] >= - 1).all()
    return df


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


def delta_salbrut_nb_years_from_findet(data_initial, delta, nb_years_from_findet, cumulative, percent = False):
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


def delta_salbrut_age_start(data_initial, delta, age_start, cumulative):
    data = data_initial.copy()
    del data_initial
    gc.collect()
    info_ind = data['individus']
    dates_col = [int(col) for col in data['salbrut'].columns]
    year_start = info_ind['anaiss'] + age_start
    year_start = year_start * 100 + 1
    mask_delta = mask_vector_dates(dates_col, year_start.values, cumulative)
    data['salbrut'].loc[:, :] += delta * mask_delta
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


def delta_salbrut_throught_career(path_file_h5_initial, delta,
                                  year_start = None, from_findet = None, age_start = None,
                                  cumulative = True, rename = False):
    assert sum([x is not None for x in [year_start, from_findet, age_start]]) == 1
    data = load_eic_eir_data(path_file_h5_initial, to_return=True)
    initial_shape = data['workstate'].shape
    if year_start:
        prefixe = 'y' + str(year_start)
        data_temp = delta_salbrut_year_start(data, delta = 1,
                                             year_start = year_start, cumulative = cumulative)
    elif from_findet:
        prefixe = 'y' + str(from_findet)
        data_temp = delta_salbrut_nb_years_from_findet(data, delta = 1,
                                             nb_years_from_findet = from_findet,
                                             cumulative = cumulative)
    elif age_start:
        prefixe = 'y' + str(age_start)
        data_temp = delta_salbrut_age_start(data, delta = 1,
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


def add_flows(result):
    result.loc[:, 'anaiss'] = result.loc[:, 'naiss'].apply(lambda x: int(str(x)[0:4]))
    esperances = [(1, 1942, 26), (1, 1946, 27), (1, 1950, 27),
                  (0, 1942, 21), (0, 1946, 22), (0, 1950, 22)]
    esperances_blanpain = [(1, 4, 47), (1, 5, 46), (1, 1, 45), (1, 2, 46), (1, 3, 44), (1, -1, 46),
                           (0, 4, 41), (0, 5, 41), (0, 1, 40), (0, 2, 40), (0, 3, 35), (0, -1, 40)]
    result.loc[:, 'pcs'] = result['pcs'].copy().convert_objects(convert_numeric=True)
    result.loc[result['pcs'].isnull(), 'pcs'] = -1
    for sexe, pcs, years in esperances_blanpain:
        result.loc[(result['sexe'] == sexe) & (result['pcs'] == pcs), 'death'] = result['anaiss'] + years + 35
    try:
        assert (result.death.isnull() == 0).all()
    except:
        # assert (result.loc[result['death'].isnull(), 'anaiss'] > max_anaiss).all()
        result = result.loc[~result['death'].isnull(), :]
        assert (result.death.isnull() == 0).all()
    result.loc[:, 'flowc_nominal'] = flow_contributions_mat(result, vector=False, nominal=True)
    result.loc[:, 'flowc_reel'] = flow_contributions_mat(result, vector=False, nominal=False)
    result.loc[:, 'flowp_nominal'] = result.apply(partial(flow_pensions, vector=False), axis=1)
    result.loc[:, 'flowp_reel'] = result.apply(partial(flow_pensions, vector=False, nominal=False), axis=1)
    return result


def initial_flows(path_file_h5_initial):
    result_ini = compute_pensions_eic(path_file_h5_initial, contribution = True)
    result_ini = add_flows(result_ini)
    result_ini.loc[:, 'pension_reel'] = nominal_to_reel(result_ini['pension'], result_ini['year_dep'])
    return result_ini


def delta_flows(path_file_h5_initial, delta,
                year_start = None, from_findet = None, age_start = None,
                cumulative = False, details = False):
    assert sum([x is not None for x in [year_start, from_findet, age_start]]) == 1
    result = delta_salbrut_throught_career(path_file_h5_initial, delta,
                                  year_start = year_start,
                                  from_findet = from_findet,
                                  age_start = age_start,
                                  cumulative = cumulative)
    for var in ['findet', 'naiss', 'year_dep', 'age', 'sexe']:
        assert var in result.columns
        assert (result[var].isnull() == False).all()
    result = add_flows(result)
    if details:
        return result
    else:
        return result[['ident', 'pension', 'flowc_nominal', 'flowc_reel',
                       'flowp_nominal', 'flowp_reel', 'workstate']]


def delta_multi_scenarios(path_file_h5_initial, delta, scenarios = dict(), delta_tri = False):
    ''' scenarios should be a dict with keys in (year_start , from_findet, age_start = None)
    and values the corresponding value the user wants to assign to this argument '''
    result_ini = initial_flows(path_file_h5_initial).reset_index(drop=True)
    results = [result_ini]
    to_keep = result_ini[['ident', 'regime']].copy()
    survie = Survival()
    survie.load_tables()
    for scenario in scenarios:
        print '  Implemented scenario: {}'.format(scenario)
        col_to_keep = ['pension', 'flowc_nominal', 'flowc_reel', 'flowp_nominal', 'flowp_reel', 'workstate']
        result_temp = delta_flows(path_file_h5_initial, delta, details = True, **scenario)
        result_temp.loc[:, 'pension_reel'] = nominal_to_reel(result_temp['pension'], result_temp['year_dep'])
        result_temp = pd.merge(result_temp, to_keep, on=['ident', 'regime'], how='right').reset_index(drop=True)
        print result_temp.shape, result_ini.shape
        suffixe = '_' + scenario.keys()[0] + str(scenario.values()[0])
        if delta_tri:
            delta_contrib = delta_contributions_pensions(result_temp, result_ini)
            result_temp.loc[:, 'delta_TRI'] = tri(delta_contrib, nominal=False, marginal=True)
            del delta_contrib
            gc.collect()
            col_to_keep += ['delta_TRI']  # , 'delta_TRI_nom']
        result_temp = result_temp[col_to_keep]
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
        scenarios_age_start = [{'age_start': age} for age in range(44, 66, 2)]
        age_start = delta_multi_scenarios(path_file_h5_initial, 1,
                                 scenarios = scenarios_age_start,
                                 delta_tri = True)
        age_start.to_csv('final_from_agestart.csv', sep=';', decimal='.')
        print " Le scénarios avec salaire additionnel selon l'âge a été sauvegardé"
    if option_scenarios in ['findet', 'all']:
        findet = dict()
        for delta in [1, 10, 100]:
            print delta
            scenarios_findet = [{'from_findet': nb_y} for nb_y in range(4, 50, 2)]
            findet[delta] = delta_multi_scenarios(path_file_h5_initial, delta,
                                         scenarios = scenarios_findet,
                                         delta_tri = True)
            findet[delta].to_csv('final_from_findet_' + str(delta) + '.csv', sep=';', decimal='.')
        print " Le scénarios avec salaire additionnel selon l'âge de fin d'étude a été sauvegardé"
