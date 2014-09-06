# -*- coding:utf-8 -*-
import numpy as np
import pandas as pd
from xml.dom import minidom
from datetime import datetime, date, timedelta

def multiple_lists(element, date):
    seuils = []
    values = []
    for val in element.getElementsByTagName("VALUE"):
        try:
            deb = datetime.strptime(val.getAttribute('deb'),"%Y-%m-%d").date()
            fin   = datetime.strptime(val.getAttribute('fin'),"%Y-%m-%d").date()
            if deb <= date <= fin:
                valeur = float(val.getAttribute('valeur'))
                seuil =  datetime.strptime(val.getAttribute('valeurcontrol'),"%Y-%m-%d").date()
                if not valeur is None and not seuil is None:
                    values = values + [valeur]
                    seuils =  seuils + [seuil]
        except Exception, e:
            code = element.getAttribute('code')
            raise Exception("Problem error when dealing with %s : \n %s" %(code,e))

    return values, seuils

def TranchesAttr(node, V, S):
        nb_tranches = len(S)
        S = S + ["unbound"]
        for i in range(nb_tranches):
            seuilinf  = 'tranche'+ str(i) + '_seuilinf'
            seuilsup  = 'tranche'+ str(i) + '_seuilsup'
            setattr(node, seuilinf, S[i])
            setattr(node, seuilsup, S[i+1])
            setattr(node, 'tranche%d' %i, V[i])
            setattr(node, '_nb', nb_tranches)
        return node

class Tree2Object(object):
    def __init__(self, node, default = False):
        for child in node._children:
            setattr(self, child.code, child)
        for a, b in self.__dict__.iteritems():

            if b.typeInfo == 'CODE' or b.typeInfo == 'BAREME':
                if default:
                    setattr(self,a, b.default)
                else:
                    setattr(self,a, b.value)

            elif  b.typeInfo == 'VALBYTRANCHES' :
                setattr(self, a, b)

            else:
                setattr(self,a, Tree2Object(b, default))

def from_excel_to_xml(data, code, data_date, description, xml = 'test_xml', format = "integer", ascendant_date = False, format_date = None):
    ''' Fonction qui transforme une colonne de data en lignes .xml '''
    def _format_date(date):
        day = date[0:2]
        month = date[3:5]
        year = date[6:]
        date = year + "-" + month + "-" + day
        return date

    if ascendant_date:
        data = data[::-1]
        data_date = data_date[::-1]

    with open(xml, "w") as f:
        to_write = '<CODE description="' + description + '" code="' + code + '" format="' + format + '">\n'
        f.write(to_write)
        # Insertions des paramètres
        for i in range(len(data)):
            if i == 0:
                fin = "2100-12-01"
            else:
                fin = str(datetime.strptime(debut,"%Y-%m-%d").date() - timedelta(days=1))
            if format_date == 'year':
                debut = str(data_date[i]) + "-01-01"
            else:
                debut = str(data_date[i])[0:10]
            if format_date == "/":
                debut = _format_date(debut)
                fin = _format_date(fin)
            to_write ='  <VALUE valeur="' + str(data[i]) + '" deb="' + debut + '" fin="' + fin + '"/>\n'
            f.write(to_write)
        to_write = '</CODE>\n'
        f.write(to_write)
        # Corps du dofile
        f.close()

