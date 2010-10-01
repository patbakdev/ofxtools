#!/usr/bin/env python
import datetime
import uuid
from xml.etree.cElementTree import Element, SubElement, tostring
import urllib2
import os
import ConfigParser
from cStringIO import StringIO

import valid
from parser import OFXParser
from utilities import _, parse_accts, acct_re

dtconverter = valid.OFXDtConverter()
stringbool = valid.OFXStringBool()
accttypeValidator = valid.validators.OneOf(valid.ACCOUNT_TYPES)

APP_DEFAULTS = {'version': '102', 'appid': 'QWIN', 'appver': '1800',}
FI_DEFAULTS = {'url': '', 'org': '', 'fid': '', 'bankid': '', 'brokerid': '',}
ACCT_DEFAULTS = {'checking': '', 'savings': '', 'moneymrkt': '',
                'creditline': '', 'creditcard': '', 'investment': '',}
STMT_DEFAULTS = {'inctran': True, 'dtstart': None, 'dtend': None,
                'incpos': True, 'dtasof': None, 'incbal': True, }
UI_DEFAULTS = {'list': False, 'dry_run': False, 'from_config': None,
                'archive': True, 'dir': None,}


class OFXClient(object):
    """ """
    defaults = APP_DEFAULTS.copy()
    defaults.update(FI_DEFAULTS)
    defaults.update(STMT_DEFAULTS)

    def __init__(self, **kwargs):
        for (name, value) in self.defaults.iteritems():
            setattr(self, name, kwargs.get(name, value))
        # Initialize
        self.reset()

    def reset(self):
        self.signon = None
        self.bank = None
        self.creditcard = None
        self.investment = None
        self.request = None
        self.response = None

    def download(self, user=None, password=None):
        mime = 'application/x-ofx'
        headers = {'Content-type': mime, 'Accept': '*/*, %s' % mime}
        if not self.request:
            self.write_request(user, password)
        http = urllib2.Request(self.url, self.request, headers)
        try:
            self.response = response = urllib2.urlopen(http)
        except urllib2.HTTPError as err:
            # FIXME
            print err.info()
            raise
        # urllib2.urlopen returns an addinfourl instance, which supports
        # a limited subset of file methods.  Copy response to a StringIO
        # so that we can use tell() and seek().
        source = StringIO()
        source.write(response.read())
        # After writing, rewind to the beginning.
        source.seek(0)
        return source

    def write_request(self, user=None, password=None):
        ofx = Element('OFX')
        if not self.signon:
            self.request_signon(user, password)
        ofx.append(self.signon)
        for msgset in ('bank', 'creditcard', 'investment'):
            msgset = getattr(self, msgset, None)
            if msgset:
                ofx.append(msgset)
        self.request = request = self.header + tostring(ofx)
        return request

    @property
    def header(self):
        """ OFX header; prepend to OFX markup. """
        version = (int(self.version)/100)*100 # Int division drops remainder
        if version == 100:
            # Flat text header
            fields = (  ('OFXHEADER', str(version)),
                        ('DATA', 'OFXSGML'),
                        ('VERSION', str(self.version)),
                        ('SECURITY', 'NONE'),
                        ('ENCODING', 'USASCII'),
                        ('CHARSET', '1252'),
                        ('COMPRESSION', 'NONE'),
                        ('OLDFILEUID', 'NONE'),
                        ('NEWFILEUID', str(uuid.uuid4())),
            )
            lines = [':'.join(field) for field in fields]
            lines = '\r\n'.join(lines)
            lines += '\r\n'*2
            return lines
        elif version == 200:
            # XML header
            xml_decl = '<?xml version="1.0" encoding="UTF-8" standalone="no"?>'
            fields = (  ('OFXHEADER', str(version)),
                        ('VERSION', str(self.version)),
                        ('SECURITY', 'NONE'),
                        ('OLDFILEUID', 'NONE'),
                        ('NEWFILEUID', str(uuid.uuid4())),
            )
            attrs = ['='.join(attr, '"%s"' %val) for attr,val in fields]
            ofx_decl = '<?OFX %s?>' % ' '.join(attrs)
            return '\r\n'.join((xml_decl, ofx_decl))
        else:
            # FIXME
            raise ValueError

    def request_signon(self, user, password):
        if not (user and password):
            # FIXME
            raise ValueError
        msgsrq = Element('SIGNONMSGSRQV1')
        sonrq = SubElement(msgsrq, 'SONRQ')
        SubElement(sonrq, 'DTCLIENT').text = dtconverter.from_python(datetime.datetime.now())
        SubElement(sonrq, 'USERID').text = user
        SubElement(sonrq, 'USERPASS').text = password
        SubElement(sonrq, 'LANGUAGE').text = 'ENG'
        if self.org:
            fi = SubElement(sonrq, 'FI')
            SubElement(fi, 'ORG').text = self.org
            if self.fid:
                SubElement(fi, 'FID').text = self.fid
        SubElement(sonrq, 'APPID').text = self.appid
        SubElement(sonrq, 'APPVER').text = self.appver
        self.signon = msgsrq

    def request_bank(self, accounts, **kwargs):
        """
        Requesting transactions without dtstart/dtend (which is the default)
        asks for all transactions on record.
        """
        if not accounts:
            # FIXME
            raise ValueError('No bank accounts requested')

        msgsrq = Element('BANKMSGSRQV1')
        for account in accounts:
            try:
                accttype, bankid, acctid = account
                accttype = accttypeValidator.to_python(accttype)
            except ValueError:
                # FIXME
                raise ValueError("Bank accounts must be specified as a sequence of (ACCTTYPE, BANKID, ACCTID) tuples, not '%s'" % str(accounts))
            stmtrq = self.wrap_request(msgsrq, 'STMTRQ')
            acctfrom = SubElement(stmtrq, 'BANKACCTFROM')
            SubElement(acctfrom, 'BANKID').text = bankid
            SubElement(acctfrom, 'ACCTID').text = acctid
            SubElement(acctfrom, 'ACCTTYPE').text = accttype

            self.include_transactions(stmtrq, **kwargs)
        self.bank = msgsrq

    def request_creditcard(self, accounts, **kwargs):
        """
        Requesting transactions without dtstart/dtend (which is the default)
        asks for all transactions on record.
        """
        if not accounts:
            # FIXME
            raise ValueError('No credit card accounts requested')

        msgsrq = Element('CREDITCARDMSGSRQV1')
        for account in accounts:
            stmtrq = self.wrap_request(msgsrq, 'CCSTMTRQ')
            acctfrom = SubElement(stmtrq, 'CCACCTFROM')
            SubElement(acctfrom, 'ACCTID').text = account

            self.include_transactions(stmtrq, **kwargs)
        self.creditcard = msgsrq

    def request_investment(self, accounts, **kwargs):
        """ """
        if not accounts:
            # FIXME
            raise ValueError('No investment accounts requested')

        incpos = kwargs.get('incpos', self.defaults['incpos'])
        dtasof = dtconverter.to_python(kwargs.get('dtasof', self.defaults['dtasof']))
        incbal = kwargs.get('incbal', self.defaults['incbal'])

        msgsrq = Element('INVSTMTMSGSRQV1')
        for account in accounts:
            try:
                brokerid, acctid = account
            except ValueError:
                raise ValueError("Investment accounts must be specified as a sequence of (BROKERID, ACCTID) tuples, not '%s'" % str(accounts))
            stmtrq = self.wrap_request(msgsrq, 'INVSTMTRQ')
            acctfrom = SubElement(stmtrq, 'INVACCTFROM')
            SubElement(acctfrom, 'BROKERID').text = brokerid
            SubElement(acctfrom, 'ACCTID').text = acctid

            self.include_transactions(stmtrq, **kwargs)

            SubElement(stmtrq, 'INCOO').text = 'N'

            pos = SubElement(stmtrq, 'INCPOS')
            if dtasof:
                SubElement(pos, 'DTASOF').text = dtconverter.from_python(dtasof)
            SubElement(pos, 'INCLUDE').text = stringbool.from_python(incpos)

            SubElement(stmtrq, 'INCBAL').text = stringbool.from_python(incbal)
        self.investment = msgsrq

    # Utilities
    def wrap_request(self, parent, tag):
        """ """
        assert 'TRNRQ' not in tag
        assert tag[-2:] == 'RQ'
        trnrq = SubElement(parent, tag.replace('RQ', 'TRNRQ'))
        SubElement(trnrq, 'TRNUID').text = str(uuid.uuid4())
        return SubElement(trnrq, tag)

    def include_transactions(self, parent, **kwargs):
        include = kwargs.get('inctran', self.defaults['inctran'])
        dtstart = dtconverter.to_python(kwargs.get('dtstart', self.defaults['dtstart']))
        dtend = dtconverter.to_python(kwargs.get('dtend', self.defaults['dtend']))

        inctran = SubElement(parent, 'INCTRAN')
        if dtstart:
            SubElement(inctran, 'DTSTART').text = dtconverter.from_python(dtstart)
        if dtend:
            SubElement(inctran, 'DTEND').text = dtconverter.from_python(dtend)
        SubElement(inctran, 'INCLUDE').text = stringbool.from_python(include)
        return inctran


