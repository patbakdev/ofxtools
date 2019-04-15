# coding: utf-8
""" Unit tests for models.invest """
# stdlib imports
import unittest
from xml.etree.ElementTree import Element, SubElement
from decimal import Decimal
from datetime import datetime
from copy import deepcopy


# local imports
from ofxtools.models.base import Aggregate
from ofxtools.models.bank.stmt import INV401KSOURCES
from ofxtools.models.invest.acct import INVSUBACCTS
from ofxtools.models.invest.transactions import (
    BUYTYPES,
    SELLTYPES,
    OPTBUYTYPES,
    OPTSELLTYPES,
)
from ofxtools.models.invest.openorders import (
    UNITTYPES,
    OO,
    OOBUYDEBT,
    OOBUYMF,
    OOBUYOPT,
    OOBUYOTHER,
    OOBUYSTOCK,
    OOSELLDEBT,
    OOSELLMF,
    OOSELLOPT,
    OOSELLOTHER,
    OOSELLSTOCK,
    SWITCHMF,
    INVOOLIST,
)
from ofxtools.models.invest.securities import SECID
from ofxtools.models.i18n import CURRENCY, CURRENCY_CODES
from ofxtools.utils import UTC, classproperty


# test imports
import base
from test_models_securities import SecidTestCase
from test_models_bank_stmt import StmttrnTestCase
from test_models_i18n import CurrencyTestCase


class OoTestCase(unittest.TestCase, base.TestAggregate):
    __test__ = True

    requiredElements = [
        "FITID",
        "SECID",
        "DTPLACED",
        "UNITS",
        "SUBACCT",
        "DURATION",
        "RESTRICTION",
    ]
    optionalElements = [
        "SRVRTID",
        "MINUNITS",
        "LIMITPRICE",
        "STOPPRICE",
        "MEMO",
        "CURRENCY",
        "INV401KSOURCE",
    ]
    oneOfs = {"SUBACCT": INVSUBACCTS,
              "DURATION": ("DAY", "GOODTILCANCEL", "IMMEDIATE"),
              "RESTRICTION": ("ALLORNONE", "MINUNITS", "NONE"),
              "CURSYM": CURRENCY_CODES, "INV401KSOURCE": INV401KSOURCES}

    @classproperty
    @classmethod
    def etree(cls):
        root = Element("OO")
        SubElement(root, "FITID").text = "1001"
        SubElement(root, "SRVRTID").text = "2002"
        root.append(SecidTestCase.etree)
        SubElement(root, "DTPLACED").text = "20040701000000.000[0:GMT]"
        SubElement(root, "UNITS").text = "150"
        SubElement(root, "SUBACCT").text = "CASH"
        SubElement(root, "DURATION").text = "GOODTILCANCEL"
        SubElement(root, "RESTRICTION").text = "ALLORNONE"
        SubElement(root, "MINUNITS").text = "100"
        SubElement(root, "LIMITPRICE").text = "10.50"
        SubElement(root, "STOPPRICE").text = "10.00"
        SubElement(root, "MEMO").text = "Open Order"
        root.append(CurrencyTestCase.etree)
        SubElement(root, "INV401KSOURCE").text = "PROFITSHARING"
        return root

    @classproperty
    @classmethod
    def aggregate(cls):
        return OO(fitid="1001", srvrtid="2002", secid=SecidTestCase.aggregate,
                  dtplaced=datetime(2004, 7, 1, tzinfo=UTC),
                  units=Decimal("150"), subacct="CASH",
                  duration="GOODTILCANCEL", restriction="ALLORNONE",
                  minunits=Decimal("100"), limitprice=Decimal("10.50"),
                  stopprice=Decimal("10.00"), memo="Open Order",
                  currency=CurrencyTestCase.aggregate,
                  inv401ksource="PROFITSHARING")

    def testPropertyAliases(cls):
        instance = Aggregate.from_etree(cls.etree)
        cls.assertEqual(instance.uniqueid, instance.secid.uniqueid)
        cls.assertEqual(instance.uniqueidtype, instance.secid.uniqueidtype)
        #  cls.assertEqual(instance.heldinacct, instance.invpos.heldinacct)
        #  cls.assertEqual(instance.postype, instance.invpos.postype)
        #  cls.assertEqual(instance.units, instance.invpos.units)
        #  cls.assertEqual(instance.unitprice, instance.invpos.unitprice)
        #  cls.assertEqual(instance.mktval, instance.invpos.mktval)
        #  cls.assertEqual(instance.dtpriceasof, instance.invpos.dtpriceasof)
        cls.assertEqual(instance.cursym, instance.currency.cursym)
        cls.assertEqual(instance.currate, instance.currency.currate)


