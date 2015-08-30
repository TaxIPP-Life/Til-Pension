# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
try:
    from scipy.optimize import fsolve, root
except:
    pass

from functools import partial



class Survival(object):
    def __init__(self):
        self.survieF = None
        self.survieH = None
        self.A_max = None
        self.step = 'annual'
        self.path_survie = 'C:\Users\l.pauldelvaux\Desktop\MThesis\Data\Survie\\'
        self.generations = [1942, 1946, 1950]
        self.sexes = [0, 1]
        self.csp = [1, 2, 3, 4, 5, 6, -1]

    def load_tables(self, csp = True):
        def load_table_csv(path_survie, sexe):
            table = pd.read_csv(path_survie + "survie" + sexe + ".csv", sep = ',')
            return table

        survieF = load_table_csv(self.path_survie, 'F')
        survieH = load_table_csv(self.path_survie, 'H')

        def _col_survie(survie):
            # year = 1900 <-> time = 0
            survie = np.round(survie, 4)
            survie.columns = ['age'] + [1900 + yr for yr in range(1, len(survie.columns))]
            survie.set_index(['age'], inplace=True)
            return survie

        self.survieH = _col_survie(survieH)
        self.survieF = _col_survie(survieF)
        if not self.A_max:
            self.A_max = max(survieH.index)
        if csp:
            def clean_blanpain(df):
                df.set_index(['age'], inplace=True)
                df = df.loc[55: self.A_max, self.csp]
                return df
            blanpain_f = pd.read_excel(self.path_survie + 'mortalite_blanpain.xlsx', sheetname='F coeff')
            blanpain_h = pd.read_excel(self.path_survie + 'mortalite_blanpain.xlsx', sheetname='H coeff')
            self.csp_coeff_F = clean_blanpain(blanpain_f)
            self.csp_coeff_H = clean_blanpain(blanpain_h)

    def conditional_proba_group(self, age_delta, dataframe=True):
        '''
        Cette fonction permet de déterminer les groupes pour les survies conditionnelles à un âge a0
        qui vont pondérer les pensions.
        Ces tables de survie dépendent de deux dimensions: l'âge par rapport auquel on conditionne et la génération.
        Les tables donnent les pondérations P(A>a| A>= a0) pour a=55...121
        '''
        generations = self.generations
        sexes = self.sexes
        csp = self.csp

        def conditional_proba_pension(sexe, age, naiss, csp = None, A_max = self.A_max):
            date = naiss + age
            if sexe == 1:
                survie = self.survieF
                if csp:
                    csp_coeff = self.csp_coeff_F
            if sexe == 0:
                survie = self.survieH
                if csp:
                    csp_coeff = self.csp_coeff_H
            s_age_delta = survie.loc[age, date]
            esp = survie.loc[55:A_max, date] / s_age_delta
            # Application d'un coefficient de pondération selon la csp
            if csp:
                esp = esp * csp_coeff.loc[:, csp].values
            assert (esp.isnull() == False).all()
            return esp.values

        nb_group = len(generations) * len(sexes) * len(csp)
        years_proba = range(55, self.A_max + 1)
        if dataframe:
            df = pd.DataFrame(index=range(nb_group), columns = ['sexe', 'anaiss', 'pcs'] + years_proba)
            i = 0
            for sexe in sexes:
                for generation in generations:
                    for sp in csp:
                        df.loc[i, 'sexe'] = sexe
                        df.loc[i, 'anaiss'] = generation
                        df.loc[i, 'pcs'] = sp

                        df.loc[i, years_proba] = conditional_proba_pension(age = age_delta,
                                                                           sexe = sexe,
                                                                           naiss = generation,
                                                                           csp = sp)
                        assert (df.loc[i, years_proba].isnull() == False).all()
                        i += 1
            return df
        else:
            list_prob = dict()
            for generation in generations:
                for sexe in [0, 1]:
                    keys = {'sexe': sexe, 'naiss': generation}
                    list_prob[str(keys)] = conditional_proba_pension(age = age_delta, **keys)
            return list_prob


def mask_vector_ages(ages_col, age_retraite):
    to_compare = np.ones(shape = (len(age_retraite), len(ages_col))) * ages_col
    mask = np.greater_equal(to_compare.transpose(), age_retraite.values).transpose()
    return mask.astype(int)


def mask_rate_matrix(age_retraite, age_delta, A_max = 120):
    ages_R = range(55, A_max + 1)
    mask = mask_vector_ages(ages_R, age_retraite)
    return mask


def rate_matrix(rate, age_retraite, age_delta, A_max = 120):
    ''' Ajustement des taux d'actualisation:
    matrix de taille (nb_indiv, 120 -55) avec des zero avant retraite est des 1/(1+r)^{age - age_delta}
    pour age_retraite<= age <= 121'''
    mask = mask_rate_matrix(age_retraite, age_delta, A_max = A_max)
    rate = rate.astype(float)
    actual = np.column_stack([rate**i for i in range(55, A_max + 1)])
    rate_m = mask * actual
    return np.array(rate_m)