if __name__ == '__main__':
    # Examples
    example = False
    if example:
        data = [0,2,3,99]
        date = ["01/04/2013", "01/04/2012", "01/04/2011", "01/04/2010"]
        code = "test"
        description = "salut"
        from_excel_to_xml(data, code, date, description, xml = 'test_xml', format_date = '/')

        date = [2009,2010,2011,2012]
        from_excel_to_xml(data, code, date, description, xml = 'test_xml', ascendant_date = True, format_date = 'year')



    #########
    # Séries chronologiques alimentant le noeud 'common'
    ########

    def _francs_to_euro(data,ix):
        data = [w.replace(',', '.') for w in data.astype(str)]
        data = [w.replace('FRF', '')  for w in data]
        data = [w.replace(' ', '') for w in data]
        data = np.array(data, dtype = np.float)
        data[ix:] =data[ix:] / 6.5596
        return data.round(2)

    def _oldfrancs_to_francs(data,ix):
        data = [w.replace(',', '.') for w in data.astype(str)]
        data = [w.replace('AF', '')  for w in data]
        data = [w.replace(' ', '') for w in data]
        data = np.array(data, dtype = np.float)
        data[ix:] = data[ix:] /  100
        return data

    # 1 -- Importation des Baremes IPP
    '''
    xlsxfile = pd.ExcelFile('Bareme_retraite.xlsx')
    # AVTS
    data = xlsxfile.parse('AVTS_montants (1962-2013)', index_col = None)
    #print data.ix[1:14, 'date'].to_string()
    dates = np.array(data.ix[1:, 'date'])
    avts = data.ix[1:, 'avts']
    avts = _francs_to_euro(avts, 13)
    plaf_avts_seul = np.array(data.ix[1:, 'plaf_mv_seul'])
    plaf_avts_seul = _francs_to_euro(plaf_avts_seul, 13)
    plaf_avts_couple = np.array(data.ix[1:, 'plaf_mv_men'])
    plaf_avts_couple = _francs_to_euro(plaf_avts_couple, 13)

    #from_excel_to_xml(data = avts, description = "Montant de l'allocations aux vieux travailleurs salariés", code = "montant", format = "float", data_date = dates)
    #from_excel_to_xml(data = plaf_avts_seul, description = "Plafond de ressources - personne seul", code = "plaf_seul", format = "float", data_date = dates)
    #from_excel_to_xml(data = plaf_avts_couple, description = "Plafond de ressources - couple", code = "plaf_couple", format = "float", data_date = dates)
    data = xlsxfile.parse('AVTS2', index_col = None)
    dates = np.array(data.ix[1:, 'date'])
    avtsold = data.ix[1:, 'avts2']
    avtsold = _oldfrancs_to_francs(avtsold, 2)
    avtsold = _francs_to_euro(avtsold, 0)
    from_excel_to_xml(data = avtsold, description = "AVTS", code = "avtsold", format = "float", data_date = dates)

        # 2 -- Importation du Excel ParamSociaux
    xlsxfile = pd.ExcelFile('ParamSociaux2.xls')
    # 2.a - Paramètres généraux
    data = xlsxfile.parse('ParamGene', index_col = None, header = True)
    dates = np.array(data.index)
    indice =  np.array(data['Indice Prix'])
    #from_excel_to_xml(data = indice, description = "Indice des prix", code = "ip_reval", format = "float", data_date = dates, ascendant_date = True, format_date = 'year')

    plaf_ss =  np.array(data['Plafond SS'])
    #from_excel_to_xml(data = plaf_ss, description = "Plafond de la sécurité sociale", code = "plaf_ss", format = "float", data_date = dates, ascendant_date = True, format_date = 'year')

    smic = np.array((data['SMIC']).round(2))
    #from_excel_to_xml(data = smic, description = "SMIC horaire projeté à partir du SMPT ", code = "smic_proj", format = "float", data_date = dates, ascendant_date = True, format_date = 'year')

    smpt = np.array(data['SMPT '])
    #from_excel_to_xml(data = smpt, description = "SMPT - Hypothèse d'évolution selon le scénario C du COR + inflation", code = "smpt", format = "float", data_date = dates, ascendant_date = True, format_date = 'year')

    point_fp = np.array(data['Valeur point FP'])
    #from_excel_to_xml(data=point_fp, description="Valeur du point Fonction Publique", code="point", format="float", data_date = dates, ascendant_date=True, format_date='year')

    # 2.b - Régimes complémentaires
    data = xlsxfile.parse('ParamRetrComp', index_col = None, header = True)
    dates = np.array(data.index)
    val_point_arrco =  np.array(data['VP UNIRS/ ARRCO en euros'])
    #from_excel_to_xml(data = val_point_arrco, description = "Valeur du point UNIRS/ARRCO, en euros (paramètre Destinie)", code = "val_point_proj", format = "float", data_date = dates, ascendant_date = True, format_date = 'year')
    val_point_agirc =  np.array(data['VP Agirc en euros'])
    from_excel_to_xml(data = val_point_agirc, description = "Valeur du point AGIRC, en euros (paramètre Destinie)", code="val_point_proj", format="float", data_date=dates, ascendant_date=True, format_date='year')
        # 3 -- Importation du Excel Bareme_Emploi
    xlsxfile = pd.ExcelFile('Bareme_Emploi.xlsx')
    # Paramètres généraux
    data = xlsxfile.parse('SMIC', index_col = None, header = True)
    smic =  np.array(data['Smic brut (horaire)'][:107])
    smic = _francs_to_euro(smic,17)
    dates = np.array(data["Date d'effet"][:107])
    #from_excel_to_xml(data = smic, description = "Montant du smic horaire", code = "smic", format = "float", data_date = dates)

        # 4 --Importation des barèmes IPP retraite
    xlsxfile = pd.ExcelFile('Retraite.xlsx')

    # Paramètres généraux
    data = xlsxfile.parse('MICO', index_col = None, header = True)
    mico =  np.array(data['Minimum contributif'][1:42])
    mico = _francs_to_euro(mico,13)
    dates = np.array(data[u"Date d'entrée en vigueur"][1:42])
    #from_excel_to_xml(data = mico, description = "Minimum contributif (annuel)", code = "mico", format = "float", data_date = dates)
    mico_maj =  np.array(data['Minimum contributif majoré'][1:12])
    #from_excel_to_xml(data = mico_maj, description = "Minimum contributif majoré", code = "maj", format = "float", data_date = dates[:12])

    # Paramètres ARRCO
    data = xlsxfile.parse('SALREF-ARRCO', index_col = None, header = True)
    arrco =  np.array(data[u'Salaire de référence (en euros)'])
    dates = np.array(data[u"Date d'entrée en vigueur"])
    #from_excel_to_xml(data = arrco, description = "Salaires de référence pour validation des points (en euros)", code = "sal_ref", format = "float", data_date = dates)

    data = xlsxfile.parse('PT-ARRCO', index_col = None, header = True)
    arrco =  np.array(data[u'Valeur du point ARRCO (en euros)'])[: -5]
    dates = np.array(data[u"Date d'entrée en vigueur"])
    dates = dates[:len(arrco)]
    #from_excel_to_xml(data = arrco, description = "Valeur du point ARRCO (en euros)", code = "val_point", format = "float", data_date = dates)

    # Paramètres AGIRC
    data = xlsxfile.parse('SALREF-AGIRC', index_col = None, header = True)
    salref_agirc=  np.array(data[ u"Salaire de référence AGIRC (prix d'achat) en euros"])[:-3]
    dates = np.array(data[u"Date d'entrée en vigueur"])[:-3]
    #from_excel_to_xml(data = salref_agirc, description = "Salaires de référence pour validation des points (en euros)", code = "sal_ref", format = "float", data_date = dates)

    data = xlsxfile.parse('PT-AGIRC', index_col = None, header = True)
    agirc =  np.array(data[u'Valeur du point AGIRC (en euros)'])[:-7].round(4)
    dates = np.array(data[u"Date d'entrée en vigueur"])[:-7]
    #from_excel_to_xml(data = agirc, description = "Valeur du point AGIRC (en euros)", code = "val_point", format = "float", data_date = dates)

    # AVPF
    data = xlsxfile.parse('AVPF', index_col = None, header = True)
    avpf = data["Montant mensuel de l'Assurance vieillesse des parents au foyer (AVPF)"][1:50]
    dates = data[u"Date d'entrée en vigueur"][1:50]
    avpf =  _francs_to_euro(np.array(avpf), 15)
    dates = np.array(dates)
    #from_excel_to_xml(data=avpf, description = "Assurance vieillesse des parents au foyer", code = "avpf", format = "float", data_date = dates)


        # 5 -- Importation des paramètres Destinie :
    # 5-1 : retraite de base
    Retbase = pd.read_csv('ParamRetBase.csv', sep=";")
    dates = np.array(Retbase['annee'])
    revalo = np.array(Retbase['Reval SPC'])
    #from_excel_to_xml(data = revalo, description = "Coefficient de revalorisation des pensions (coeff. Destinie)", code = "revalo", format = "float", data_date = dates, format_date = 'year', ascendant_date = True)

    # 5-2 : retraite complémentaire
    Retcomp = pd.read_csv('ParamRetComp.csv', sep=";")
    dates = np.array(Retcomp['annee'])
    taux_1 = np.array(Retcomp['Tx  ARRCO tot Tranche 1'])
    taux_2 = np.array(Retcomp['Tx ARRCO tot tranche 2'])
    taux_appel = np.array(Retcomp["Taux d'appel ARRCO"])
    salref =  np.array(Retcomp[u'Salaire de r_f_rence UNIRS/ ARRCO en euros'])[:69] #On ne prend qu'avant 1998 car après actualisé sur Barèmes IPP
    vp_point =  np.array(Retcomp[u'VP UNIRS/ ARRCO en euros'])[:69] #On ne prend qu'avant 1998 car après actualisé sur Barèmes IPP
    #from_excel_to_xml(data = taux_1, description = "Taux d'acquisition des points pour le première tranche", code = "taux_ac", format = "float", data_date = dates, format_date = 'year', ascendant_date = True)
    '''
        # 6 - importation des taux de cotisations (barèmes IPP)
    prelsoc = pd.ExcelFile('Baremes IPP - prelevements sociaux.xlsx')
    
    # 6.1 - CET
    cet = prelsoc.parse("CET",index_col = None, header = True)
    cet_sal = cet["salarie"][0:5]
    cet_empl = cet["employeur"][0:5]
    dates = cet[u"Date d'entrée en vigueur"][0:5]
    dates = np.array(dates)
    #from_excel_to_xml(data=cet_sal, description = "Cotisation Exceptionnelle et Temporaire, cotisation salariale pour les cadres du régime Agirc", code = "cot_sal", format = "float", data_date = dates)
    #from_excel_to_xml(data=cet_empl, description = "Cotisation Exceptionnelle et Temporaire, cotisation employeur pour les cadres du régime Agirc", code = "cot_pat", format = "float", data_date = dates)

    # 6.2 - Retenus sur pensions (fonction publique)
    rp = prelsoc.parse("RP",index_col = None, header = True)
    rp_sal = rp["Retenues"][0:17]
    dates = rp[u"Date d'entrée en vigueur"][0:17]
    dates = np.array(dates)
    #from_excel_to_xml(data=rp_sal, description = "", code = "rp_sal", format = "float", data_date = dates)
    
    rp = prelsoc.parse("RET-Etat",index_col = None, header = True)
    dates = rp[u"Date d'entrée en vigueur"][11:22]
    dates = np.array(dates)
    rp_pat_impl = np.array(rp["Taux implicite"][11:22])
    #from_excel_to_xml(data=rp_pat_impl, description = u"Cotisation retraite de l'Etat employeur, implicite (jusqu'en 2005)", code = "rp_pat_impl", format = "float", data_date = dates)

    dates = rp[u"Date d'entrée en vigueur"][0:11]
    dates = np.array(dates)
    rp_pat_pc = np.array(rp["Pensions civils"][0:11])
    #from_excel_to_xml(data=rp_pat_pc, description = u"Cotisation retraite de l'Etat employeur, pensions civiles taux explicite", code = "rp_pat_pc", format = "float", data_date = dates)

    rp_pat_pc = np.array(rp["Pensions militaires"][0:11])
    #from_excel_to_xml(data=rp_pat_pc, description = u"Cotisation retraite de l'Etat employeur, pensions militaires taux explicite", code = "rp_pat_pm", format = "float", data_date = dates)
    
        # 6.3 - Retenus sur pensions (artisans et commerçants)
    rp = prelsoc.parse("RET-AC",index_col = None, header = True)
    dates = rp[u"Date d'entrée en vigueur"][1:16]
    dates = np.array(dates)
    
    cot_arti = np.array(rp["Artisans"][1:16])
    cot_indus= np.array(rp[u"Industriels et commercants"][1:16])
    #from_excel_to_xml(data=cot_arti, description = u"Cotisations à l'assurance-vieillesse des professions artisanales ", code = "cot_arti", format = "float", data_date = dates)
    #from_excel_to_xml(data=cot_indus, description = u"Cotisations à l'assurance-vieillesse des professions industrielles et commerciales", code = "cot_indus", format = "float", data_date = dates)

        # 6.4 taux de cotisations RG
    rg = prelsoc.parse("CNAV",index_col = None, header = True)
    #print rg.columns
    dates = rg[u"Date d'entrée en vigueur"][0:18]
    cot_sal_plaf = np.array(rg[u"Sal_1_pss"][0:18].fillna(0))
    cot_emp_plaf = np.array(rg[u"empl_1_pss"][0:18].replace(np.nan, 0))
    cot_sal = np.array(rg[u"Salariés"][0:18]) + cot_sal_plaf
    cot_emp = np.array(rg[u"Employeurs"][0:18]) 
    cot_emp2 = cot_emp + + cot_emp_plaf
    dates = np.array(dates)
    #from_excel_to_xml(data=cot_sal_plaf, description = u"Cotisations retraites pour les salariés de Régime Général, inférieur à 1PSS ", code = "cot_sal_plaf", format = "float", data_date = dates)
    #from_excel_to_xml(data=cot_sal, description = u"Cotisations retraites pour les salariés de Régime Général, ensemble du salaire", code = "cot_sal", format = "float", data_date = dates)
   # from_excel_to_xml(data=cot_emp, description = u"Cotisations retraites pour les salariés de Régime Général, inférieur à 1PSS ", code = "cot_sal_plaf", format = "float", data_date = dates)
    #from_excel_to_xml(data=cot_sal, description = u"Cotisations retraites pour les salariés de Régime Général, ensemble du salaire", code = "cot_sal", format = "float", data_date = dates)
    
    
        #6.5 Taux de cotisations ARRCO
    arrco = prelsoc.parse("ARRCO",index_col = None, header = True)
    print arrco.columns
    dates = arrco[u"Date d'entrée en vigueur"][0:26]
    dates = np.array(dates)
    cot_sal_1 = np.array(arrco[u"tranche1_sal"][0:26].fillna(0))
    cot_sal_2 = np.array(arrco[u"tranche2_sal"][0:26].fillna(0))
    cot_sal_297 = np.array(arrco[u"tranche2_sal_97"][0:26].fillna(0))
    #from_excel_to_xml(data=cot_sal_2, description = u"", code = "", format = "float", data_date = dates)
    
    cot_emp_1 = np.array(arrco[u"tranche1_emp"][0:26].fillna(0))
    cot_emp_2 = np.array(arrco[u"tranche2_emp"][0:26].fillna(0))
    cot_emp_297 = np.array(arrco[u"tranche_2_emp_97"][0:26].fillna(0))
    #from_excel_to_xml(data=cot_emp_2, description = u"", code = "", format = "float", data_date = dates)
    
        #6.6 Taux de cotisations AGIRC
    agirc = prelsoc.parse("AGIRC",index_col = None, header = True)
    print agirc.columns
    dates = agirc[u"Date d'entrée en vigueur"][0:26]
    dates = np.array(dates)
    cot_sal_B = np.array(agirc[u"sal_B"][0:26])
    cot_sal_C = np.array(agirc[u"sal_C"][0:26])
    cot_sal_B81 = np.array(agirc[u"sal_B_81"][0:26])
    cot_sal_C81 = np.array(agirc[u"sal_C_81"][0:26])
    #from_excel_to_xml(data=cot_sal_C81, description = u"", code = "", format = "float", data_date = dates)
    
    cot_emp_B = np.array(agirc[u"emp_B"][0:26])
    cot_emp_C = np.array(agirc[u"emp_C"][0:26])
    cot_emp_B81 = np.array(agirc[u"emp_B_81"][0:26])
    cot_emp_C81 = np.array(agirc[u"emp_C_81"][0:26])
    from_excel_to_xml(data=cot_emp_C81, description = u"", code = "", format = "float", data_date = dates)

    
#TODO: import IRCANTEC et collectivites locales
