# -*- coding: utf-8 -*-
import numpy as np
from pandas import DataFrame, Series
from til_pension.pension_functions import sum_by_regime, update_all_regime
from til_pension.add_print import AddPrint
from til_pension.datetil import DateTil
import pdb
import inspect
import cProfile

basic_info = [('index', '<i8'), ('n_enf', '<f8'), ('sexe', '<f8'), ('tauxprime', '<f8'),
              ('naiss', 'O'), ('agem', '<f8'), ('nb_pac', '<f8')]

class PensionSimulation(object):
    ''' class qui permet de simuler un système de retraite :
            a besoin d'une data et d'une legislation
          La méthode evaluate renvoie un vecteur qui est le montant de pension calculé
    '''

    def __init__(self, data, legislation):
        self.data = data
        self.legislation = legislation

        #adapt longitudinal parameter to data
        duration_sim = data.last_date.year - data.first_date.year
        self.legislation.P_longit = legislation.long_param_builder(duration_sim)
        self.legislation.P = legislation.param.P

        self.trimesters_wages = dict()
        self.pensions = dict()
        self.check()
        
        tous_regimes = self.legislation.regimes['bases'] + self.legislation.regimes['complementaires']
        regimes_names = [reg.name for reg in tous_regimes]
        self.calculated = dict((reg_name, dict()) for reg_name in regimes_names + ['all'])

    def check(self):
        ''' Cette fonction vérifie que le data d'entrée comporte toute l'information nécessaire au
        lancement d'une simulation'''
        info_ind = self.data.info_ind
        var_info_ind = ['agem', 'sexe', 'tauxprime', 'naiss']
        regime_base_names = ['nb_enf_' + regime.name 
                             for regime in self.legislation.regimes['bases']]
        var_info_ind += regime_base_names
        for var in var_info_ind:
            if var not in info_ind.dtype.names:
                print("La variable {} doit être renseignée dans info_ind pour que la simulation puisse tourner, \n seules {} sont connues").format(var, info_ind.columns)
                import pdb
                pdb.set_trace()
                
    def get_regime(self, regime_name):
        # subtilité : 
        if regime_name == 'all':
            return self
        for serie in ['bases', 'complementaires']:
            regimes = self.legislation.regimes[serie]
            regimes_names = [reg.name for reg in regimes]
            if regime_name in regimes_names:
                return regimes[regimes_names.index(regime_name)]
            

    def set_config(self, time_step='year',):
        P = self.legislation.P
        P_longit = self.legislation.P_longit
        yearleg = self.legislation.date.year
        #TODO: remove yearleg
        config = {'dateleg' : yearleg, 'P': P, 'P_longit': P_longit, 'time_step': time_step, 'data': self.data}
        
        """
        Configures the Regime
        """
        # Setting general attributes and getting the specific ones
        # TODO: peut-être supprimer des choses si tout est dans calculated
        for key, val in config.iteritems():
            if hasattr(self, key):
                setattr(self, key, val)
                self.calculated['all'][key] = val
        if 'dateleg' in config.keys():
            date = DateTil(config['dateleg'])
            self.dateleg = date
            self.calculated['all']['dateleg'] = date
        
        # TODO: to remove since parameters are in simulation and not in regime anymore 
        regimes = self.legislation.regimes
        for reg in regimes['bases'] + regimes['complementaires']:
            reg.set_config(**config)

   

    def calculate(self, varname, regime_name='all'):
        ''' renvoie la variable calculée 
            va chercher les arguments et les renvois
            Note: il y a une subtilité quand un régime a besoin d'infos qui sont plus larges que le 
            régime lui-même, la foncion renvoie un tuple avec le régime concerné (ou bien 'all") et 
            le nom de la variable à calculer'''
        # TODO: remonter le nom de la variable plus haut.
        assert regime_name in self.calculated
        if varname not in self.calculated[regime_name]:
            print ("on est en train de calculer la variable " + varname + 
                          " de " + regime_name)
            reg = self.get_regime(regime_name)
            try: 
                method = reg.__getattribute__(varname)
            except: 
                raise Exception("Attention, la variable que vous appeler doit être le nom d'une methode de la classe" +
                                " ce n'est pas le cas pour " + varname + " dans " + regime_name)
            arguments = inspect.getargspec(method)
            # cas particulier quand on veut appeler une fonction d'un autre régime
            if arguments.args == ['self', 'regime']:
                other_regime_name =  arguments.defaults[0]
                if varname not in self.calculated[other_regime_name]:
                    self.calculate(varname, other_regime_name)
                return self.calculated[other_regime_name][varname]
                
            try:  # TODO: remove the try except function
                assert arguments.varargs is None
                assert arguments.keywords is None
                assert arguments.defaults is None 
            except: 
                pdb.set_trace()
            arguments = arguments.args
            print(varname)
            print(arguments)
            dict_var = dict()
            for arg in arguments:
                if arg == 'self':
                    pass
    #                 dict_var[arg] = self
                elif arg in ['data']:
                    dict_var[arg] = self.data
                else:
                    dict_var[arg] = self.calculate(arg, regime_name)
            try:
                self.calculated[regime_name][varname] = method(**dict_var)
            except:
                print (dict_var)
                pdb.set_trace()
            
        return self.calculated[regime_name][varname]
    