def pension_wealth(r, pension_contrib, info_ind, survie, var_pension, age_start = None):
    pension_contrib = pension_contrib.sort('ident')
    info_ind = info_ind.sort('ident')
    assert pension_contrib.shape[0] == info_ind.shape[0]
    shape_ini = info_ind.shape
    age_retraite = info_ind['year_dep'] - info_ind['anaiss']
    pension = pension_contrib[var_pension]
    proba_by_group = survie.conditional_proba_group(age_start)
    to_merge = info_ind.loc[:, ['sexe', 'pcs', 'anaiss', 'ident']]
    to_merge.loc[:, 'pcs'] = to_merge.loc[:, 'pcs'].fillna(-1)
    to_merge.loc[:, 'anaiss'] = to_merge.loc[:, 'anaiss'].astype(int)
    to_merge.loc[:, 'sexe'] = to_merge.loc[:, 'sexe'].astype(int)
    # to_merge.loc[:, 'helper'] = 1
    proba_pension = to_merge.merge(proba_by_group, on=['sexe', 'pcs', 'anaiss'], how = 'outer').sort('ident')
    # proba_pension = proba_pension.loc[(proba_pension['helper'] == 1), :]
    assert proba_pension.shape[0] == shape_ini[0]
    proba_pension = np.array(proba_pension.loc[:, range(55, survie.A_max + 1)])
    rates = rate_matrix(r, age_retraite, age_start, A_max = survie.A_max)
    flow_p = np.sum(proba_pension * rates, axis=1) * pension.values.copy()
    return flow_p


def net_marginal_tax(r, delta_pension_contrib, info_ind, survie,
                 year_start = None, from_findet = None, age_start = None, taux_moyen = False,
                 nominal = False):
    if nominal:
        delta_c = delta_pension_contrib['delta_flowc_nominal']
        var_pension = 'delta_pension'
    else:
        delta_c = delta_pension_contrib['delta_flowc_reel']
        if taux_moyen:
            delta_c = delta_pension_contrib['delta_flowc_moy_reel']
        var_pension = 'delta_pension_reel'
    if age_start:
        dflow_p = pension_wealth(r, delta_pension_contrib, info_ind, survie, var_pension, age_start)
        return delta_c - dflow_p


def flow_fct_builder(table, info_ind, survie, age_delta, nominal=True):
    ''' These functions creates the vectorial function taking as an argument the vector r (1*N) of TRI '''
    pension_contrib = table.copy().sort('ident')
    info_ind = info_ind.sort('ident')
    assert pension_contrib.shape[0] == info_ind.shape[0]
    shape_ini = info_ind.shape
    if nominal:
        delta_pension = pension_contrib['delta_pension']
        delta_c = pension_contrib['delta_flowc_nominal']
    else:
        delta_pension = pension_contrib['delta_pension_reel']
        delta_c = pension_contrib['delta_flowc_reel']
    age_retraite = info_ind['year_dep'] - info_ind['anaiss']
    proba_by_group = survie.conditional_proba_group(age_delta)
    to_merge = info_ind.loc[:, ['sexe', 'pcs', 'anaiss', 'ident']]
    to_merge.loc[:, 'pcs'] = to_merge.loc[:, 'pcs'].fillna(-1)
    to_merge.loc[:, 'anaiss'] = to_merge.loc[:, 'anaiss'].astype(int)
    to_merge.loc[:, 'sexe'] = to_merge.loc[:, 'sexe'].astype(int)
    to_merge.loc[:, 'helper'] = 1
    proba_pension = to_merge.merge(proba_by_group, on=['sexe', 'pcs', 'anaiss'], how = 'outer').sort('ident')
    proba_pension = proba_pension.loc[(proba_pension['helper'] == 1), :]
    assert proba_pension.shape[0] == shape_ini[0]
    proba_pension = np.array(proba_pension.loc[:, range(55, survie.A_max + 1)])
    mask_rate = np.array(mask_rate_matrix(age_retraite, age_delta, A_max = survie.A_max))
    print proba_pension.sum(1)
    print proba_pension.sum(1).mean()
    def flow_fct(r):
        delta_p = mask_rate * proba_pension * np.column_stack([r**i for i in range(55, survie.A_max + 1)])
        delta_p = np.sum(delta_p, axis=1) * delta_pension.values.copy()
        delta = delta_p - delta_c.copy()
        return delta.values
    return flow_fct


def initial_filter(table, nominal=True):
    ''' These functions creates the vectorial function taking as an argument the vector r (1*N) of TRI '''
    pension_contrib = table.copy().sort('ident')
    if nominal:
        delta_pension = pension_contrib['delta_pension']
        delta_c = pension_contrib['delta_flowc_nominal']
    else:
        delta_pension = pension_contrib['delta_pension_reel']
        delta_c = pension_contrib['delta_flowc_reel']
    initial = delta_pension * delta_c
    to_keep = initial.loc[initial != 0]
    return to_keep


