# -*- coding: utf-8 -*-

import pandas as pd

from til_pension.sandbox.compare.CONFIG_compare import pensipp_comparison_path as pensipp_data_path 
from til_pension.simulation import PensionSimulation
from til_pension.pension_legislation import PensionParam, PensionLegislation
from til_pension.sandbox.compare.load_pensipp import load_pensipp_data
first_year_sal = 1949

def compute_TRI():
    pensions = dict()
    cotisations = dict()
    for yearsim in range(2004,2005):
        print(yearsim)
        data_bounded = load_pensipp_data(pensipp_data_path, yearsim, first_year_sal)
        param = PensionParam(yearsim, data_bounded)
        legislation = PensionLegislation(param)
        simul_til = PensionSimulation(data_bounded, legislation)
        pensions[yearsim], cotisations[yearsim] = simul_til.evaluate(output="pensions and contributions")

if __name__ == '__main__':
    compute_TRI()
  