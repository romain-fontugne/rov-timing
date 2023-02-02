import argparse
import arrow
import json
import logging
import radix
import random
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support import expected_conditions as EC

from pyvirtualdisplay import Display 

class Bot(object):

    def __init__(self, config_fname="config.json", headless=True):
        """ Initialize crawler with variables from config file"""

        with open(config_fname, 'r') as fp:
            config = json.load(fp)

            logging.basicConfig(filename=config['log']['error'],
                            filemode='a',
                            format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S',
                            level=logging.WARN)

            self.urls = config['urls']

            self.username = config['credentials']['username']
            self.password = config['credentials']['password']
            # To get relevant files from firefox profile see:
            # https://stackoverflow.com/questions/10889085/automating-ssl-client-side-certificates-in-firefox-and-selenium-testing
            self.profile_directory = config['credentials']['firefox_profile']

            self.rtree = radix.Radix()
            for prefix in config['resources']['prefix']:
                self.rtree.add(prefix)

            self.asns = config['resources']['asn']
        # Initialisation of selenium 
        self.browser = None
        self.headless = headless

        self.log = open(config['log']['timing'], 'a')

    def login(self):
        """ Input username/password on the login page.

        Returns True if succesful login."""

        if self.headless:
            display = Display(visible=False, size=(1024, 768)) 
            display.start()

        # Prepared Firefox profile directory
        profile = webdriver.FirefoxProfile(self.profile_directory)

        profile.set_preference("security.default_personal_cert", "Select Automatically")
        profile.set_preference("webdriver_accept_untrusted_certs", True)
        self.browser = webdriver.Firefox(firefox_profile=profile)
        self.browser.implicitly_wait(180)
        self.browser.get(self.urls['login'])
        assert 'Home - Sign In' in self.browser.title

        # login
        self.browser.find_element( By.NAME, 'handle').send_keys( 
                self.username 
                )
        self.browser.find_element(By.NAME, 'user_password').send_keys(
                self.password  + Keys.RETURN 
                )

        # Wait for the 'routes' page to load
        WebDriverWait(self.browser, timeout=60).until(
                EC.presence_of_element_located((By.NAME,'btnSubmit')) )
        WebDriverWait(self.browser, timeout=60).until(
                lambda d: d.execute_script('return document.readyState') == 'complete')

        if self.urls['login'] == self.browser.current_url:
            return True
        else:
            return False


    def create_roa(self, prefix, asn, maxlength, startdate=None, enddate=None):
        """Create a ROA for the given prefix, ASN, and max. prefix length.

        Assumes the bot is already logged in
        """
        assert self.browser is not None
        self.browser.get(self.urls['add'])
        # Wait for the page to load
        WebDriverWait(self.browser, timeout=60).until(
                EC.element_to_be_clickable((By.ID,'addButtonV4')) )
        assert self.urls['add'] in self.browser.current_url

        # check that prefix/asn match the configured resources
        assert str(asn) in self.asns
        rnode = self.rtree.search_best(prefix)
        assert rnode is not None

        # Fill the form
        if startdate == None:
            startdate = arrow.utcnow()
        if enddate == None:
            enddate = startdate.shift(years=1)
        roa_id = prefix+'_AS'+str(asn)+'_'+startdate.format('YYYY-MM-DD')

        WebDriverWait(self.browser, timeout=60).until(
                EC.presence_of_element_located((By.NAME, 'name')) )

        self.browser.find_element(By.NAME, 'name').send_keys(
                roa_id
                )
        self.browser.find_element(By.NAME, 'asnumber').send_keys(
                str(asn)
                )

        menu_id, btn_id, maxlen_id = ( ('ipv4', 'addButtonV4', 'v4maxlength1')
                if '.' in prefix else ('ipv6', 'addButtonV6', 'v6maxlength1') )

        # Select the prefix
        drop_menu = Select(self.browser.find_element(By.ID, menu_id))
        drop_menu.select_by_visible_text(prefix)

        # Add prefix to ROA
        self.browser.find_element(By.ID, btn_id).click()
        self.browser.find_element(By.ID, maxlen_id).send_keys(
                str(maxlength) 
                )


        self.browser.find_element(By.ID, 'not_valid_before').send_keys(
                startdate.format("YYYY-MM-DD")
                )
        self.browser.find_element(By.ID, 'not_valid_after').send_keys(
                enddate.format("YYYY-MM-DD")
                )
        self.browser.find_element(By.ID, 'submit').click()

        WebDriverWait(self.browser, timeout=60).until(
                EC.presence_of_element_located((By.ID,'rpki')) )


        while 'Please be patient' in self.browser.page_source:
            time.sleep(10)

        # Wait for the ROA list page to load 
        WebDriverWait(self.browser, timeout=60).until(
                EC.presence_of_element_located((By.ID,'rpki')) )

        if ( 'List ROAs' in self.browser.page_source 
                and roa_id in self.browser.page_source ):
            now = arrow.utcnow().format()
            self.log.write(f'{now},create,{prefix},{asn},{maxlength}\n')
            return True

        return False


    def delete_roa(self, prefix, asn, startdate=None, roa_id=None):
        """Delete the ROA for the given prefix, ASN.

        Assumes the bot is already logged in
        """
        assert self.browser is not None

        if roa_id is None:
            # Compute daily ROA ID
            if not startdate:
                startdate = arrow.utcnow().format('YYYY-MM-DD')

            roa_id = prefix+'_AS'+str(asn)+'_'+startdate

        url = self.urls['delete'].format(id=roa_id)
        self.browser.get( url )

        # Wait for the page to load
        WebDriverWait(self.browser, timeout=60).until(
                EC.element_to_be_clickable((By.NAME,'submit')) )
        assert url in self.browser.current_url

        # check that prefix/asn match the configured resources
        assert str(asn) in self.asns
        rnode = self.rtree.search_best(prefix)
        assert rnode is not None

        if self.headless:
            # overwrite alerts when running headless
            self.browser.execute_script("window.confirm = function(){return true;}");

        # Click the revoke button
        self.browser.find_element(By.NAME, 'submit').click()

        if not self.headless:
            # Confirm
            self.browser.switch_to.alert.accept()

        # Wait for the ROA list page to load 
        while self.browser.current_url != 'https://my.afrinic.net/resources/rpki/roa/revoke':
            time.sleep(10)

        if 'ROA successfully revoked.' in self.browser.page_source:
            now = arrow.utcnow().format()
            self.log.write(f'{now},delete,{prefix},{asn},0\n')
            return True
        else:
            print(self.browser.page_source)

        return False


    def close(self):
        """End browser session and close log/error files."""

        if self.browser is not None:
            self.browser.quit()
        self.browser = None

        self.log.close()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Automated creation/deletion of ROAs.')
    parser.add_argument('--gui', action='store_false', help='show browser (headless by default)')
    parser.add_argument('--delay_max', default=0, type=int, 
            help='time window to preform the action in minutes (default: 0)')

    # Subcommands
    subcommands = parser.add_subparsers(dest='action', required=True)

    ## Create ROA
    create = subcommands.add_parser('create')
    create.add_argument('prefix', help='prefix for the ROA')
    create.add_argument('asn', help='origin ASN for the ROA (e.g. 2497)')
    create.add_argument('maxPrefixLength', help='Maximum prefix length for the ROA')

    ## Delete ROA
    delete = subcommands.add_parser('delete')
    delete.add_argument('prefix', help='prefix for the ROA')
    delete.add_argument('asn', help='origin ASN for the ROA (e.g. 2497)')
    delete.add_argument('--date', help='date used in the ROA id', default=None)

    args = parser.parse_args()

    # Wait to perform the action
    win_sec = args.delay_max*60
    delay = random.randint(0, win_sec) 
    time.sleep(delay)

    bot = Bot(headless=args.gui)

    try:
        if bot.login():
            success = False
            if args.action == 'create':
                success = bot.create_roa(args.prefix, args.asn, args.maxPrefixLength)
            elif args.action == 'delete':
                success = bot.delete_roa(args.prefix, args.asn, startdate=args.date)

            if not success:
                raise Exception(f'Failed to {args.action} ROA!')
        else:
            raise Exception('Failed login!')

    # Log any error that could happen
    except Exception as e:
        logging.error('Error', exc_info=e)

    finally:
        bot.close()