def init_optionparser():
    from optparse import OptionParser, OptionGroup

    usage = "usage: %prog [options] institution"
    optparser = OptionParser(usage=usage)
    defaults = UI_DEFAULTS.copy()
    defaults.update(STMT_DEFAULTS)
    defaults.update(ACCT_DEFAULTS)
    defaults['user'] = ''
    optparser.set_defaults(**defaults)
    optparser.add_option('-l', '--list', action='store_true',
                        help='list known institutions and exit')
    optparser.add_option('-n', '--dry-run', action='store_true',
                        help='display OFX request and exit')
    optparser.add_option('-f', '--from-config', metavar='FILE', help='use alternate config file')
    optparser.add_option('-a', '--no-archive', dest='archive', action='store_false',
                        help="don't archive OFX downloads to file")
    optparser.add_option('-o', '--dir', metavar='DIR', help='archive OFX downloads in DIR')
    optparser.add_option('-u', '--user', help='login user ID at institution')
    # Bank accounts
    bankgroup = OptionGroup(optparser, 'Bank accounts are specified as pairs of (routing#, acct#)')
    bankgroup.add_option('-C', '--checking', metavar='(LIST OF ACCOUNTS)')
    bankgroup.add_option('-S', '--savings', metavar='(LIST OF ACCOUNTS)')
    bankgroup.add_option('-M', '--moneymrkt', metavar='(LIST OF ACCOUNTS)')
    bankgroup.add_option('-L', '--creditline', metavar='(LIST OF ACCOUNTS)')
    optparser.add_option_group(bankgroup)

    # Credit card accounts
    ccgroup = OptionGroup(optparser, 'Credit cards are specified by an acct#')
    ccgroup.add_option('-c', '--creditcard', metavar='(LIST OF ACCOUNTS)')
    optparser.add_option_group(ccgroup)

    # Investment accounts
    invgroup = OptionGroup(optparser, 'Investment accounts are specified as pairs of (brokerid, acct#)')
    invgroup.add_option('-i', '--investment', metavar='(LIST OF ACCOUNTS)')
    optparser.add_option_group(invgroup)

    # Statement options
    stmtgroup = OptionGroup(optparser, 'Statement Options')
    stmtgroup.add_option('-t', '--no-transactions', dest='inctran',
                        action='store_false')
    stmtgroup.add_option('-s', '--start', dest='dtstart', help='Start date/time for transactions')
    stmtgroup.add_option('-e', '--end', dest='dtend', help='End date/time for transactions')
    stmtgroup.add_option('-p', '--no-positions', dest='incpos',
                        action='store_false')
    stmtgroup.add_option('-d', '--date', dest='dtasof', help='As-of date for investment positions')
    stmtgroup.add_option('-b', '--no-balances', dest='incbal',
                        action='store_false')
    optparser.add_option_group(stmtgroup)

    return optparser


