# -*- coding: utf-8 -*-

import calendar
import collections
import copy
import datetime as dt
import gc
import numpy as np
import pandas as pd

from xml.etree import ElementTree

from Param import legislations_add_pension as legislations
from Param import legislationsxml_add_pension as  legislationsxml
from openfisca_core import conv
from utils import build_long_values, build_long_baremes, valbytranches, substract_months
#from .columns import EnumCol, EnumPresta
#from .taxbenefitsystems import TaxBenefitSystem

first_year_sal = 1949 

class Simulation(object):
    """
    Class from OF
    A simulation object contains all parameters to compute a simulation from a
    test-case household (scenario) or a survey-like dataset

    See also                                                                                         
    --------
    ScenarioSimulation, SurveySimulation
    """
    chunks_count = 1
    datesim = None
    disabled_prestations = None
    input_table = None
    num_table = 1
    P = None
    P_default = None
    param_file = None
    reforme = False  # Boolean signaling reform mode
    verbose = False

    def __init__(self):
        self.io_column_by_label = collections.OrderedDict()
        self.io_column_by_name = collections.OrderedDict()

    def __getstate__(self):
        def should_pickle(v):
            return v not in ['P_default', 'P']
        return dict((k, v) for (k, v) in self.__dict__.iteritems() if should_pickle(k))

    def _set_config(self, **kwargs):
        """
        Sets some general Simulation attributes
        """
        remaining = kwargs.copy()

        for key, val in kwargs.iteritems():
            if key == "year":
                date_str = str(val)+ '-05-01'
                self.datesim = dt.datetime.strptime(date_str ,"%Y-%m-%d").date()
                remaining.pop(key)

            elif key == "datesim":
                if isinstance(val, dt.date):
                    self.datesim = val
                else:
                    self.datesim = dt.datetime.strptime(val ,"%Y-%m-%d").date()
                remaining.pop(key)

            elif key in ['param_file', 'decomp_file']:
                if hasattr(self, key):
                    setattr(self, key, val)
                    remaining.pop(key)

        if self.param_file is None:
            print "Absence de paramètres législatifs"

        return remaining

    def set_param(self, param=None, param_default=None):
        """
        Set the parameters of the simulation

        Parameters
        ----------
        param : a socio-fiscal parameter object to be used in the microsimulation.
                By default, the method uses the one provided by the attribute param_file
        param_default : a socio-fiscal parameter object to be used
                in the microsimulation to compute some gross quantities not available in the initial data.
                parma_default is necessarily different from param when examining a reform
        """
        if param is None or param_default is None:
            legislation_tree = ElementTree.parse(self.param_file)
            legislation_xml_json = conv.check(legislationsxml.xml_legislation_to_json)(legislation_tree.getroot(),
                state = conv.default_state)
            legislation_xml_json, _ = legislationsxml.validate_node_xml_json(legislation_xml_json,
                state = conv.default_state)
            _, legislation_json = legislationsxml.transform_node_xml_json_to_json(legislation_xml_json)
            dated_legislation_json = legislations.generate_dated_legislation_json(legislation_json, self.datesim)
            long_dated_legislation_json = legislations.generate_long_legislation_json(legislation_json, self.datesim)
            compact_legislation = legislations.compact_dated_node_json(dated_legislation_json)
            compact_legislation_long = legislations.compact_long_dated_node_json(long_dated_legislation_json)
        if param_default is None:
            self.P_default = copy.deepcopy(compact_legislation)
        else:
            self.P_default = param_default
        if param is None:
            self.P = compact_legislation
            self.P_long = compact_legislation_long
        else:
            self.P = param


    def _compute(self, **kwargs):
        """
        Computes output_data for the Simulation

        Parameters
        ----------
        difference : boolean, default True
                     When in reform mode, compute the difference between actual and default
        Returns
        -------
        data, data_default : Computed data and possibly data_default according to decomp_file

        """
        # Clear outputs
        #self.clear()

        output_table, output_table_default = self.output_table, self.output_table_default
        for key, val in kwargs.iteritems():
            setattr(output_table, key, val)
            setattr(output_table_default, key, val)
        data = output_table.calculate()
        if self.reforme:
            output_table_default.reset()
            output_table_default.disable(self.disabled_prestations)
            data_default = output_table_default.calculate()
        else:
            output_table_default = output_table
            data_default = data

        self.data, self.data_default = data, data_default

        io_column_by_label = self.io_column_by_label
        io_column_by_name = self.io_column_by_name
        for column_name, column in output_table.column_by_name.iteritems():
            io_column_by_label[column.label] = column
            io_column_by_name[column_name] = column

        gc.collect()


