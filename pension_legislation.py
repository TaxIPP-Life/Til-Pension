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

from Regimes.Fonction_publique import FonctionPublique
from Regimes.Regimes_complementaires_prive import AGIRC, ARRCO
from Regimes.Regimes_prives import RegimeGeneral, RegimeSocialIndependants
from regime import compare_destinie

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

class PensionParam(object):
    
    def __init__(self, dateleg, data):
        #TODO: use all attrbutes except data in a PensionParam class
        # example: 
        #     duration = data.last_year - data.first_year 
        #     self.param = PensionParam.builder(dateleg, data.info_ind, duration)
        #  or, by anticipation: 
        #     self.param = PensionParam.builder(dateleg, data.info_ind, duration, method)
        #  where method give how to shift legislation from on year to an other, constant_year, constant_sequence, etc?
        self.date = DateTil(dateleg)
        self.param = None
        self.param_long = None

#         def load_param(self):
#             ''' should run after having a data '''
        assert data is not None
        path_pension = os.path.dirname(os.path.abspath(__file__))
        param_file = path_pension + '\\France\\param.xml'
        
        ''' It's a simplification of an (old) openfisca program '''
        legislation_tree = ElementTree.parse(param_file)
        legislation_xml_json = conv.check(legislationsxml.xml_legislation_to_json)(legislation_tree.getroot(),
                                                                                   state = conv.default_state)
        #legislation_xml_json, _ = legislationsxml.validate_node_xml_json(legislation_xml_json,
        #                                                                 state = conv.default_state)
        _, legislation_json = legislationsxml.transform_node_xml_json_to_json(legislation_xml_json)
        
        dated_legislation_json = legislations.generate_dated_legislation_json(legislation_json, self.date.datetime)
        compact_legislation = legislations.compact_dated_node_json(dated_legislation_json, data.info_ind) #here is where data is needed
        self.param = compact_legislation
        
        long_dated_legislation_json = legislations.generate_long_legislation_json(legislation_json, self.date.datetime)
        compact_legislation_long = legislations.compact_long_dated_node_json(long_dated_legislation_json)
        self.param_long = compact_legislation_long

        #Travail sur Salref 
        #
        # Salref = salaire trimestriel de référence minimum pour le régime général
        #
        # Note: il existe deux opinions différentes acceptables mais non compatible sur la construction du salref
        # - la première c'est de considérer que le salaire de référence de chaque année est donné directement par la 
        #  legisaltion et que même si c'est écrit comme étant égal à d'autres paramètres de la législation, c'est un
        #  élément indépendant avec son propre code
        # - la seconde, consiste à voir l'étape de détermination du salaire de référence comme une étape de la 
        #  législation; le fait d'indexer sur tel ou tel indice n'est pas anodin. 
        #
        # Les deux sont valables, ici, on s'appuie sur la première, on ne fait que recalculer le niveau du salref 
        # à partir de sa définition. On considère en particulier que l'indexation sur le SMIC a lieu en 1972 et 
        # on ne peut pas, ailleur qu'ici faire comme si ce changement dépendant de l'année de la base de donnée
        # ce ne serait toutefois pas difficile à faire, il suffit de l'inscrire vraiment comme une étape de calcul
        # 
        # En résumé, on ne fait ici qu'écrire un salref qu'on aurait pu relevé dans la législation
        # Note :Toute la série chronologique est exprimé en euros
        
        # Article R351-9 du code de la sécurité sociale
        # de 1949 à 1972 -> AVTS, après jusqu'en 2014, 200 fois le smic horaire de la première année, ensuite 150 fois.
        param_long = self.param_long
        smic = param_long.common.smic
        avts = param_long.common.avts.montant
        if compare_destinie == True:
            smic = dict((key,val / (52*35)) for key, val in param_long.common.smic_proj.iteritems())
        smic_key = sorted(smic.keys())
        avts_key = sorted(avts.keys())
        debut_annee = '-01-01'
        
        salref = dict()
        k = -1
        year = 1949 # supposer and year < self.date.year
        while year < 1972 and year < self.date.year: 
            date = str(year) + debut_annee
            while avts_key[k+1] <= date:
                k +=1
            salref[date] = avts[avts_key[k]]/4
            if compare_destinie == True:
                salref[date] = 1
            year += 1           
            
        k = -1 
        while year < 2014 and year < self.date.year: 
            date = str(year) + debut_annee
            while smic_key[k+1] <= date:
                k +=1
            salref[date] = 200*smic[smic_key[k]]
            year += 1

        while year < 2014 and year < self.date.year: 
            date = str(year) + debut_annee
            while smic_key[k+1] <= date:
                k +=1
            salref[date] = 150*smic[smic_key[k]]
            year += 1        

        self.param_long.prive.RG.salref = salref       


