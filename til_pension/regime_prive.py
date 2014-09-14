# -*- coding:utf-8 -*-

from datetime import datetime

from numpy import minimum, maximum, array, divide, multiply, isnan

from til_pension.regime import RegimeBase
from til_pension.trimesters_functions import nb_trim_surcote, nb_trim_decote


def date_(year, month, day):
    return datetime.date(year, month, day)


class RegimePrive(RegimeBase):

    def __init__(self):
        RegimeBase.__init__(self)
        self.param_name = 'prive.RG'
        # TODO: move P.prive.RG used in the subclass RegimePrive in P.prive
        self.param_name_bis = None

    def sal_cot(self, data):
        select = data.workstate.isin(self.code_regime)
        sal = data.sali*select
        sal[isnan(sal)] = 0
        return sal

    def trim_cot_by_year(self, data, sal_cot):
        P_long = reduce(getattr, self.param_name.split('.'), self.P_longit)
        salref = P_long.salref
        plafond = 4  # nombre de trimestres dans l'année
        ratio = divide(sal_cot, salref).astype(int)
        return minimum(ratio, plafond)

    def nb_trimesters(self, trimesters):
        return trimesters.sum(axis=1)

    def trim_maj_ini(self, trim_maj_mda_ini):  # sert à comparer avec pensipp
        return trim_maj_mda_ini

    def trim_maj(self, trim_maj_mda):
        return trim_maj_mda

    def age_min_retirement(self):
        P = reduce(getattr, self.param_name.split('.'), self.P)
        return P.age_min

    def salref(self, data, sal_regime):
        ''' SAM : Calcul du salaire annuel moyen de référence :
        notamment application du plafonnement à un PSS'''
        P = reduce(getattr, self.param_name_bis.split('.'), self.P)
        nb_best_years_to_take = P.nb_years
        plafond = self.P_longit.common.plaf_ss
        revalo = self.P_longit.prive.RG.revalo

        revalo = array(revalo)
        for i in range(1, len(revalo)):
            revalo[:i] *= revalo[i]

        sal_regime.translate_frequency(output_frequency='year', method='sum', inplace=True)
        years_sali = (sal_regime != 0).sum(axis=1)
        nb_best_years_to_take = array(nb_best_years_to_take)
        nb_best_years_to_take[years_sali < nb_best_years_to_take] = \
            years_sali[years_sali < nb_best_years_to_take]

        if plafond is not None:
            assert sal_regime.shape[1] == len(plafond)
            sal_regime = minimum(sal_regime, plafond)
        if revalo is not None:
            assert sal_regime.shape[1] == len(revalo)
            sal_regime = multiply(sal_regime, revalo)
        salref = sal_regime.best_dates_mean(nb_best_years_to_take)
        return salref.round(2)

    def trim_decote(self, data, trimesters_tot, trim_maj_enf_tot):
        ''' Détermination de la décote à appliquer aux pensions '''
        P = reduce(getattr, self.param_name.split('.'), self.P)
        agem = data.info_ind['agem']
        if P.decote.dispositif == 1:
            age_annulation = P.decote.age_null
            trim_decote = max(divide(age_annulation - agem, 3), 0)
        elif P.decote.dispositif == 2:
            trim_decote = nb_trim_decote(trimesters_tot, trim_maj_enf_tot, agem, P)
        return trim_decote

    def age_annulation_decote(self):
        ''' Détermination de l'âge d'annularion de la décote '''
        P = reduce(getattr, self.param_name.split('.'), self.P)
        return P.decote.age_null

    def coeff_proratisation(self, info_ind, nb_trimesters, trim_maj):
        ''' Calcul du coefficient de proratisation '''

        def _assurance_corrigee(trim_regime, agem):
            '''
            Deux types de corrections :
            - correction de 1948-1982
            - Détermination de la durée d'assurance corrigée introduite par la réforme Boulin
            (majoration quand départ à la retraite après 65 ans) à partir de 1983'''
            P = reduce(getattr, self.param_name.split('.'), self.P)

            if P.prorat.dispositif == 1:
                correction = (P.prorat.n_trim - trim_regime)/2
                return trim_regime + correction
            elif P.prorat.dispositif == 2:
                age_taux_plein = P.decote.age_null
                trim_majo = divide(agem - age_taux_plein, 3)*(agem > age_taux_plein)
                elig_majo = (trim_regime < P.prorat.n_trim)
                correction = trim_regime*P.tx_maj*trim_majo*elig_majo
                return trim_regime + correction
            else:
                return trim_regime

        P = reduce(getattr, self.param_name.split('.'), self.P)
        trim_regime = trim_maj + nb_trimesters  # _assurance_corrigee(trim_regime, agem)
        # disposition pour montée en charge de la loi Boulin (ne s'applique qu'entre 72 et 74) :
        if P.prorat.application_plaf == 1:
            trim_regime = minimum(trim_regime, P.prorat.plaf)
        CP = minimum(1, divide(trim_regime, P.prorat.n_trim))
        return CP

    def surcote(self, data, trimesters, trimesters_tot, date_start_surcote):
        ''' Détermination de la surcote à appliquer aux pensions.'''
        P = reduce(getattr, self.param_name.split('.'), self.P)
        P_long = reduce(getattr, self.param_name.split('.'), self.P_longit)
        # dispositif de type 0
        n_trim = array(P.plein.n_trim, dtype=float)
        trim_tot = trimesters_tot.sum(axis=1)
        surcote = P.surcote.dispositif0.taux*(trim_tot - n_trim)*(trim_tot > n_trim)
        # Note surcote = 0 après 1983
        # dispositif de type 1
        if P.surcote.dispositif1.taux > 0:
            trick = P.surcote.dispositif1.date_trick
            trick = str(int(trick))
            selected_dates = getattr(P_long.surcote.dispositif1, 'dates' + trick)
            if sum(selected_dates) > 0:
                surcote += P.surcote.dispositif1.taux * \
                    nb_trim_surcote(trimesters, selected_dates,
                                    date_start_surcote)

        # dispositif de type 2
        P2 = P.surcote.dispositif2
        if P2.taux0 > 0:
            selected_dates = P_long.surcote.dispositif2.dates
            basic_trim = nb_trim_surcote(trimesters, selected_dates,
                                         date_start_surcote)
            maj_age_trim = nb_trim_surcote(trimesters, selected_dates,
                                           12*P2.age_majoration)
