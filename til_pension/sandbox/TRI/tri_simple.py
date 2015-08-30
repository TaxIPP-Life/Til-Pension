# -*- coding: utf-8 -*-
"""
Created on Sat Aug 15 07:25:26 2015

@author: Une
"""
import pandas as pd
import numpy as np
try:
    from scipy.optimize import fsolve
    from scipy.optimize import minimize_scalar, fmin_l_bfgs_b
except:
    pass
from functools import partial


def tri(row):
    def _tri(row):
        R = row['age_dep']
        D = row['age_death']
        S = row['age_start']
        assert S < R
        c0 = row['delta_c_age'] / row['delta_p_age']
        p = np.zeros(D - S + 1)
        p[0] = - c0
        p[R - S:] = 1
        sol = np.roots(p)
        sol_r = np.sort(sol[np.isreal(sol)])
        sol_r = sol_r[sol_r > 0]
        if sol_r[0] < 1:
            print S, R, D
            print sol_r
            print 1 / sol_r[0].real - 1
        return 1 / sol_r[0].real - 1

    if (row['delta_p_age'] == 0.0) & (row['delta_c_age'] == 0.0):
        return -9999
    elif row['delta_p_age'] == 0.0:
        return -1
    elif row['delta_c_age'] == 0.0:
        return 99999
    else:
        return _tri(row)


def flow_fct(row, taux_moyen = False):
    R = row['age_dep']
    D = row['age_death']
    S = row['age_start']
    assert S < R
    if taux_moyen:
        c0 = row['delta_c_moy_age'] / row['delta_p_age']
    else:
        c0 = row['delta_c_age'] / row['delta_p_age']
    p = np.zeros(D - S + 1)
    p[0] = - c0
    p[R - S:] = 1

    def fct(rate):
        rates = np.array([rate**k for k in range(len(p))])
        return np.sum(p * rates)
    return fct


def flow_fct_2(row, gradient = False, taux_moyen = False):
    fct = flow_fct(row, taux_moyen = taux_moyen)
    R = row['age_dep']
    D = row['age_death']
    S = row['age_start']
    p = np.zeros(D - S + 1)
    p[R - S:] = 1

    def fct_2(rate):
        return np.array(fct(rate) * fct(rate))

    if gradient:
        def grad(rate):
            rates = np.array([k * rate**(k - 1) for k in range(len(p))])
            return np.array(np.sum(p * rates))
        return fct, grad
    else:
        return fct


def tri_v2(row):
    def _tri(row):
        fct = flow_fct(row)
        c0 = row['delta_c_age'] / row['delta_p_age']
        if c0 > 10:
            val0 = 100
        else:
            val0 = 0.97
        sol = fsolve(fct, val0, maxfev = 800)
        return 1 / sol[0] - 1

    if (row['delta_p_age'] == 0.0) & (row['delta_c_age'] == 0.0):
        return -9999
    elif row['delta_p_age'] == 0.0:
        return -1
    elif row['delta_c_age'] == 0.0:
        return 99999
    else:
        return _tri(row)


def tri_v3(row):
    def _tri(row):
        fct = flow_fct_2(row)
        sol = minimize_scalar(fct, bounds=(0, 9999), method='bounded')
        return 1 / sol.x - 1

    if (row['delta_p_age'] == 0.0) & (row['delta_c_age'] == 0.0):
        return -9999
    elif row['delta_p_age'] == 0.0:
        return -1
    elif row['delta_c_age'] == 0.0:
        return 99999
    else:
        return _tri(row)


def tri_v4(row, taux_moyen = False):
    def _tri(row):
        fct, grad = flow_fct_2(row, gradient = True, taux_moyen = taux_moyen)
        c0 = row['delta_c_age'] / row['delta_p_age']
        val0 = 10 * c0
        sol = fmin_l_bfgs_b(fct, np.array([val0]),
                            fprime = grad,
                            bounds= np.array([(0.0, None)]))
        try:
            return 1 / np.sort(sol)[0][0] - 1
        except:
            return -6

    if taux_moyen:
        var_contrib = 'delta_c_moy_age'
    else:
        var_contrib = 'delta_c_age'
    if (row['delta_p_age'] == 0.0) & (row[var_contrib] == 0.0):
        return -9999
    elif row['delta_p_age'] == 0.0:
        return -1
    elif row[var_contrib] == 0.0:
        return 99999
    else:
        return _tri(row)


if __name__ == '__main__':
    path_work = "C:\\Users\\l.pauldelvaux\\Desktop\\MThesis\\Data\\"
    df = pd.read_csv(path_work + "delta_analysis12.csv", sep=',')
    test = False
    if test:
        df = df.ix[1:100, :]
    print df.columns
    df = df.fillna(0)
    df.loc[:, 'tri_moy'] = df.apply(partial(tri_v4, taux_moyen = True), 1)
    print df.columns
    path_dropbox = "C:\\Users\\l.pauldelvaux\\Dropbox\\MThesis_extract\\"
    df.to_csv(path_dropbox + "delta_with_tri12.csv", sep=',')
