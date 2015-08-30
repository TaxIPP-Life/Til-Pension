# -*- coding: utf-8 -*-
import numpy as np
from til_pension.sandbox.compare.compare_eir import compare_eir
from til_pension.sandbox.eic.load_eic import load_eic_eir_data, rework_on_earnings
from matching_patrimoine_eic.base.load_data import store_to_hdf
from matching_patrimoine_eic.matching.format_careers import imputation_years_missing_dads


def impute_years(row_ini):
    row = row_ini.copy()
    nb_to_impute = min(row.nb_years_to_impute, 5)
    print "Inital", nb_to_impute
    nb_imputed = 0
    dates = list(row.keys())
    row.drop('nb_years_to_impute', inplace = True)
    lnull = list(row[: -1].isnull().astype(int))
    first_valid = lnull.index(0)
    last_valid = len(lnull) - lnull[::-1].index(0)
    index_between = [idx for idx, val in enumerate(lnull)
                    if val == 1 and idx > first_valid and idx < last_valid]
    index_before = [idx for idx, val in enumerate(lnull) if val == 1 and idx < first_valid]
    if index_between != [] and nb_to_impute > 0:
        for ident in index_between:
            if nb_to_impute > 0:
                missing_to_impute = dates[ident]
                year_ref = dates[ident - 1]
                row[missing_to_impute] = row[year_ref]
                print ident, year_ref, missing_to_impute
                nb_to_impute = nb_to_impute - 1
                nb_imputed += 1
    if first_valid != 0 and nb_to_impute > 0 and index_before != []:
        for ident in index_before:
            idx_before = first_valid - 1
            while nb_to_impute > 0 and idx_before != 0:
                year_ref = dates[first_valid]
                missing_to_impute = dates[idx_before]
                row[missing_to_impute] = row[year_ref]
                idx_before = idx_before - 1
                nb_to_impute -= 1
                print ident, year_ref, missing_to_impute
                nb_imputed += 1
    print " Nb of years imputed: {} ".format(nb_imputed)
    return row


def impute_cot_years(workstate, delta_trim_cot):
    workstate.loc[:, 'nb_years_to_impute'] = - delta_trim_cot // 4
    print workstate.loc[:, 'nb_years_to_impute'].value_counts()
    workstate = workstate.apply(impute_years, axis = 1)
    assert 'nb_years_to_impute' not in workstate
    return workstate


def preliminary_imputation_from_compare(path_file_h5_ini):
    data_ini = load_eic_eir_data(path_file_h5_eic, to_return=True)
    compare_ini = compare_eir(path_file_h5_ini).set_index('noind')
    workstate = data_ini['workstate']
    salbrut = data_ini['salbrut']
    workstate = impute_cot_years(workstate, compare_ini.loc[compare_ini['regime'] == 'RG', 'delta_trim_cot'])
    salbrut = rework_on_earnings(salbrut.copy(), workstate.copy())
    salbrut, workstate = imputation_years_missing_dads(salbrut, workstate)
    imputed_data = {'workstate': workstate,
                    'salbrut': salbrut,
                    'individus': data_ini['individus'],
                    'pension_eir': data_ini['pension_eir']}
    return imputed_data


def select_data(data, test = False, hdf_store = True, limit_difference = 12.0):
    # Define path for saving data
    store_to_hdf(data, 'temp.h5')
    compare = compare_eir('temp.h5')
    ind_to_keep = list(set(compare.loc[(compare['regime'] == 'RG') & (compare['delta_trim_cot'].abs() <=
                            limit_difference) * (compare['delta_brute'].abs() <= 150), 'noind']))
    findet_condition = list(set(data['individus'].loc[data['individus']['findet'] <= 26, 'sexe'].index))
    ind_to_keep = set(ind_to_keep).intersection(findet_condition)
    compare = compare.loc[compare.noind.isin(ind_to_keep), :]
    compare = compare.loc[compare['regime'].isin(['RG', 'agirc', 'arrco'])]
    compare = compare.set_index('noind')
    assert compare.loc[:, 'delta_trim_cot'].max() <= limit_difference
    for dataset in data.keys():
        data[dataset] = data[dataset].loc[data[dataset].index.isin(ind_to_keep), :].copy()
    workstate = data['workstate'].copy()
    salbrut = data['salbrut'].copy()
    individus = data['individus']
    trim_maj_RG = - (compare.loc[compare['regime'] == 'RG', 'delta_trim_tot'] -
                    compare.loc[compare['regime'] == 'RG', 'delta_trim_cot'])
    individus.loc[:, 'trim_other_RG'] = np.minimum(np.maximum(trim_maj_RG, 0), 12)
    individus.loc[:, 'trim_other_RG'] = np.maximum(trim_maj_RG, 0)
    individus.loc[:, 'pcs'] = individus['pcs'].fillna(-1)
    assert (workstate.columns == salbrut.columns).all()
    assert workstate.shape[0] == salbrut.shape[0] == individus.shape[0]
    def nan_dataset(dataset):
        nb_nan = 0
        for col in dataset.columns:
            nb_nan += sum(dataset[col].astype(float).isnull())
        return nb_nan

    nan_sal = nan_dataset(salbrut)
    nan_work = nan_dataset(workstate)
    print nan_sal, nan_work
    salbrut[workstate.isnull()] = np.nan
    print nan_dataset(salbrut)
    selected_data = {'workstate': workstate,
                    'salbrut': salbrut,
                    'individus': individus,
                    'pension_eir': data['pension_eir']}
    if hdf_store:
        if test:
            path_store = 'C:\\Users\\l.pauldelvaux\\Desktop\\MThesis\\Data\\test_modified.h5'
        else:
            path_store = 'C:\\Users\\l.pauldelvaux\\Desktop\\MThesis\\Data\\modified.h5'
        store_to_hdf(selected_data, path_store)
    else:
        return selected_data


def select_generation(path_hdf, generation, hdf_store = True):
    df = load_eic_eir_data(path_hdf, to_return = True)
    data = df.copy()
    individus = data['individus']
    ind_to_keep = list(set(individus.loc[individus['anaiss'] == generation, :].index))
    for dataset in data.keys():
        data[dataset] = data[dataset].loc[data[dataset].index.isin(ind_to_keep), :].copy()
    if hdf_store:
        if test:
            path_store = 'C:\\Users\\l.pauldelvaux\\Desktop\\MThesis\\Data\\test_modified' + str(generation) + '.h5'
        else:
            path_store = 'C:\\Users\\l.pauldelvaux\\Desktop\\MThesis\\Data\\modified' + str(generation) + '.h5'
        store_to_hdf(data, path_store)
        return data
    else:
        return data


if __name__ == '__main__':
    test = False
    if test:
        path_file_h5_eic = 'C:\\Users\\l.pauldelvaux\\Desktop\\MThesis\\Data\\test_final.h5'
    else:
        path_file_h5_eic = 'C:\\Users\\l.pauldelvaux\\Desktop\\MThesis\\Data\\final.h5'

    #to_keep_imputation = ['noind', 'trim_cot_til', 'trim_cot', 'trim_tot_til', 'trim_tot',
    #                     'delta_trim_tot', 'delta_trim_cot']
    #data_ini = load_eic_eir_data(path_file_h5_eic, to_return=True)
    #imputed_data = preliminary_imputation_from_compare(path_file_h5_eic)
    #selected_data = select_data(imputed_data.copy(),
    #                                     test = test,
    #                                     hdf_store = False)
    test = select_generation('C:\\Users\\l.pauldelvaux\\Desktop\\MThesis\\Data\\modified.h5', 1942, hdf_store = True)