#             date_start_surcote_65 = self._date_start_surcote(trimesters_tot,
#                                           trim_maj, age, age_start_surcote)
            # TODO: why it doesn't equal date_start_surcote ?
            basic_trim = basic_trim - maj_age_trim
            trim_with_majo = (basic_trim - P2.trim_majoration) * \
                             ((basic_trim - P2.trim_majoration) >= 0)
            basic_trim = basic_trim - trim_with_majo
            surcote += P2.taux0*basic_trim + \
                P2.taux_maj_trim*trim_with_majo + \
                P2.taux_maj_age*maj_age_trim
        return surcote

    def minimum_pension(self, trimesters_tot, nb_trimesters, trim_maj, pension_reg, pension_all):
        ''' MICO du régime général : allocation différentielle
        RQ : ASPA et minimum vieillesse sont gérés par OF
        Il est attribué quels que soient les revenus dont dispose le retraité
        en plus de ses pensions :
         loyers, revenus du capital, activité professionnelle...
        + mécanisme de répartition si cotisations à plusieurs régimes
        TODO: coder toutes les évolutions et rebondissements 2004/2008'''
        P = reduce(getattr, self.param_name.split('.'), self.P)
        # pension_RG, pension, trim_RG, trim_cot, trim
        trim_regime = nb_trimesters + trim_maj
        coeff = minimum(1, divide(trim_regime, P.prorat.n_trim))
        if P.mico.dispositif == 0:
            # Avant le 1er janvier 1983, comparé à l'AVTS
            min_pension = self.P.common.avts
            return maximum(min_pension - pension_reg, 0)*coeff
        elif P.mico.dispositif == 1:
            # TODO: Voir comment gérer la limite de cumul relativement
            # complexe (Doc n°5 du COR)
            mico = P.mico.entier
            return maximum(mico - pension_reg, 0)*coeff
        elif P.mico.dispositif == 2:
            # A partir du 1er janvier 2004 les périodes cotisées interviennent
            # (+ dispositif transitoire de 2004)
            nb_trim = P.prorat.n_trim
            trim_regime = nb_trimesters  # + sum(trim_maj)
            mico_entier = P.mico.entier*minimum(divide(trim_regime, nb_trim), 1)
            maj = (P.mico.entier_maj - P.mico.entier)*divide(trimesters_tot, nb_trim)
            mico = mico_entier + maj*(trimesters_tot >= P.mico.trim_min)
            return (mico - pension_reg)*(mico > pension_reg)*(pension_reg > 0)

    def plafond_pension(self, pension_brute, salref, coeff_proratisation, surcote):
        ''' plafonnement à 50% du PSS
        TODO: gérer les plus de 65 ans au 1er janvier 1983'''
        PSS = self.P.common.plaf_ss
        P = reduce(getattr, self.param_name.split('.'), self.P)
        taux_plein = P.plein.taux
        taux_PSS = P.plafond
        pension_surcote_RG = taux_plein*salref*coeff_proratisation*surcote
        return minimum(pension_brute - pension_surcote_RG, taux_PSS*PSS) + \
            pension_surcote_RG