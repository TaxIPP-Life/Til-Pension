# -*- coding: utf-8 -*-

from numpy import maximum, array, nan_to_num, greater, divide, around, zeros, minimum, multiply
from til_pension.time_array import TimeArray

first_year_sal = 1949
compare_destinie = True


class Regime(object):
    """
    A Simulation class tailored to compute pensions (deal with survey data )
    """
    descr = None

    def __init__(self):
        self.code_regime = None
        self.name = None
        self.param_name = None

        self.dates = None
        self.time_step = None
        self.data_type = None
        self.dateleg = None

        self.P = None
        self.P_longit = None

        self.data = None
        self.calculated = dict()

    # variables communes à tous les régimes
    def info_ind(self, regime='all'):
        pass

    def data(self, regime='all'):
        pass

    # fonctions communes à touts les régimes
    def date_start_surcote(self, data, trimesters_tot, trim_maj_tot, age_min_retirement):
        ''' Détermine la date individuelle a partir de laquelle on atteint la surcote
        (a atteint l'âge légal de départ en retraite + côtisé le nombre de trimestres cible)
        Rq : pour l'instant on pourrait ne renvoyer que l'année'''
        agem = data.info_ind['agem']
        # TODO: do something better with datesim
        datesim = self.dateleg.liam
        P = reduce(getattr, self.param_name.split('.'), self.P)
        if P.surcote.exist == 0:
            # Si pas de dispositif de surcote
            return [2100*100 + 1]*len(trim_maj_tot)
        else:
            # 1. Construction de la matrice des booléens indiquant si l'année
            # est surcotée selon critère trimestres
            n_trim = array(P.plein.n_trim)
            cumul_trim = trimesters_tot.cumsum(axis=1)
            trim_limit = array((n_trim - nan_to_num(trim_maj_tot)))
            years_surcote_trim = greater(cumul_trim.T, trim_limit).T
            nb_years = years_surcote_trim.shape[1]

            # 2. Construction de la matrice des booléens indiquant si l'année
            # est surcotée selon critère âge
            age_by_year = array([array(agem) - 12*i for i in reversed(range(nb_years))])
            years_surcote_age = greater(age_by_year, array(age_min_retirement)).T

            # 3. Décompte du nombre d'années répondant aux deux critères
            years_surcote = years_surcote_trim*years_surcote_age
            nb_years_surcote = years_surcote.sum(axis=1)
            start_surcote = [datesim - nb_year*100
                             if nb_year > 0 else 2100*100 + 1
                             for nb_year in nb_years_surcote]
            return start_surcote

    def date_start_taux_plein(self, data, trimesters_tot, trim_maj_tot,
                              age_min_retirement, date_start_surcote,
                              age_annulation_decote):
        ''' Détermine la date individuelle a partir de laquelle on atteint le
        taux plein condition date_surcote ou si atteint l'âge du taux plein
        Rq : pour l'instant on pourrait ne renvoyer que l'année'''
        agem = data.info_ind['agem']
        datesim = self.dateleg.liam
        # TODO: find the origin of that non int array
        age_annulation_decote = age_annulation_decote.astype(int)
        datesim_in_month = 12*(datesim // 100) + datesim % 100
        start_taux_plein_in_month = agem - age_annulation_decote
        datenaiss_in_month = datesim_in_month - start_taux_plein_in_month
        start_taux_plein = 100*(datenaiss_in_month // 12) + datenaiss_in_month % 12 + 1
        start_taux_plein[datenaiss_in_month < 0] = 2100*100 + 1  # =inf
        return minimum(start_taux_plein, date_start_surcote)

    def taux(self, decote, surcote):
        ''' Détérmination du taux de liquidation à appliquer à la pension
            La formule générale est taux pondéré par (1+surcote-decote)
            _surcote and _decote are called
            _date_start_surcote is a general method helping surcote
            '''
        P = reduce(getattr, self.param_name.split('.'), self.P)
        return P.plein.taux*(1 - decote + surcote)


    def bonif_pension(self, data, trim_wage_reg, trim_wage_all, pension_reg,
                      pension_all):
        pension = pension_reg + self.minimum_pension(trim_wage_reg, trim_wage_all, pension_reg, pension_all)
        # Remarque : la majoration de pension s'applique à la pension rapportée au maximum ou au minimum
        pension += self.majoration_pension(data, pension)
        return pension


class RegimeBase(Regime):

    def trimester(self):
        return 0

    def trim_maj_mda(self):
        return 0

    def trim_maj(self):
        return 0

    def revenu_valides(self, workstate, sali, code=None):
        ''' Cette fonction pertmet de calculer des nombres par trimesters
        TODO: gérer la comptabilisation des temps partiels quand variable présente'''
        assert isinstance(workstate, TimeArray)
        # assert isinstance(sali, TimeArray)
        if code is None:
            code = self.code_regime
        wk_selection = workstate.isin(self.code_regime)
        wk_selection.translate_frequency(output_frequency='month', inplace=True)
        # TODO: condition not assuming sali is in year
        sali.translate_frequency(output_frequency='month', inplace=True)
        sali = around(divide(sali, 12), decimals=3)
        trim = divide(wk_selection.sum(axis=1), 4).astype(int)
        return trim

    def majoration_pension(self, data, pension_brute):
        P = reduce(getattr, self.param_name.split('.'), self.P)
        nb_enf = data.info_ind['nb_enf_all']

        def _taux_enf(nb_enf, P):
            ''' Majoration pour avoir élevé trois enfants '''
            taux_3enf = P.maj_3enf.taux
            taux_supp = P.maj_3enf.taux_sup
            return taux_3enf*(nb_enf >= 3) + (taux_supp*maximum(nb_enf - 3, 0))

        maj_enf = _taux_enf(nb_enf, P)*pension_brute
        return maj_enf

    def trimesters_tot(self, regime='all'):
        pass

    def trim_maj_tot(self, regime='all'):
        pass

    def trim_maj_enf_tot(self, regime='all'):
        pass

    def decote(self, trim_decote, nb_trimesters):
        P = reduce(getattr, self.param_name.split('.'), self.P)
        decote = P.decote.taux*trim_decote
        return decote*(nb_trimesters > 0)

    def pension_brute(self, data, taux,
                      coeff_proratisation, salref):
        return coeff_proratisation*salref*taux

    def pension(self, plafond_pension, majoration_pension):
        # Remarque : la majoration de pension s'applique à la pension rapportée au maximum ou au minimum
        return plafond_pension + majoration_pension # TODO: delete because in bonif_pension

    def N_CP(self):
        P = reduce(getattr, self.param_name.split('.'), self.P)
        return P.prorat.n_trim / 4

    def n_trim(self):
        P = reduce(getattr, self.param_name.split('.'), self.P)
        return P.plein.n_trim / 4

    def DA(self, nb_trimesters, trim_maj_ini):
        return (nb_trimesters + trim_maj_ini)/4


class RegimeComplementaires(Regime):

    def __init__(self):
        Regime.__init__(self)
        self.param_base = None
        self.regime_base = None

    def nombre_points(self, data, sali_for_regime):
        ''' Détermine le nombre de point à liquidation de la pension dans les
        régimes complémentaires (pour l'instant Ok pour ARRCO/AGIRC)
        Pour calculer ces points, il faut diviser la cotisation annuelle
        ouvrant des droits par le salaire de référence de l'année concernée
        et multiplier par le taux d'acquisition des points'''
        Plong_regime = reduce(getattr, self.param_name.split('.'), self.P_longit) #getattr(self.P_longit.prive.complementaire,  self.name)
        salref = Plong_regime.sal_ref
        taux_cot = Plong_regime.taux_cot_moy
        sali_plaf = sali_for_regime
        assert len(salref) == sali_plaf.shape[1] == len(taux_cot)
        nombre_points = zeros(sali_plaf.shape)
        for ix_year in range(sali_plaf.shape[1]):
            if salref[ix_year] > 0:
                nombre_points[:, ix_year] = (taux_cot[ix_year].calc(sali_plaf[:, ix_year])/salref[ix_year])
        nb_points_by_year = nombre_points.round(2)
        return nb_points_by_year

    def minimum_points(self, nombre_points):
        ''' Application de la garantie minimum de points '''
        P = reduce(getattr, self.param_name.split('.'), self.P)
        gmp = P.gmp
        nb_points = maximum(nombre_points, gmp)*(nombre_points > 0)
        return nb_points.sum(axis=1)

    def coefficient_age(self, data, nb_trimesters):
        ''' TODO: add surcote  pour avant 1955 '''
        P = reduce(getattr, self.param_name.split('.'), self.P)
        coef_mino = P.coef_mino
        agem = data.info_ind['agem']
        age_annulation_decote = self.P.prive.RG.decote.age_null
        diff_age = divide(age_annulation_decote - agem, 12)*(age_annulation_decote > agem)
        coeff_min = zeros(len(agem))
        for nb_annees, coef_mino in coef_mino._tranches:
            coeff_min += (diff_age == nb_annees)*coef_mino

        coeff_min += P.coeff_maj*diff_age
        if P.cond_taux_plein == 1:
            # Dans ce cas, la minoration ne s'applique que si la durée de cotisation au régime général est inférieure à celle requise pour le taux plein
            n_trim = self.P.prive.RG.plein.n_trim
            # la bonne formule est la suivante :
            # coeff_min = coeff_min*(n_trim > nb_trimesters) + (n_trim <= nb_trimesters)
            # mais on a ça...
            coeff_min = 1
        return coeff_min

    def majoration_enf(self, data, nombre_points):
        ''' Application de la majoration pour enfants à charge. Deux types de
        majorations peuvent s'appliquer :
          - pour enfant à charge au moment du départ en retraite
          - pour enfant nés et élevés en cours de carrière (majoration sur la totalité des droits acquis)
        C'est la plus avantageuse qui s'applique.'''
        P = reduce(getattr, self.param_name.split('.'), self.P)
        P_long = reduce(getattr, self.param_name.split('.'), self.P_longit).maj_enf
        nb_pac = data.info_ind['nb_pac'].copy()
        nb_born = data.info_ind['nb_enf_all'].copy()

        # 1- Calcul des points pour enfants à charge
        taux_pac = P.maj_enf.pac.taux
        points_pac = nombre_points.sum(axis=1)*taux_pac*nb_pac

        # 2- Calcul des points pour enfants nés ou élevés
        points_born = zeros(len(nb_pac))
        nb_enf_maj = zeros(len(nb_pac))
        for num_dispo in [0, 1]:
            P_dispositif = getattr(P.maj_enf.born, 'dispositif' + str(num_dispo))
            selected_dates = getattr(P_long.born, 'dispositif' + str(num_dispo)).dates
            taux_dispositif = P_dispositif.taux
            nb_enf_min = P_dispositif.nb_enf_min
            nb_points_dates = multiply(nombre_points, selected_dates).sum(axis=1)
            nb_points_enf = nb_points_dates*taux_dispositif*(nb_born >= nb_enf_min)
            if hasattr(P_dispositif, 'taux_maj'):
                taux_maj = P_dispositif.taux_maj
                plaf_nb = P_dispositif.nb_enf_count
                nb_enf_maj = maximum(minimum(nb_born, plaf_nb) - nb_enf_min, 0)
                nb_points_enf += nb_enf_maj*taux_maj*nb_points_dates

            points_born += nb_points_enf
        # Retourne la situation la plus avantageuse
        val_point = P.val_point
        if compare_destinie:
            val_point = P.val_point_proj
        if compare_destinie:
            return points_born*val_point
        return maximum(points_born, points_pac)*val_point

    def majoration_pension(self, majoration_enf):
        return majoration_enf

    def nb_points(self, nombre_points):
        return nombre_points.sum(axis=1)

    def pension(self, data, coefficient_age, nombre_points,
                majoration_pension, minimum_points, trim_decote):
        P = reduce(getattr, self.param_name.split('.'), self.P)
        val_point = P.val_point
        if compare_destinie:
            val_point = P.val_point_proj
        pension = minimum_points*val_point
        P = reduce(getattr, self.param_name.split('.'), self.P)
        pension = pension + majoration_pension
        decote = trim_decote*P.taux_decote
        pension = (1 - decote)*pension
        return pension*coefficient_age
