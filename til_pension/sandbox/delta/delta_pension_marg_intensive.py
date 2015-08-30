# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import gc
import pdb
from matching_patrimoine_eic.base.load_data import store_to_hdf
from til_pension.sandbox.eic.pensions_eic import compute_pensions_eic, load_eic_eir_data
from til_pension.sandbox.tri.compute_tri_vector import flow_contributions_matrix, nominal_to_reel, indices_prix
from til_pension.sandbox.tri.compute_tri_marg import Survival, tri_marginal, net_marginal_tax, pension_wealth

pss_path = "C:\\Users\l.pauldelvaux\Desktop\MThesis\Data\EIC\\pss.xlsx"


def mask_vector_dates(dates_col, vector_dates, cumulative):
    to_compare = np.ones(shape = (len(vector_dates), len(dates_col))) * dates_col
    if cumulative:
        mask = np.greater_equal(to_compare.transpose(), vector_dates).transpose()
    else:
        mask = np.equal(to_compare.transpose(), vector_dates).transpose()
    return mask.astype(int)


def delta_contributions_pensions(table, table_ref, vector = True):
    ''' This function returns a dataframe with:
    - delta_contributions (nominal + reel)
    - delta_pensions (nominal + reel)'''
    var_delta = ['pension', 'pension_reel', 'flowc_nominal', 'flowc_reel', 'flowc_moy_reel']
    ref = table_ref.copy()
    df = table.copy()
    del table_ref, table
    gc.collect()
    for var in var_delta:
        df_ini = df[var].copy()
        df.loc[:, 'delta_' + var] = df.loc[:, var].fillna(0) - ref.loc[:, var].fillna(0)
        try:
            assert (df['delta_' + var] >= - 1).all()
        except:
            print len(df.loc[df[var] < - 1, var])
            print df.loc[df[var] < - 1, var]
            print df_ini.loc[df[var] < - 1]
            print ref.loc[df[var] < - 1, var]
            pdb.set_trace()
            assert (df[var] >= - 1).all()
    to_keep = ['ident'] + ['delta_' + var for var in var_delta]
    return df[to_keep]


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