def tri_out_of_bounds(table, nominal = True):
    pension_contrib = table.copy().sort('ident')
    if nominal:
        dpension = 'delta_pension'
        dflowc = 'delta_flowc_nominal'
    else:
        dpension = 'delta_pension_reel'
        dflowc = 'delta_flowc_reel'
    delta = pension_contrib[[dpension, dflowc]]
    delta = delta.loc[(delta[dpension] * delta[dflowc] == 0), :]
    ind_inf = delta.loc[(delta[dpension] != 0) & (delta[dflowc] == 0), :].index
    ind_m1 = delta.loc[(delta[dpension] == 0) & (delta[dflowc] != 0), :].index
    return pd.concat([pd.DataFrame(999999 * np.ones(len(ind_inf)), index = ind_inf),
            pd.DataFrame(- np.ones(len(ind_m1)), index = ind_m1)])


def tri_marginal(delta_pensions_contrib, info_ind, survie,
                 year_start = None, from_findet = None, age_start = None,
                 nominal = False, high_dimension = True):
    delta_pc = delta_pensions_contrib.copy().fillna(0)
    tri_out = tri_out_of_bounds(delta_pc, nominal = nominal)
    info = info_ind.copy()
    to_keep = initial_filter(delta_pc, nominal = nominal)
    if to_keep.shape[0] != 0:
        delta_pc = delta_pc.loc[to_keep.index, :]
        cond = (delta_pc['delta_pension_reel'] > 2 *delta_pc['delta_flowc_reel']).astype(int).values
        initial_value = 0.98 * (1-cond) + 0.2 * cond
        info = info.loc[to_keep.index, :]
        initial_value = 0.98 * np.ones(delta_pc.shape[0])
        if age_start:
            print age_start
            if high_dimension:
                fct = flow_fct_builder(delta_pc, info, survie,
                                       age_start, nominal = nominal)
                sol = root(fct, initial_value, method = 'krylov',
                               options={'fatol': 54e-3, 'maxiter': 413})['x']
            else:
                fct, jac = flow_fct_builder(delta_pc, info, survie,
                                            age_start, nominal = nominal)
                sol = root(fct, initial_value, jac = jac, method='hybr', options = {'maxfev': 800})['x']
        if (sol == initial_value).all():
            print "TRI not computed"
            not_available = pd.DataFrame(index = to_keep.index)
            return pd.concat([not_available, tri_out])
        print len(sol[sol < 0.5])
        # sol[sol < 0.5] = -1
        tri = 1. / sol - 1
        # tri[tri == -2] = np.nan
        tri = pd.DataFrame(tri, index = to_keep.index)
        print tri
        tri = pd.concat([tri, tri_out])
    else:
        tri = tri_out
    return tri.sort_index()


def fct_row(survie, age_delta, nominal=False):
    proba_by_group = survie.conditional_proba_group(age_delta)
    def fct(r, row):
        if nominal:
            delta_pension = row['delta_pension']
            delta_c = row['delta_flowc_nominal']
        else:
            delta_pension = row['delta_pension_reel']
            delta_c = row['delta_flowc_reel']
        age_retraite = row['year_dep'] - row['anaiss']
        pcs = int(row['pcs'])
        if pcs not in range(1, 7):
            pcs = -1
        anaiss = int(row['anaiss'])
        sexe = int(row['sexe'])
        proba_pension = proba_by_group.loc[(proba_by_group['sexe'] == sexe) & (proba_by_group['pcs'] == pcs) & (proba_by_group['anaiss'] == anaiss), range(55, survie.A_max + 1)]
        mask_rate = np.greater_equal(range(55, survie.A_max + 1), age_retraite).astype(int)
        delta_p = mask_rate * proba_pension * [r**i for i in range(55, survie.A_max + 1)]
        delta_p = np.sum(delta_p) * delta_pension
        delta = delta_p - delta_c
        return delta
    return fct


def fct_opt(row, fct_apply_row = None):
    def to_opt(r):
        return fct_apply_row(r, row)
    sol = fsolve(to_opt, 0.98, maxfev = 713)
    tri = 1. / sol - 1
    row.loc['tri'] = tri[0]
    return row


def tri_marginal_apply(pensions_contrib, survie,
                       year_start = None, from_findet = None, age_start = None,
                       nominal = False, high_dimension = True):
    delta_pc = pensions_contrib.copy().fillna(0)
    tri_out = tri_out_of_bounds(delta_pc, nominal = nominal)
    to_keep = initial_filter(delta_pc, nominal = nominal)

    if to_keep.shape[0] != 0:
        delta_pc = delta_pc.loc[to_keep.index, :]
        delta_pc.loc[:, 'pcs'] = delta_pc.loc[:, 'pcs'].fillna(-1)
        if age_start:
            print age_start
            fct_r = fct_row(survie, age_start, nominal=nominal)
            delta_pc = delta_pc.apply(partial(fct_opt, fct_apply_row = fct_r), axis=1)
            tri = delta_pc.loc[:, 'tri']
    test = pd.concat([tri, tri_out])
    return test

if __name__ == '__main__':
    survie = Survival()
    survie.load_tables()
