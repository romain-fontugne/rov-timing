import argparse
import arrow
import json
import logging
import pyotp
import radix
import random
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
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

            self.url = config['url']

            self.username = config['credentials']['username']
            self.password = config['credentials']['password']
            self.totp_secret = config['credentials']['totp_secret']

            self.rtree = radix.Radix()
            for prefix in config['resources']['prefix']:
                self.rtree.add(prefix)

            self.asns = config['resources']['asn']
        # Initialisation of selenium and TOTP
        self.totp = pyotp.TOTP(self.totp_secret)
        self.browser = None
        self.headless = headless

        self.log = open(config['log']['timing'], 'a')

    def login(self):
        """ Input username/password on the login page and complete 2fa.

        Returns True if succesful login."""

        if self.headless:
            display = Display(visible=False, size=(1024, 768)) 
            display.start()

        self.browser = webdriver.Firefox()
        self.browser.implicitly_wait(60)
        self.browser.get(self.url)
        assert 'APNIC-login' in self.browser.title

        # login
        self.browser.find_element( By.NAME, 'username').send_keys( 
                self.username + Keys.RETURN 
                )

        WebDriverWait(self.browser, timeout=60).until(
                EC.presence_of_element_located((By.NAME,'password')) )

        self.browser.find_element(By.NAME, 'password').send_keys(
                self.password  + Keys.RETURN 
                )

        # Wait for 2FA prompt
        WebDriverWait(self.browser, timeout=60).until(
                EC.presence_of_element_located((By.NAME,'answer')) )

        # two-factor-authentication
        elem =  self.browser.find_element(By.NAME, 'answer')
        pwd = self.totp.now()
        elem.send_keys(pwd + Keys.RETURN )

        # Wait for the 'routes' page to load
        WebDriverWait(self.browser, timeout=60).until(
                EC.presence_of_element_located((By.ID,'create-route-btn')) )
        WebDriverWait(self.browser, timeout=60).until(
                lambda d: d.execute_script('return document.readyState') == 'complete')

        if self.url == self.browser.current_url:
            return True
        else:
            return False


    def create_roa(self, prefix, asn, maxlength, create_irr=False):
        """Create a ROA for the given prefix, ASN, and max. prefix length.

        Assumes the bot is already logged in
        """
        assert self.browser is not None
        assert self.url in self.browser.current_url

        # check that prefix/asn match the configured resources
        assert str(asn) in self.asns
        rnode = self.rtree.search_best(prefix)
        assert rnode is not None

        self.browser.find_element(By.ID, 'create-route-btn').click()

        # Fill the form
        WebDriverWait(self.browser, timeout=60).until(
                EC.presence_of_element_located((By.ID, 'create-route-prefix-input')) )

        self.browser.find_element(By.ID, 'create-route-prefix-input').send_keys(
                prefix
                )
        self.browser.find_element(By.ID, 'create-route-origin-input').send_keys(
                str(asn)
                )
        self.browser.find_element(By.ID, 'create-route-msa-input').send_keys(
                str(maxlength) 
                )
        # uncheck whois option if needed
        if not create_irr:
            self.browser.find_element(By.ID, 'whois-checkbox').click()

        self.browser.find_element(By.ID, 'create-route-next-btn').click()

        WebDriverWait(self.browser, timeout=60).until(
                EC.presence_of_element_located((By.ID,'confirm-route-submit-btn')) )
        self.browser.find_element(By.ID, 'confirm-route-submit-btn').click()

        now = arrow.utcnow().format()
        self.log.write(f'{now},create,{prefix},{asn},{maxlength}\n')

        return True


    def delete_roa(self, prefix, asn):
        """Delete the ROA for the given prefix, ASN.

        Assumes the bot is already logged in
        """
        assert self.browser is not None
        assert self.url in self.browser.current_url

        # check that prefix/asn match the configured resources
        assert str(asn) in self.asns
        rnode = self.rtree.search_best(prefix)
        assert rnode is not None

        table = self.browser.find_element(By.ID, 'prefixTable')
        for row in table.find_elements_by_tag_name('tr'):
            values = []
            for cell in row.find_elements_by_tag_name('td'):
                values.append(cell.text)

            
            # Delete if prefix and asn match the given arguments
            if len(values)>2 and values[1] == prefix and values[2] == 'AS'+str(asn):
                id = row.get_attribute('id')
                prefix = values[1]
                asn = values[2]

                # delete ROA
                self.browser.execute_script(f'routes.deleteIndividualRoute("{prefix} - {asn}", {id})')
                # confirm
                WebDriverWait(self.browser, timeout=60).until(
                    EC.visibility_of_element_located((By.ID, 'individual-deletion-yes-btn')) )
                self.browser.find_element(By.ID, 'individual-deletion-yes-btn').click()

                now = arrow.utcnow().format()
                self.log.write(f'{now},delete,{prefix},{asn},0\n')

                return True

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

    ## Print 2FA token
    token = subcommands.add_parser('token')
    
    ## Create ROA
    create = subcommands.add_parser('create')
    create.add_argument('prefix', help='prefix for the ROA')
    create.add_argument('asn', help='origin ASN for the ROA (e.g. 2497)')
    create.add_argument('maxPrefixLength', help='Maximum prefix length for the ROA')

    ## Delete ROA
    delete = subcommands.add_parser('delete')
    delete.add_argument('prefix', help='prefix for the ROA')
    delete.add_argument('asn', help='origin ASN for the ROA (e.g. 2497)')

    args = parser.parse_args()

    try:
        # Wait to perform the action
        win_sec = args.delay_max*60
        delay = random.randint(0, win_sec) 
        time.sleep(delay)

        bot = Bot(headless=args.gui)


        if args.action == 'token':
            print(bot.totp.now())
        elif bot.login():
            success = False
            if args.action == 'create':
                success = bot.create_roa(args.prefix, args.asn, args.maxPrefixLength)
            elif args.action == 'delete':
                success = bot.delete_roa(args.prefix, args.asn)

            # Wait a bit to make sure things are done
            time.sleep(30)

            if not success:
                raise Exception(f'Failed to {args.action} ROA!')
        else:
            raise Exception('Failed login!')

        bot.close()

    # Log any error that could happen
    except Exception as e:
        logging.error('Error', exc_info=e)