def delta_salbrut_age_start(data_initial, delta, age_start, cumulative, percent = False, nominal=True):
    ''' This function modifies the initial dataset to add a delta raise to wages:
        - if cumulative this delta is added to all years from age_start
        - if percent this raise is in percentage terms
        - if nominal: raise in euros of age_start year '''
    data = data_initial.copy()
    del data_initial
    gc.collect()
    info_ind = data['individus']
    dates_col = [int(col) for col in data['salbrut'].columns]
    year_start = info_ind['anaiss'] + age_start
    year_start = year_start * 100 + 1
    mask_delta = mask_vector_dates(dates_col, year_start.values, cumulative)
    if not cumulative:
        assert (mask_delta.sum(1) <= 1).all()
    if percent:
        data['salbrut'] = data['salbrut'] * (1 + delta * mask_delta)
    else:
        if nominal:
            delta_vect = delta / nominal_to_reel(np.ones(len(year_start)), year_start // 100)
            delta_vect = delta_vect.values
        else:
            delta_vect = np.ones(len(year_start))
        ini = (data['salbrut'] * mask_delta).sum(1)
        data['salbrut'] += (mask_delta.transpose() * delta_vect).transpose()
        assert (ini - (data['salbrut']*mask_delta).sum(1) <= delta_vect).all()
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
        data_temp = delta_salbrut_year_start(data, delta = delta,
                                             year_start = year_start, cumulative = cumulative)
    elif from_findet:
        prefixe = 'y' + str(from_findet)
        data_temp = delta_salbrut_nb_years_from_findet(data, delta = delta,
                                             nb_years_from_findet = from_findet,
                                             cumulative = cumulative)
    elif age_start:
        prefixe = 'y' + str(age_start)
        data_temp = delta_salbrut_age_start(data, delta = delta,
                                            age_start = age_start,
                                            cumulative = cumulative)
    assert initial_shape == data_temp['workstate'].shape
    assert initial_shape == data_temp['salbrut'].shape
    path_file_h5_temp = path_file_h5_initial[:-3] + '_temp.h5'
    store_to_hdf(data_temp, path_file_h5_temp)
    result_year_start = compute_pensions_eic(path_file_h5_temp, contribution = True)
    assert (result_year_start['pension'].isnull() == False).all()
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


def add_flows(result, survie, rates=[0.03]):
    result.loc[:, 'anaiss'] = result.loc[:, 'naiss'].apply(lambda x: int(str(x)[0:4]))
    result.loc[:, 'pcs'] = result.loc[:, 'pcs'].fillna(-1)
    result.loc[:, 'flowc_nominal'] = flow_contributions_matrix(result, vector=True, nominal=True)
    result.loc[:, 'flowc_reel'] = flow_contributions_matrix(result, vector=True, nominal=False)
    result.loc[:, 'flowc_moy_reel'] = flow_contributions_matrix(result, vector=True, nominal=False, taux_moyen=True)
    for r in rates:
        info_ind = result.loc[:, ['sexe', 'pcs', 'anaiss', 'ident', 'year_dep']]
        rate = (1 / (1 + r)) * np.ones(result.shape[0])
        result.loc[:, 'p_wealth_reel_r' + str(r)] = pension_wealth(rate, result, info_ind, survie,
                                                                   var_pension ='pension_reel',
                                                                   age_start = 60)
    return result


def initial_flows(path_file_h5_initial, survie):
    result_ini = compute_pensions_eic(path_file_h5_initial, contribution = True)
    result_ini.loc[:, 'pension_reel'] = nominal_to_reel(result_ini['pension'], result_ini['year_dep'])
    result_ini = add_flows(result_ini, survie)
    data_ini = load_eic_eir_data(path_file_h5_initial, to_return=True)
    w_m = wage_mean_lifecycle(data_ini['workstate'], data_ini['salbrut'])
    w_m = pd.DataFrame({'ident': w_m.index, 'w_m': w_m.values})
    result_ini = result_ini.merge(w_m, on='ident', how = 'left')
    return result_ini


def delta_flows(path_file_h5_initial, delta, survie,
                year_start = None, from_findet = None, age_start = None,
                cumulative = False, details = False):
    assert sum([x is not None for x in [year_start, from_findet, age_start]]) == 1
    result = delta_salbrut_throught_career(path_file_h5_initial, delta,
                                           year_start = year_start,
                                           from_findet = from_findet,
                                           age_start = age_start,
                                           cumulative = cumulative)
    for var in ['findet', 'naiss', 'year_dep', 'age', 'sexe', 'pension']:
        assert var in result.columns
        assert (result[var].isnull() == False).all()
    result.loc[:, 'pension_reel'] = nominal_to_reel(result['pension'], result['year_dep'])
    result = add_flows(result, survie)
    for var in ['findet', 'naiss', 'year_dep', 'age', 'sexe', 'pension']:
        assert var in result.columns
        assert (result[var].isnull() == False).all()
    if details:
        return result
    else:
        return result[['ident', 'pension', 'pension_reel', 'flowc_nominal', 'flowc_reel', 'flowc_moy_reel', 'sexe',
                       'workstate', 'year_dep', 'anaiss', 'findet', 'regime', 'pcs', 'p_wealth_reel_r0.03']]


def wage_mean_lifecycle(workstate, salbrut):
    selection = workstate.isin([4, 3, 2, 8, 15])
    nb_sal = selection.sum(axis=1)
    min_year = workstate.columns.min() // 100
    max_year = workstate.columns.max() // 100
    indices = indices_prix(min_year, max_year, return_dict = False)
    sal = salbrut.copy() * indices
    salbrut_sum = (selection * sal).sum(axis=1)
    return salbrut_sum / nb_sal


def pss_vector_from_Excel(miny, maxy, pss_file_path = pss_path):
    ''' This functions creates a dataframe with columns ['year', 'pss'] which provides the annual PSS per year '''
    pss_by_year = pd.ExcelFile(pss_file_path).parse('PSS')[['pss', 'date']].iloc[1:94, :]
    pss_by_year['date'] = pss_by_year['date'].astype(str).apply(lambda x: x[:4]).astype(int)
    pss_by_year.loc[pss_by_year.date < 2002, 'pss'] = pss_by_year.loc[pss_by_year.date < 2002, 'pss'] / 6.55957
    pss_by_year.rename(columns={'date': 'year'}, inplace=True)
    return pss_by_year.loc[(pss_by_year['year'] >= miny) & (pss_by_year['year'] <= maxy), :]


def salref_from_Excel(miny, maxy, salref_file_path = pss_path):
    ''' This functions creates a dataframe with columns ['year', 'salref'] which provides the annual PSS per year '''
    salref_by_year = pd.ExcelFile(salref_file_path).parse('salref')[['year', 'salref']]
    condition_euro = (salref_by_year.year < 2002)
    salref_by_year.loc[condition_euro, 'salref'] = salref_by_year.loc[condition_euro, 'salref'] / 6.55957
    return salref_by_year.loc[(salref_by_year['year'] >= miny) & (salref_by_year['year'] <= maxy), :]


def wage_pss(salbrut, info_ind, age):
    vector_dates = pd.DataFrame({'year': (info_ind['anaiss'] + age)})
    mask_sal = mask_vector_dates(salbrut.columns.values, vector_dates['year'].values * 100 + 1, False)
    min_year = salbrut.columns.min() // 100
    max_year = salbrut.columns.max() // 100
    pss = pss_vector_from_Excel(min_year, max_year).drop_duplicates('year')
    pss = vector_dates.merge(pss, on='year', how='left')['pss'].values / 4
    salref = salref_from_Excel(min_year, max_year).drop_duplicates('year')
    salref = vector_dates.merge(salref, on='year', how='left')['salref'].values
    sal_age = np.sum(mask_sal * salbrut.fillna(0), axis=1) // pss
    salref = np.sum(mask_sal * salbrut.fillna(0), axis=1) // salref
    return sal_age, salref


def delta_multi_scenarios(path_file_h5_initial, delta, scenarios = dict(), marginal = False, tri = False):
    ''' scenarios should be a dict with keys in (year_start , from_findet, age_start = None)
    and values the corresponding value the user wants to assign to this argument '''
    survie = Survival()
    survie.load_tables()
    result_ini = initial_flows(path_file_h5_initial, survie).reset_index(drop=True)
    results = [result_ini]
    to_keep = result_ini[['ident', 'regime']].copy()
    data_ini = load_eic_eir_data(path_file_h5_initial, to_return=True)
    salbrut = data_ini['salbrut']
    individus = data_ini['individus']
    for scenario in scenarios:
        print '  Implemented scenario: {}'.format(scenario)
        col_to_keep = ['pension', 'pension_reel', 'workstate', 'ident', 'flowc_reel', 'flowc_moy_reel']
        result_temp = delta_flows(path_file_h5_initial, delta, survie, details = False, **scenario)
        print result_temp.shape, result_ini.shape
        assert (result_temp['pension'].isnull() == False).all()
        result_temp = pd.merge(result_temp, to_keep, on=['ident', 'regime'], how = 'right')
        try:
            assert (result_temp['pension'].isnull() == False).all()
        except:
            print result_temp.shape, result_ini.shape
            print result_temp.loc[result_temp['pension'].isnull(), :]
            result_temp = result_temp.loc[~result_temp['pension'].isnull(), :]

        if marginal:
            delta_vars = delta_contributions_pensions(result_temp, result_ini)
            info_ind = result_temp[['year_dep', 'anaiss', 'findet', 'pcs', 'ident', 'sexe']]
            # net of tax rate
            for r in [0.02, 0.04, 0.06]:
                rate = ( 1 / (1 + r) ) * np.ones(result_temp.shape[0])
                result_temp.loc[:, 'net_marginal_' + str(r)] = net_marginal_tax(rate, delta_vars,
                                                                                info_ind, survie,
                                                                                nominal = False,
                                                                                taux_moyen = False,
                                                                                **scenario)
                result_temp.loc[:, 'net_marginal_moy_' + str(r)] = net_marginal_tax(rate, delta_vars,
                                                                                info_ind, survie,
                                                                                nominal = False,
                                                                                taux_moyen = True,
                                                                                **scenario)
            if tri:
                # TRI marginaux
                #delta_vars.loc[range(1,1000), :], info_ind.loc[range(1,1000)
                try:
                    tri_m = tri_marginal(delta_vars, info_ind, survie, nominal=False, **scenario)
                except:
                    tri_m = tri_marginal(delta_vars, info_ind, survie, nominal=False, **scenario)
                result_temp = result_temp.merge(delta_vars, on='ident').rename(columns={'delta_flowc_reel_y':
                                                                                        'delta_flowc_reel'})
                result_temp.loc[tri_m.index, 'delta_TRI'] = tri_m.values
                # tri_m2 = tri_marginal_apply(result_temp, survie, age_start = scenario['age_start'])

                # result_temp.loc[tri_m2.index, 'delta_TRI2'] = tri_m2.values
                col_to_keep += ['delta_TRI']

            del delta_vars
            gc.collect()
            if 'age_start' in scenario.keys():
                nb_pss, nb_salref = wage_pss(salbrut, individus, scenario['age_start'])
                nb_pss = pd.DataFrame({'ident': nb_pss.index, 'nb_pss': nb_pss.values})
                nb_salref = pd.DataFrame({'ident': nb_salref.index, 'nb_salref': nb_salref.values})
                result_temp = result_temp.merge(nb_pss, on='ident', how = 'left')
                result_temp = result_temp.merge(nb_salref, on='ident', how = 'left')
            col_to_keep += ['p_wealth_reel_r0.03', 'net_marginal_0.02', 'net_marginal_0.04',
                            'net_marginal_0.06', 'nb_pss', 'nb_salref']
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
        scenarios_age_start = [{'age_start': age} for age in range(18, 66, 2)]
        for delta in [12, 120]:
            print delta
            age_start = delta_multi_scenarios(path_file_h5_initial, delta = delta,
                                          scenarios = scenarios_age_start,
                                          marginal = True)

            age_start.to_csv('final_from_agestart' + str(delta) + '.csv', sep=';', decimal='.')
        print " Le scénarios avec salaire additionnel selon l'âge a été sauvegardé"
    if option_scenarios in ['findet', 'all']:
        findet = dict()
        for delta in [1, 10, 100]:
            print delta
            scenarios_findet = [{'from_findet': nb_y} for nb_y in range(4, 50, 2)]
            findet[delta] = delta_multi_scenarios(path_file_h5_initial, delta,
                                                 scenarios = scenarios_findet,
                                                 marginal = True)
            findet[delta].to_csv('final_from_findet_' + str(delta) + '.csv', sep=';', decimal='.')
            " Le scénarios avec salaire additionnel selon l'âge de fin d'étude a été sauvegardé"
