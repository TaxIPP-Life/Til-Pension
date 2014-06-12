# -*- coding: utf-8 -*-

import datetime as dt
import os

from datetil import DateTil
from numpy import array, ones
from pandas import DataFrame

from xml.etree import ElementTree
from Param import legislations_add_pension as legislations
from Param import legislationsxml_add_pension as  legislationsxml
from openfisca_core import conv

from France.dates_start import dates_start


class PensionLegislation(object):
    '''
    Class à envoyer à Simulation de Til-pension qui contient les informations sur la législations. Elle tient compte de:
    - la date de législation demandée (sélection adéquate des paramètres)
    - les infos individuelles contenues dans data.info_ind (pour les paramètres par génération)
    - la structure des tables sali/workstate (pour ajuster la longueur des paramètres long)
    '''
    def __init__(self, dateleg, data, dates_start=dates_start): 
        self.date = DateTil(dateleg)
        self.param = None
        self.param_long = None
        self.dates_start = dates_start
        self.data = data
        self.regimes = dict(
                            bases = ['RegimeGeneral', 'FonctionPublique', 'RegimeSocialIndependants'],
                            complementaires = ['ARRCO', 'AGIRC'],
                            base_to_complementaire = {'RegimeGeneral': ['arrco', 'agirc'], 'FonctionPublique': []}
                            )
  
    def long_param_builder(self, P_longit): 
        ''' Cette fonction permet de traduire les paramètres longitudinaux en vecteur numpy 
        comportant une valeur par année comprise entre first_year_sim et last_year_sim '''
        yearleg = self.date.year
        duration_sim = self.data.last_date.year - self.data.first_date.year
        first_year_sim = yearleg - 1 - duration_sim
        last_year_sim = yearleg
        # TODO: trouver une méthode plus systématique qui test le 'type' du noeud et construit le long parameter qui va bien
        for param_name in ['common.plaf_ss', 'prive.RG.revalo','common.smic_proj','common.avpf']:
            param_name = param_name.split('.')
            param = reduce(getattr, param_name, P_longit)
            param = build_long_values(param_long=param, first=first_year_sim, last=last_year_sim)
            setattr(eval('P_longit.' + '.'.join(param_name[:-1])), param_name[-1], param)

        for regime in self.regimes['complementaires']:
            regime = regime.lower()
            P = getattr(P_longit.prive.complementaire, regime)
            salref_long = P.sal_ref
            salref_long = build_long_values(salref_long,
                                        first=first_year_sim, last=last_year_sim) 
            setattr(eval('P_longit.prive.complementaire.' + regime), 'sal_ref', salref_long)
            taux_cot_long = P.taux_cot_moy
            taux_cot_long = build_long_values(taux_cot_long,
                                               first=first_year_sim, last=last_year_sim)
            taux_cot_long = scales_long_baremes(baremes=taux_cot_long, scales=P_longit.common.plaf_ss)
            setattr(eval('P_longit.prive.complementaire.' + regime), 'taux_cot_moy', taux_cot_long)
            
        return P_longit
    
    def salref_RG_builder(self):
        '''
        salaire trimestriel de référence minimum pour le régime général
        Rq : Toute la série chronologique est exprimé en euros
        '''
        first_year = self.data.first_date.year
        last_year = self.data.last_date.year + 1
        year_avts_to_smic = self.dates_start['avts_to_smic']
        assert first_year <=  year_avts_to_smic
        assert last_year >  year_avts_to_smic
        salmin = DataFrame({'year': range(first_year, last_year), 'sal': -ones(last_year - first_year)} ) 
        avts_year = []
        smic_year = []
        param_long = self.param_long
        smic_long = param_long.common.smic
        avts_long = param_long.common.avts.montant
    
        for year in range(first_year, year_avts_to_smic):
            avts_old = avts_year
            avts_year = []
            for key in avts_long.keys():
                if str(year) in key:
                    avts_year.append(key)
            if not avts_year:
                avts_year = avts_old
            try:
                salmin.loc[salmin['year'] == year, 'sal'] = avts_long[avts_year[0]]
            except:
                if not avts_old:
                    salmin.loc[salmin['year'] == year, 'sal'] = 0
        for year in range(year_avts_to_smic, last_year):
            smic_old = smic_year
            smic_year = []
            for key in smic_long.keys():
                if str(year) in key:
                    smic_year.append(key)
            if not smic_year:
                smic_year = smic_old
            if year <= 2013 :
                salmin.loc[salmin['year'] == year, 'sal'] = 200*smic_long[smic_year[0]]
                if year <= 2001 :
                    salmin.loc[salmin['year'] == year, 'sal'] = 200*smic_long[smic_year[0]]/6.5596
            else:
                salmin.loc[salmin['year'] == year, 'sal'] = 150*smic_long[smic_year[0]]
        return array(salmin['sal'])


    def load_param(self):
        ''' should run after having a data'''
        assert self.data is not None
        path_pension = os.path.dirname(os.path.abspath(__file__))
        param_file = path_pension + '\\France\\param.xml'
        
        ''' It's a simplification of an (old) openfisca program '''
        legislation_tree = ElementTree.parse(param_file)
        legislation_xml_json = conv.check(legislationsxml.xml_legislation_to_json)(legislation_tree.getroot(),
                                                                                   state = conv.default_state)
        legislation_xml_json, _ = legislationsxml.validate_node_xml_json(legislation_xml_json,
                                                                         state = conv.default_state)
        _, legislation_json = legislationsxml.transform_node_xml_json_to_json(legislation_xml_json)
        dated_legislation_json = legislations.generate_dated_legislation_json(legislation_json, self.date.datetime)
        compact_legislation = legislations.compact_dated_node_json(dated_legislation_json, self.data.info_ind)
        long_dated_legislation_json = legislations.generate_long_legislation_json(legislation_json, self.date.datetime)
        compact_legislation_long = legislations.compact_long_dated_node_json(long_dated_legislation_json)

        compact_legislation_long = self.long_param_builder(compact_legislation_long)
        self.param_long = compact_legislation_long
        setattr(compact_legislation.prive.RG, 'salref', self.salref_RG_builder())
        self.param = compact_legislation 
        



def build_long_values(param_long, first, last, time_scale='year'):   
    ''' Cette fonction permet de traduire les paramètres longitudinaux en vecteur numpy 
    comportant une valeur par année comprise en first_year et last_year '''
    #TODO: Idea : return a TimeArray and use select if needed
    param_dates = sorted(param_long.keys())
    def _convert_date(x):
        date = dt.datetime.strptime(x, "%Y-%m-%d")
        return 100*date.year + date.month
    #TODO: convert here all param in dates   
    param_dates_liam = [_convert_date(x) for x in param_dates]
    param_dates_liam += [210001]

    if time_scale=='year':
        list_dates = [100*x + 1  for x in range(first, last)]
    else: 
        #TODO: create a function...
        raise Exception("Not implemented yet for time_scale not year")
    
    output = []
    k = 0
    for date in list_dates:
        while param_dates_liam[k+1] <= date:
            k += 1
        output += [param_long[param_dates[k]]]  
    return output
        
def scales_long_baremes(baremes, scales):   
    ''' Cette fonction permet de traduire les barèmes longitudinaux en dictionnaire de bareme
    comportant un barème par année comprise en first_year et last_year'''
    from Param.Scales import scaleBaremes
    assert len(scales) == len(baremes)
    for date in range(len(baremes)):
        baremes[date] = scaleBaremes(baremes[date], scales[date])
    return baremes
 