class OobuydebtTestCase(unittest.TestCase, base.TestAggregate):
    __test__ = True

    requiredElements = ["OO", "AUCTION"]
    optionalElements = ["DTAUCTION"]

    @classproperty
    @classmethod
    def etree(cls):
        root = Element("OOBUYDEBT")
        root.append(OoTestCase.etree)
        SubElement(root, "AUCTION").text = "N"
        SubElement(root, "DTAUCTION").text = "20120109000000.000[0:GMT]"
        return root

    @classproperty
    @classmethod
    def aggregate(cls):
        return OOBUYDEBT(oo=OoTestCase.aggregate, auction=False,
                         dtauction=datetime(2012, 1, 9, tzinfo=UTC))


class OobuymfTestCase(unittest.TestCase, base.TestAggregate):
    __test__ = True

    requiredElements = ["OO", "BUYTYPE", "UNITTYPE"]
    oneOfs = {"BUYTYPE": BUYTYPES, "UNITTYPE": UNITTYPES}

    @classproperty
    @classmethod
    def etree(cls):
        root = Element("OOBUYMF")
        root.append(OoTestCase.etree)
        SubElement(root, "BUYTYPE").text = "BUY"
        SubElement(root, "UNITTYPE").text = "SHARES"
        return root

    @classproperty
    @classmethod
    def aggregate(cls):
        return OOBUYMF(oo=OoTestCase.aggregate, buytype="BUY",
                       unittype="SHARES")


class OobuyoptTestCase(unittest.TestCase, base.TestAggregate):
    __test__ = True

    requiredElements = ["OO", "OPTBUYTYPE"]
    oneOfs = {"OPTBUYTYPE": OPTBUYTYPES}

    @classproperty
    @classmethod
    def etree(cls):
        root = Element("OOBUYOPT")
        root.append(OoTestCase.etree)
        SubElement(root, "OPTBUYTYPE").text = "BUYTOOPEN"
        return root

    @classproperty
    @classmethod
    def aggregate(cls):
        return OOBUYOPT(oo=OoTestCase.aggregate, optbuytype="BUYTOOPEN")


class OobuyotherTestCase(unittest.TestCase, base.TestAggregate):
    __test__ = True

    requiredElements = ["OO", "UNITTYPE"]
    oneOfs = {"UNITTYPE": UNITTYPES}

    @classproperty
    @classmethod
    def etree(cls):
        root = Element("OOBUYOTHER")
        root.append(OoTestCase.etree)
        SubElement(root, "UNITTYPE").text = "SHARES"
        return root

    @classproperty
    @classmethod
    def aggregate(cls):
        return OOBUYOTHER(oo=OoTestCase.aggregate, unittype="SHARES")


class OobuystockTestCase(unittest.TestCase, base.TestAggregate):
    __test__ = True

    requiredElements = ["OO", "BUYTYPE"]
    oneOfs = {"BUYTYPE": BUYTYPES}

    @classproperty
    @classmethod
    def etree(cls):
        root = Element("OOBUYSTOCK")
        oo = OoTestCase.etree
        root.append(oo)
        SubElement(root, "BUYTYPE").text = "BUYTOCOVER"
        return root

    @classproperty
    @classmethod
    def aggregate(cls):
        return OOBUYSTOCK(oo=OoTestCase.aggregate, buytype="BUYTOCOVER")


class OoselldebtTestCase(unittest.TestCase, base.TestAggregate):
    __test__ = True

    requiredElements = ["OO"]
    optionalElements = []

    @classproperty
    @classmethod
    def etree(cls):
        root = Element("OOSELLDEBT")
        root.append(OoTestCase.etree)
        return root

    @classproperty
    @classmethod
    def aggregate(cls):
        return OOSELLDEBT(oo=OoTestCase.aggregate)


class OosellmfTestCase(unittest.TestCase, base.TestAggregate):
    __test__ = True

    requiredElements = ["OO", "SELLTYPE", "UNITTYPE", "SELLALL"]
    optionalElements = []
    oneOfs = {"SELLTYPE": SELLTYPES, "UNITTYPE": UNITTYPES}

    @classproperty
    @classmethod
    def etree(cls):
        root = Element("OOSELLMF")
        root.append(OoTestCase.etree)
        SubElement(root, "SELLTYPE").text = "SELLSHORT"
        SubElement(root, "UNITTYPE").text = "SHARES"
        SubElement(root, "SELLALL").text = "Y"
        return root

    @classproperty
    @classmethod
    def aggregate(cls):
        return OOSELLMF(oo=OoTestCase.aggregate, selltype="SELLSHORT",
                        unittype="SHARES", sellall=True)