class OFXConfigParser(ConfigParser.SafeConfigParser):
    """ """
    main_config = _(os.path.join(os.path.dirname(__file__), 'main.cfg'))

    defaults = APP_DEFAULTS.copy()
    defaults.update(FI_DEFAULTS)
    defaults['user'] = ''
    defaults.update(ACCT_DEFAULTS)


    def __init__(self):
        ConfigParser.SafeConfigParser.__init__(self, self.defaults)

    def read(self, filenames=None):
        # Load main config
        self.readfp(open(self.main_config))
        # Then load user configs (defaults to main.cfg [global] config: value)
        filenames = filenames or _(self.get('global', 'config'))
        return ConfigParser.SafeConfigParser.read(self, filenames)

    @property
    def fi_index(self):
        sections = self.sections()
        sections.remove('global')
        return sections


def main():
    ### PARSE COMMAND LINE OPTIONS
    from getpass import getpass

    optparser = init_optionparser()
    (options, args) = optparser.parse_args()

    ### PARSE CONFIG
    config = OFXConfigParser()
    config.read(options.from_config)

    # If we're just listing known FIs, then bail out here.
    if options.list:
        print config.fi_index
        return

    if len(args) != 1:
        optparser.print_usage()
        return
    fi = args[0]

    ### DEMUX UI INPUT
    options = options.__dict__

    # Meta options for controlling the UI itself.
    ui_opts = dict([(option,options.pop(option)) for option in UI_DEFAULTS.keys()])

    # Options which can be controlled by either UI or config file.
    # Defaults are empty strings i.e. no input; fall back to config.
    acct_opts = dict([(option, options.pop(option) or config.get(fi, option)) \
                for option in ACCT_DEFAULTS.keys() + ['user',]])

    # Remaining optparse options should be statement options, which are only
    # controlled via UI.
    stmt_opts = dict([(option, options.pop(option)) for option in STMT_DEFAULTS.keys()])
    if options != {}:
        # FIXME
        print options
        raise ValueError

    ### INSTANTIATE CLIENT
    # Client instance attributes are controlled only via config file.
    client_opts = dict([(option, config.get(fi, option)) for option in APP_DEFAULTS.keys() + FI_DEFAULTS.keys()])
    client = OFXClient(**client_opts)

    ### CONSTRUCT OFX REQUEST
    # Parse account strings
    bankid = client.bankid
    brokerid = client.brokerid

    bank_accts = []
    for accttype in ('checking', 'savings', 'moneymrkt', 'creditline'):
        accts  = parse_accts(acct_opts[accttype])
        bank_accts += [(accttype.upper(), acct[0] or bankid, acct[1])
                        for acct in accts]

    cc_accts = acct_re.findall(acct_opts['creditcard'])
    inv_accts = [(brokerid, acct)
                    for acct in acct_re.findall(acct_opts['investment'])]

    # Create STMTRQ aggregates
    if bank_accts:
        client.request_bank(bank_accts, **stmt_opts)
    if cc_accts:
        client.request_creditcard(cc_accts, **stmt_opts)
    if inv_accts:
        client.request_investment(inv_accts, **stmt_opts)

    ### HANDLE REQUEST
    if ui_opts['dry_run']:
        print client.write_request(acct_opts['user'], 'TOPSECRETPASSWORD')
        return

    password = getpass()
    response = client.download(user=acct_opts['user'], password=password)

    if ui_opts['archive']:
        # Parse response to check for errors before saving to archive.
        ofxparser = OFXParser()
        errors = ofxparser.parse(response)
        # Rewind source again after parsing
        response.seek(0)
        if errors:
            # FIXME
            print response.read()
            raise ValueError("OFX download errors: '%s'" % str(errors))

        # Archive to disk
        archive_dir = _(ui_opts['dir'] or os.path.join(config.get('global', 'dir'), fi))
        timestamp = ofxparser.signon.dtserver.strftime('%Y%m%d%H%M%S')
        if not os.path.exists(archive_dir):
            os.makedirs(archive_dir)
        archive_path = os.path.join(archive_dir, '%s.ofx' % timestamp)
        with open(archive_path, 'w') as archive:
            archive.write(response.read())
    else:
        print response.read()


if __name__ == '__main__':
    main()