#     def trim_by_year_all(self):
#         return sum([ self.legislation.regimes['bases'] + self.legislation.regimes['complementaires'])

# def update_all_regime(trimesters_wages, dict_to_check):
#     #devrait peut-être remonter dans PensionLegislation
#     trim_by_year_tot = sum_from_dict({ regime : trimesters_wages[regime]['trimesters']['regime'] for regime in trimesters_wages.keys()})
#     trimesters_wages = attribution_mda(trimesters_wages)
#     maj_tot = sum([sum(trimesters_wages[regime]['maj'].values()) for regime in trimesters_wages.keys()])
#     enf_tot = sum([trimesters_wages[regime]['maj']['DA'] for regime in trimesters_wages.keys()])
#     trimesters_wages['all_regime'] = {'trimesters' : {'tot' : trim_by_year_tot}, 'maj' : {'tot' : maj_tot, 'enf':enf_tot}}
#     return trimesters_wages


    def _eval_for_regimes(self, varname, regimes):
        regimes_names = [reg.name for reg in regimes]
        result = []
        for reg_name in regimes_names:
            result += [self.calculate(varname, regime_name=reg_name)]
        return result

    def trimesters_tot(self):   # old trimesters_wages['all_regime']['trimesters']['tot']
        return sum(self._eval_for_regimes('trimesters', regimes=self.legislation.regimes['bases']))
        
    def trim_maj_enf_tot(self):  # old trimesters_wages['all_regime']['maj']['enf']
        return sum(self._eval_for_regimes('trim_maj_mda', regimes=self.legislation.regimes['bases']))
        
    def trim_maj_tot(self):  # old trimesters_wages['all_regime']['maj']['tot']
        return sum(self._eval_for_regimes('trim_maj', regimes=self.legislation.regimes['bases']))
    
    def pension(self):
        return sum(self._eval_for_regimes('pension', 
                                          regimes=self.legislation.regimes['bases'] + 
                                          self.legislation.regimes['complementaires']))

    def evaluate(self, time_step='year', to_check=False, output='pension', to_print=(None,None,True)):
        ''' to print commande ce que va afficher le calcul, c'est un tuple de longueur 3 :
                - en première position: un dictionnaire par régime qui donne les fonctions que l'on veut afficher
                - en deuxième position: les indices à retourner : si None, on retourne tout
                - en troisième postition: un booléun, si True c'est des valeurs de index qu'on donne, si false, c'est des numéro de ligne
        '''
        if self.legislation.param is None:
            raise Exception("you should give parameter to PensionData before to evaluate")

        methods_to_look_into = to_print[0]
        idx_to_print = to_print[1]
        ident_to_print = to_print[1]
        index = self.data.info_ind['index']
        if to_print[1] is None:
            idx_to_print = range(len(index))
            ident_to_print = index
        else:
            if to_print[2]:
                select = Series(range(len(index)), index=index)
                idx_to_print = select.loc[to_print[1]].values


        def update_methods(reg):
            ''' la methode pour modifier les méthodes du régime reg si:
                 - le regime est dans la liste
                 - pour les méthodes de la listes
            '''
            if methods_to_look_into is None:
                pass
            else:
                # change les méthodes que l'on veut voir afficher
                if reg.name in methods_to_look_into:
                    methods_to_look = methods_to_look_into[reg.name]
                    for method in methods_to_look:
                        method_init = reg.__getattribute__(method)
                        new_method = AddPrint(ident_to_print, idx_to_print)(method_init)
                        reg.__setattr__(method, new_method)
            return reg
        
        dict_to_check = dict()
        
        # TODO: remove all of this since it's in set_config now
        P = self.legislation.P
        P_longit = self.legislation.P_longit
        yearleg = self.legislation.date.year
        #TODO: remove yearleg
        config = {'dateleg' : yearleg, 'P': P, 'P_longit': P_longit, 'time_step': time_step, 'data': self.data}

        data = self.data
        regimes = self.legislation.regimes
        base_regimes = regimes['bases']
        complementaire_regimes = regimes['complementaires']
        
        ### get trimesters (only TimeArray with trim by year), wages (only TimeArray with wage by year) and trim_maj (only vector of majoration):
        trimesters_wages = self.trimesters_wages

        # 1 - Détermination des trimestres et des salaires cotisés, assimilés, avpf et majorés par régime
        if len(trimesters_wages) == 0:
            to_other = dict()
            for reg in base_regimes:
                reg.set_config(**config)
                reg = update_methods(reg)
                trimesters_wages_regime, to_other_regime = reg.get_trimesters_wages(data)
                trimesters_wages[reg.name] = trimesters_wages_regime
                to_other.update(to_other_regime)

            trimesters_wages = sum_by_regime(trimesters_wages, to_other)
            trimesters_wages = update_all_regime(trimesters_wages, dict_to_check)
            self.trimesters_wages = trimesters_wages

        if output == 'trimesters_wages':
            return self.trimesters_wages

        if output == 'dates_taux_plein':
            dates_taux_plein = dict()
            for reg in base_regimes:
                reg.set_config(**config)
                date_taux_plein = reg.date_start_taux_plein(data, trimesters_wages['all_regime'])
                date_taux_plein[date_taux_plein == 210001] = -1
                dates_taux_plein[reg.name] = date_taux_plein
            dates = reduce(np.minimum, dates_taux_plein.values())
            return dates

        # 2 - Calcul des pensions brutes par régime (de base et complémentaire)
        pensions = self.pensions
        trim_decote = dict()
        if len(pensions) == 0:
            for reg in base_regimes:
                reg.set_config(**config)
                reg = update_methods(reg)
                pension_reg, decote_reg = reg.pension(data, trimesters_wages[reg.name], trimesters_wages['all_regime'],
                                                                dict_to_check)
                trim_decote[reg.name] = decote_reg
                pensions[reg.name] = pension_reg

            for reg in complementaire_regimes:
                reg.set_config(**config)
                reg = update_methods(reg)
                regime_base = reg.regime_base
                pension_reg = reg.pension(data, trimesters_wages[regime_base], trimesters_wages['all_regime'],
                                                    trim_decote[regime_base], dict_to_check)
                pensions[reg.name] = pension_reg

            output = np.zeros(len(pension_reg))
            for val in pensions.values():
                output += val
            pensions['tot'] = output
            self.pensions = pensions

        # 3 - Application des minimums de pensions et majorations postérieures
        '''
        pension = 0
        pensions = dict()
        for reg in base_regimes:
            pension_brut_reg = pensions_brut[reg.name]
            pension_reg = reg.bonif_pension(data, trimesters_wages[reg.name], trimesters_wages['all_regime'],
                                            pension_brut_reg, pension)
            pension += pension_reg
            pensions[reg.name] = pension_reg
        '''

        if to_check == True:
            output = dict_to_check
            for key, value in self.pensions.iteritems():
                output['pension_' + key] = value
            return DataFrame(output, index = self.data.info_ind['index'])
        else:
            return self.pensions['tot'] # TODO: define the output : for the moment a dic with pensions by regime


    def profile_evaluate(self, time_step='year', to_check=False, output='pension', to_print=(None,None,True)):
        prof = cProfile.Profile()
        result = prof.runcall(self.evaluate, *(time_step, to_check, output, to_print))
        #TODO: add a suffix, like yearleg : was + str(self.yearsim)
        prof.dump_stats("profile_pension" + str(self.legislation.date.liam))
        return result