class OoselloptTestCase(unittest.TestCase, base.TestAggregate):
    __test__ = True

    requiredElements = ["OO", "OPTSELLTYPE"]
    optionalElements = []
    oneOfs = {"OPTSELLTYPE": OPTSELLTYPES}

    @classproperty
    @classmethod
    def etree(cls):
        root = Element("OOSELLOPT")
        root.append(OoTestCase.etree)
        SubElement(root, "OPTSELLTYPE").text = "SELLTOCLOSE"
        return root

    @classproperty
    @classmethod
    def aggregate(cls):
        return OOSELLOPT(oo=OoTestCase.aggregate, optselltype="SELLTOCLOSE")


class OosellotherTestCase(unittest.TestCase, base.TestAggregate):
    __test__ = True

    requiredElements = ["OO", "UNITTYPE"]
    optionalElements = []
    oneOfs = {"UNITTYPE": UNITTYPES}

    @classproperty
    @classmethod
    def etree(cls):
        root = Element("OOSELLOTHER")
        root.append(OoTestCase.etree)
        SubElement(root, "UNITTYPE").text = "SHARES"
        return root

    @classproperty
    @classmethod
    def aggregate(cls):
        return OOSELLOTHER(oo=OoTestCase.aggregate, unittype="SHARES")


class OosellstockTestCase(unittest.TestCase, base.TestAggregate):
    __test__ = True

    requiredElements = ["OO", "SELLTYPE"]
    optionalElements = []
    oneOfs = {"SELLTYPE": SELLTYPES}

    @classproperty
    @classmethod
    def etree(cls):
        root = Element("OOSELLSTOCK")
        root.append(OoTestCase.etree)
        SubElement(root, "SELLTYPE").text = "SELLSHORT"
        return root

    @classproperty
    @classmethod
    def aggregate(cls):
        return OOSELLSTOCK(oo=OoTestCase.aggregate, selltype="SELLSHORT")


class SwitchmfTestCase(unittest.TestCase, base.TestAggregate):
    __test__ = True

    requiredElements = ["OO", "SECID", "UNITTYPE", "SWITCHALL"]
    optionalElements = []
    oneOfs = {"UNITTYPE": UNITTYPES}

    @classproperty
    @classmethod
    def etree(cls):
        root = Element("SWITCHMF")
        root.append(OoTestCase.etree)
        root.append(SecidTestCase.etree)
        SubElement(root, "UNITTYPE").text = "SHARES"
        SubElement(root, "SWITCHALL").text = "Y"
        return root

    @classproperty
    @classmethod
    def aggregate(cls):
        return SWITCHMF(oo=OoTestCase.aggregate, secid=SecidTestCase.aggregate,
                        unittype="SHARES", switchall=True)


class InvoolistTestCase(unittest.TestCase, base.TestAggregate):
    __test__ = True

    optionalElements = []  # FIXME - how to handle OO subclasses?

    @classproperty
    @classmethod
    def etree(cls):
        root = Element("INVOOLIST")
        for oo in (
            "Oobuydebt",
            "Oobuymf",
            "Oobuyopt",
            "Oobuyother",
            "Oobuystock",
            "Ooselldebt",
            "Oosellmf",
            "Oosellopt",
            "Oosellother",
            "Oosellstock",
            "Switchmf",
        ):
            testCase = "{}TestCase".format(oo)
            elem = globals()[testCase].etree
            root.append(elem)
        return root

    def testListItems(self):
        # INVOOLIST may only contain
        # ['OOBUYDEBT', 'OOBUYMF', 'OOBUYOPT', 'OOBUYOTHER',
        # 'OOBUYSTOCK', 'OOSELLDEBT', 'OOSELLMF', 'OOSELLOPT',
        # 'OOSELLOTHER', 'OOSELLSTOCK', 'SWITCHMF', ]
        listitems = INVOOLIST.listitems
        self.assertEqual(len(listitems), 11)
        root = self.etree
        root.append(StmttrnTestCase.etree)

        with self.assertRaises(ValueError):
            Aggregate.from_etree(root)

    @classproperty
    @classmethod
    def aggregate(cls):
        return INVOOLIST(OobuydebtTestCase.aggregate,
                         OobuymfTestCase.aggregate,
                         OobuyoptTestCase.aggregate,
                         OobuyotherTestCase.aggregate,
                         OobuystockTestCase.aggregate,
                         OoselldebtTestCase.aggregate,
                         OosellmfTestCase.aggregate,
                         OoselloptTestCase.aggregate,
                         OosellotherTestCase.aggregate,
                         OosellstockTestCase.aggregate,
                         SwitchmfTestCase.aggregate)


if __name__ == "__main__":
    unittest.main()