class PensionSimulation(Simulation):
    """
    A Simulation class tailored to compute pensions (deal with survey data )
    """
    descr = None
     
    def __init__(self, survey_filename = None):
        Simulation.__init__(self)
        self.survey_filename = survey_filename
        self.workstate = None
        self.sali = None
        self.code_regime = None
        self.regime = None
        self.info_ind = None
        self.time_step = None
        
    def set_config(self, **kwargs):
        """
        Configures the PensionSimulation
        """
        # Setting general attributes and getting the specific ones
        specific_kwargs = self._set_config(**kwargs)
        for key, val in specific_kwargs.iteritems():
            if hasattr(self, key):
                setattr(self, key, val)

    def build_sal_regime(self):
        self.sal_regime = self.sali*(self.workstate.isin(self.code_regime))
        
    def calculate_taux(self, decote, surcote):
        ''' Détermination du taux de liquidation à appliquer à la pension '''
        taux_plein = self._P.plein.taux
        return taux_plein*(1 - decote + surcote)
        
    def nombre_points(self, first_year=first_year_sal, last_year=None):
        ''' Détermine le nombre de point à liquidation de la pension dans les régimes complémentaires (pour l'instant Ok pour ARRCO/AGIRC)
        Pour calculer ces points, il faut diviser la cotisation annuelle ouvrant des droits par le salaire de référence de l'année concernée 
        et multiplier par le taux d'acquisition des points'''
        yearsim = self.datesim.year
        last_year_sali = yearsim - 1
        if last_year == None:
            last_year = last_year_sali
        regime = self.regime
        P = self._P.complementaire.__dict__[regime]
        Plong = self._Plongitudinal.prive.complementaire.__dict__[regime]
        sali = self.sal_regime
        salref = build_long_values(Plong.sal_ref, first_year=first_year_sal, last_year=yearsim)
        plaf_ss = self._Plongitudinal.common.plaf_ss
        pss = build_long_values(plaf_ss, first_year=first_year_sal, last_year=yearsim)    
        taux_cot = build_long_baremes(Plong.taux_cot_moy, first_year=first_year_sal, last_year=yearsim, scale=pss)
        assert len(salref) == sali.shape[1] == len(taux_cot)
        nb_points = pd.Series(np.zeros(len(sali.index)), index=sali.index)
        if last_year_sali < first_year:
            return nb_points
        for year in range(first_year, min(last_year_sali, last_year) + 1):
            points_acquis = np.divide(taux_cot[year].calc(sali[year*100 + 1]), salref[year-first_year_sal]).round(2) 
            gmp = P.gmp
            #print year, taux_cot[year], sali.ix[1926 ,year *100 + 1], salref[year-first_year_sal]
            #print 'result', pd.Series(points_acquis, index=sali.index).ix[1926]
            nb_points += np.maximum(points_acquis, gmp)*(points_acquis > 0)
        return nb_points       
 
    def coeff_age(self, agem, trim):
        ''' TODO: add surcote  pour avant 1955 '''
        regime = self.regime
        P = self._P.complementaire.__dict__[regime]
        coef_mino = P.coef_mino
        age_annulation_decote = valbytranches(self._P.RG.decote.age_null, self.info_ind) 
        N_taux = valbytranches(self._P.RG.plein.N_taux, self.info_ind)
        diff_age = np.maximum(np.divide(age_annulation_decote - agem, 12), 0)
        coeff_min = pd.Series(np.zeros(len(agem)), index=agem.index)
        coeff_maj = pd.Series(np.zeros(len(agem)), index=agem.index)
        for nb_annees, coef_mino in coef_mino._tranches:
            coeff_min += (diff_age == nb_annees)*coef_mino
        if self.datesim.year <= 1955:
            maj_age = np.maximum(np.divide(agem - age_annulation_decote, 12), 0)
            coeff_maj = maj_age*0.05
            return coeff_min + coeff_maj
        elif  self.datesim.year < 1983:
            return coeff_min
        elif self.datesim.year >= 1983:
            # A partir de cette date, la minoration ne s'applique que si la durée de cotisation au régime général est inférieure à celle requise pour le taux plein
            return  coeff_min*(N_taux > trim) + (N_taux <= trim)             