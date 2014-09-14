# -*- coding: utf-8 -*-
from til_pension.datetil import DateTil
from numpy import minimum
import pdb
import inspect
import cProfile

basic_info = [('index', '<i8'), ('n_enf', '<f8'), ('sexe', '<f8'),
              ('tauxprime', '<f8'), ('naiss', 'O'), ('agem', '<f8'),
              ('nb_pac', '<f8')]


class PensionSimulation(object):
    ''' class qui permet de simuler un système de retraite :
            a besoin d'une data et d'une legislation
          La méthode evaluate renvoie un vecteur qui est le montant
          de pension calculé
    '''
    def __init__(self, data, legislation):
        self.data = data
        self.legislation = legislation

        # adapt longitudinal parameter to data
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
        ''' Cette fonction vérifie que le data d'entrée comporte toute
        l'information nécessaire au lancement d'une simulation'''
        info_ind = self.data.info_ind
        var_info_ind = ['agem', 'sexe', 'tauxprime', 'naiss']
        regime_base_names = ['nb_enf_' + regime.name
                             for regime in self.legislation.regimes['bases']]
        var_info_ind += regime_base_names
        for var in var_info_ind:
            if var not in info_ind.dtype.names:
                print("La variable {} doit être renseignée dans info_ind " +
                      "pour que la simulation puisse tourner, \n seules" +
                      "{} sont connues").format(var, info_ind.columns)

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
        # TODO: remove yearleg
        config = {'dateleg': yearleg, 'P': P, 'P_longit': P_longit,
                  'time_step': time_step, 'data': self.data}
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
            reg.P = P
            reg.P_longit = P_longit
            reg.dateleg = date

    def calculate(self, varname, regime_name='all'):
        ''' renvoie la variable calculée
            va chercher les arguments et les renvois
            Note: il y a une subtilité quand un régime a besoin d'infos qui viennnent
            d'un autre régime. Il faut alors définir cette variable-focntion
            en lui donnant comme paramètre uniquement (self, regime='')
            avec le nom du régime concerné ou bien 'all' si on veut une
            info tous régimes
        '''
        # TODO: remonter le nom de la variable plus haut.
        assert regime_name in self.calculated
        if varname not in self.calculated[regime_name]:
            reg = self.get_regime(regime_name)
            try:
                method = reg.__getattribute__(varname)
            except:
                raise Exception("Attention, la variable que vous appeler doit" +
                                "être le nom d'une methode de la classe" +
                                " ce n'est pas le cas pour " + varname +
                                " dans " + regime_name)
            arguments = inspect.getargspec(method)
            # cas particulier quand on veut appeler une fonction d'un autre régime
            if arguments.args == ['self', 'regime']:
                other_regime_name = arguments.defaults[0]
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
            except Exception, e:
                print ("on est en train de calculer la variable " + varname +
                       " de " + regime_name)
                print (dict_var)
                print(varname)
                print(arguments)
                print str(e)
                pdb.set_trace()

        return self.calculated[regime_name][varname]

    def _eval_for_regimes(self, varname, regimes):
        regimes_names = [reg.name for reg in regimes]
        result = []
        for reg_name in regimes_names:
            result += [self.calculate(varname, regime_name=reg_name)]
        return result

    def data(self):
        return self.data

    def info_ind(self):
        return self.data.info_ind

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

    def date_depart(self):
        list_dates = self._eval_for_regimes('date_start_taux_plein', regimes=self.legislation.regimes['bases'])
        for date in list_dates:
            date[date == 210001] = -1
        dates = reduce(minimum, list_dates)
        return dates

    def profile_evaluate(self, varname, regime_name='all'):
        prof = cProfile.Profile()
        result = prof.runcall(self.calculate, *(varname, regime_name))
        # TODO: add a suffix, like yearleg : was + str(self.yearsim)
        prof.dump_stats("profile_pension" + str(self.legislation.date.liam))
        return result
