# -*- coding: utf-8 -*-

from math import pow
from numpy import array
import pandas as pd

try:
    from scipy.optimize import fsolve
except:
    pass
first_year_sal = 1949

# TODO: Tres tres moche et donc a refaire
path_xlsx = "C:\Users\l.pauldelvaux\Desktop\MThesis\Data\indices_prix.xlsx"


def indices_prix(year_start, year_end, year_ref = 2009, path_xlsx = path_xlsx):
    sheet_name = 'indice_prix_' + str(year_ref)
    var_euro = 'euro_' + str(year_ref)
    df = pd.read_excel(path_xlsx, sheetname=sheet_name)[['annee', var_euro]].sort('annee', ascending = 1)
    return df.loc[(df['annee'] >= year_start) * (df['annee'] <= year_end), var_euro].values


def revalo_pension(year_liq, year_target, path_xlsx = path_xlsx):
    sheet_name = 'revalo_pension'
    df = pd.read_excel(path_xlsx, sheetname=sheet_name)[['year', 'revaloRG']].sort('year', ascending = 1)
    df = df.loc[(df['year'] >= year_liq) * (df['year'] <= year_target) * ~(df['year'].isnull()), :]
    df.loc[:, 'year'] = df.loc[:, 'year'].astype(int)
    df.loc[:, 'revaloRG'] = df.loc[:, 'revaloRG'].astype(float)
    return df.groupby(['year'])['revaloRG'].apply(lambda x: x.prod())


def flow_pensions(pensions_contrib, nominal = False, vector = True):
    year_dep = int(pensions_contrib['year_dep'])
    year_death = pensions_contrib['death']
    if nominal:
        pension = pensions_contrib['pension']
    else:
        pension = pensions_contrib['pension_reel']
    nb_pensions = int(year_death - year_dep + 1)
    flow_pensions = [pension] * nb_pensions
    if vector:
        return flow_pensions
    else:
        return sum(flow_pensions)


def flow_contributions(pensions_contrib, nominal=True, vector = True, taux_moyen = False):
    year_naiss = int(str(pensions_contrib['naiss'])[0:4])
    year_dep = int(pensions_contrib['year_dep'])
    findet = int(pensions_contrib.loc['findet'])
    if taux_moyen:
        flow_contrib = [- pensions_contrib.loc['contrib_moy_' + str(year * 100 + 1)]
                for year in range(year_naiss + findet, year_dep)]
    else:
        flow_contrib = [- pensions_contrib.loc[str(year * 100 + 1)]
                        for year in range(year_naiss + findet, year_dep)]

    if nominal:
        if vector:
            return flow_contrib
        else:
            return sum(flow_contrib)
    else:
        # Le salaire doit être passé en réel
        nominal_to_reel = indices_prix(year_naiss + findet, year_dep - 1)
        flow_contrib = list(flow_contrib * nominal_to_reel)
        assert len(flow_contrib) == len(nominal_to_reel)
        if vector:
            return flow_contrib
        else:
            return sum(flow_contrib)


def flow(rate, pensions_contrib, nominal, taux_moyen):
    ''' fonction individuelle de calcul de la partie cotisation du TRI '''
    year_naiss = int(str(pensions_contrib['naiss'])[0:4])
    year_dep = int(pensions_contrib['year_dep'])
    findet = int(pensions_contrib.loc['findet'])
    year_death = pensions_contrib['death']
    nb_contrib = year_dep - (year_naiss + findet)
    nb_pensions = int(year_death - year_dep + 1)
    flow_contrib = flow_contributions(pensions_contrib, nominal = nominal, taux_moyen = taux_moyen)
    flow_pens = flow_pensions(pensions_contrib, nominal = nominal)
    flows = flow_contrib + flow_pens
    assert len(flows) == nb_pensions + nb_contrib
    actual = array([pow(rate, p) for p in range(0, nb_contrib + nb_pensions)])
    return sum(flows * actual)


def TRI(pensions_contrib, val0 = 0.98, nominal = False, taux_moyen = False):
    sol = fsolve(flow, val0, args=(pensions_contrib, nominal, taux_moyen),
                 maxfev = 400)
    try:
        rate = [s for s in sol if s > 1 / 2 and s < 1][0]
    except:
        rate = -1
    if rate > 1:
        rate = -1
    return 1 / rate - 1
