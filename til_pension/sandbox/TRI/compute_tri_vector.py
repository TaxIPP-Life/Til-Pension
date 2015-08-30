# -*- coding: utf-8 -*-
import gc
import numpy as np
import pandas as pd
from numpy import nan_to_num
from functools import partial
try:
    from scipy.optimize import root
except:
    pass

# TODO: Tres tres moche et donc a refaire
path_xlsx = "C:\Users\l.pauldelvaux\Desktop\MThesis\Data\indices_prix.xlsx"


def add_pension(row, nominal=True):
    year_dep = int(row['year_dep'])
    year_death = int(row['death'])
    dates_pension = [str(int(year * 100) + 1) for year in range(year_dep, year_death + 1)]
    if nominal:
        pension = row['pension']
    else:
        pension = row['pension'] * indices_prix(year_dep)
    for date in dates_pension:
        row[date] = pension
    return row


def flow_contributions_matrix(pension_contrib, nominal=True, vector=True, taux_moyen = False):
    dates_contrib = [col for col in pension_contrib.columns if str(col)[0:2] in ['19', '20']]
    actual_dates = [int(date) for date in dates_contrib]
    if taux_moyen:
        dates_contrib = [col for col in pension_contrib.columns if str(col)[0:12] == 'contrib_moy_']
        actual_dates = [int(contrib_varname[12:]) for contrib_varname in dates_contrib]
    year_min = min(actual_dates) // 100
    year_max = max(actual_dates) // 100
    flow_contrib = pension_contrib.copy().loc[:, dates_contrib].fillna(0)
    del pension_contrib
    gc.collect()
    if nominal:
        if vector:
            return flow_contrib.sum(axis=1)
        else:
            return flow_contrib
    else:
        # Le salaire doit être passé en réel
        nominal_to_reel = indices_prix(year_min, year_max)
        assert flow_contrib.shape[1] == len(nominal_to_reel)
        flow_contrib = flow_contrib.multiply(nominal_to_reel, axis='columns')
        if vector:
            return flow_contrib.sum(axis=1)
        else:
            return flow_contrib


def flow_fct_builder(table, nominal=True, jac_inverse = False, taux_moyen = False):
    ''' These functions creates the vectorial function taking as an argument the vector r (1*N) of TRI '''
    pension_contrib = table.copy()
    del table
    dates_contrib = [col for col in pension_contrib.columns if str(col)[0:2] in ['19', '20']]
    actual_dates = [int(date) for date in dates_contrib]
    if taux_moyen:
        dates_contrib = [col for col in pension_contrib.columns if str(col)[0:12] == 'contrib_moy_']
        actual_dates = [int(contrib_varname[12:]) for contrib_varname in dates_contrib]
    year_min = min(actual_dates) // 100
    year_max = max(actual_dates) // 100
    if not nominal:
        nominal_to_reel = indices_prix(year_min, year_max)
        pension_contrib.loc[:, dates_contrib] = pension_contrib.loc[:, dates_contrib].values * nominal_to_reel
    pension_contrib = pension_contrib.apply(partial(add_pension, nominal = nominal), axis = 1)
    dates_flows = [col for col in pension_contrib.columns if str(col)[0:2] in ['19', '20']]
    pension_contrib = pension_contrib.loc[:, dates_flows].fillna(0)
    flows = np.array(pension_contrib)
    flows = nan_to_num(flows)
    del pension_contrib
    gc.collect()

    def flow_fct(r):
        flows_r = flows * np.vander(r, flows.shape[1], increasing=True)
        return np.sum(flows_r, axis = 1)

    def flow_jacobian_diag(r):
        mat_r = np.repeat([np.arange(1, flows.shape[1])], flows.shape[0], axis = 0)
        mat_r = mat_r * np.vander(r, flows.shape[1] - 1, increasing=True)
        mat = np.zeros(flows.shape)
        mat[:, 1::] = mat_r
        return np.sum(flows * mat, axis = 1)

    def flow_jacobian_inverse(r):
        mat_r = np.repeat([np.arange(1, flows.shape[1])], flows.shape[0], axis = 0)
        mat_r = mat_r * np.vander(r, flows.shape[1] - 1, increasing=True)
        mat = np.zeros(flows.shape)
        mat[:, 1::] = mat_r
        return np.diag(1. / np.sum(flows * mat, axis = 1))

    if jac_inverse:
        return flow_fct, flow_jacobian_diag, flow_jacobian_inverse
    else:
        return flow_fct, flow_jacobian_diag


def nominal_to_reel(to_convert, years):
    min_year = years.min()
    max_year = years.max()
    indices = indices_prix(min_year, max_year, return_dict = True)
    convertor = years.copy().replace(indices)
    return to_convert * convertor


def indices_prix(year_start, year_end = None, year_ref = 2009, path_xlsx = path_xlsx, return_dict = False):
    sheet_name = 'indice_prix_' + str(year_ref)
    var_euro = 'euro_' + str(year_ref)
    df = pd.read_excel(path_xlsx, sheet=sheet_name)[['annee', var_euro]].sort('annee', ascending = 1)
    if not year_end:
        return df.loc[df['annee'] == year_start, var_euro].values[0]
    elif return_dict:
        return dict([(year, value) for year, value in zip(df['annee'], df[var_euro])])
    else:
        return df.loc[(df['annee'] >= year_start) * (df['annee'] <= year_end), var_euro].values


def tri(pensions_contrib, nominal = False, high_dimension = True, marginal=False, initial = 0.98, taux_moyen = False):
    print "   Initial functions to calculate TRI have been built"
    initial_value = initial * np.ones(pensions_contrib.shape[0])
    if high_dimension:
        fct, jac_diag = flow_fct_builder(pensions_contrib, nominal = nominal,
                                         jac_inverse = False,
                                         taux_moyen = taux_moyen)
        sol = root(fct, initial_value, method = 'krylov',
                   options={'maxiter': 413})['x']
    else:
        fct, jac = flow_fct_builder(pensions_contrib, nominal = nominal,
                                    jac_inverse = high_dimension)
        sol = root(fct, initial_value, jac = jac, method='hybr', options = {'maxfev': 800})['x']

    if marginal:
        sol[sol < 0.5] = -1
    else:
        # sol[sol > 1] = -1 # On born inf le TRI par 0
        sol[sol < 0.5] = - 1 # On borne sup le TRI par 1
        # sol[sol < -1] = -1
        print "Not a marginal TRI"
    tri = 1. / sol - 1
    tri[tri == -2] = np.nan
    print "   TRI has been calculated"
    return tri