class PensionLegislation(object):
    '''
    Class à envoyer à Simulation de Til-pension qui contient toutes les informations sur la législations. Elle tient compte de:
    - la date de législation demandée (sélection adéquate des paramètres)
    - les infos individuelles contenues dans data.info_ind (pour les paramètres par génération)
    - la structure des tables sali/workstate (pour ajuster la longueur des paramètres long)
    '''
    def __init__(self, param):
        #TODO: use all attrbutes except data in a PensionParam class
        # example: 
        #     duration = data.last_year - data.first_year 
        #     self.param = PensionParam.builder(dateleg, data.info_ind, duration)
        #  or, by anticipation: 
        #     self.param = PensionParam.builder(dateleg, data.info_ind, duration, method)
        #  where method give how to shift legislation from on year to an other, constant_year, constant_sequence, etc?
        self.param = param
        self.regimes = dict(
                            bases = [RegimeGeneral(), FonctionPublique(), RegimeSocialIndependants()],
                            complementaires = [ARRCO(), AGIRC()],
                            )
        self.date = param.date
            
    def long_param_builder(self, duration_sim): 
        ''' Cette fonction permet de traduire les paramètres longitudinaux en vecteur numpy 
        comportant une valeur par année comprise entre first_year_sim et last_year_sim '''
        yearleg = self.date.year
        P_longit = self.param.param_long
        first_year_sim = yearleg - 1 - duration_sim
        last_year_sim = yearleg
        # TODO: trouver une méthode plus systématique qui test le 'type' du noeud et construit le long parameter qui va bien
        for param_name in ['common.plaf_ss', 'prive.RG.revalo','common.smic_proj','common.avpf', 
                            'prive.RG.surcote.dispositif1.dates1','prive.RG.surcote.dispositif1.dates2',
                            'prive.RG.surcote.dispositif2.dates', 'public.fp.surcote.dates',
                            'prive.RG.salref', 'public.fp.val_point', 
                            'prive.complementaire.agirc.maj_enf.born.dispositif0.dates', 'prive.complementaire.agirc.maj_enf.born.dispositif1.dates',
                            'prive.complementaire.arrco.maj_enf.born.dispositif0.dates', 'prive.complementaire.arrco.maj_enf.born.dispositif1.dates']:
            param_name = param_name.split('.')
            param = reduce(getattr, param_name, P_longit)
            param = build_long_values(param_long=param, first=first_year_sim, last=last_year_sim)
            setattr(eval('P_longit.' + '.'.join(param_name[:-1])), param_name[-1], param)

        for regime in self.regimes['complementaires']:
            regime = regime.name
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


if __name__ == '__main__':
    from pension_data import PensionData
    import datetime
    
    data = DataFrame()
    table = array([ (186L, 1941.0, 2.0, 1.0, datetime.date(1941, 1, 1), 186L, 756.0, 0.0, 2.0, datetime.date(2060, 1, 1)),
       (376L, 1941.0, 1.0, 1.0, datetime.date(1941, 1, 1), 376L, 756.0, 0.0, 1.0, datetime.date(2060, 1, 1)),
       (833L, 1941.0, 3.0, 0.0, datetime.date(1941, 1, 1), 833L, 756.0, 0.0, 3.0, datetime.date(2060, 1, 1)),
       (834L, 1941.0, 3.0, 1.0, datetime.date(1941, 1, 1), 834L, 756.0, 0.0, 3.0, datetime.date(2060, 1, 1)),
       (956L, 1941.0, 0.0, 0.0, datetime.date(1941, 1, 1), 956L, 756.0, 0.0, 0.0, datetime.date(2060, 1, 1))], 
      dtype=[('index', '<i8'), ('t_naiss', '<f8'), ('n_enf', '<f8'), ('sexe', '<f8'), ('naiss', 'O'), ('id', '<i8'), ('agem', '<f8'), ('nb_pac', '<f8'), ('nb_born', '<f8'), ('date_liquidation', 'O')])
    info_ind = DataFrame(table)
    sali = DataFrame(0, index=info_ind.index, columns=[201301,201401])
    data = PensionData.from_arrays(sali, sali, info_ind)
    
    param = PensionParam(2015, data)
    print param.param.prive.RG.prorat
    print param.param.prive.RG.prorat
    
    legislation = PensionLegislation(param)
    legislation.salref_RG_builder(1000)

