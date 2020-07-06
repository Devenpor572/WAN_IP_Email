#!/usr/bin/env python3
import configparser
import csv
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
import os
import sys
import smtplib
import ssl
import traceback
import xml.dom.minidom
import xml.etree.ElementTree as ET


# https://stackoverflow.com/a/4943474
def get_script_path():
    return os.path.dirname(os.path.realpath(sys.argv[0]))


PARAMS_PATH = os.path.join(get_script_path(), 'params.cfg')
CONFIG = configparser.ConfigParser()
CONFIG.read(PARAMS_PATH)

logging.basicConfig(filename=CONFIG['params']['log_file'], level=logging.INFO, format='%(asctime)s:%(levelname)s:%(message)s')

DATETIME_FIELD = 'datetime'
IP_FIELD = 'ip'
FIELD_NAMES = [DATETIME_FIELD, IP_FIELD]


def send_email(new_ip):
    message = MIMEMultipart("alternative")
    text = f'WAN IP updated: {new_ip}'
    message.attach(MIMEText(text, "plain"))
    html_el = ET.Element('html')
    body_el = ET.SubElement(html_el, 'body')
    h2_el = ET.SubElement(body_el, 'h2')
    h2_el.text = 'WAN IP updated: '
    link_el = ET.SubElement(h2_el, 'a', {'href': new_ip})
    link_el.text = new_ip
    message.attach(MIMEText(xml.dom.minidom.parseString(ET.tostring(html_el)).toprettyxml(), 'html'))
    message['Subject'] = 'WAN IP Update'
    message['From'] = CONFIG['email']['username']
    recipients = CONFIG['email']['recipients'].split(' ')
    message["To"] = ', '.join(recipients)
    with smtplib.SMTP_SSL(host='smtp.gmail.com', port=465, context=ssl.create_default_context()) as server:
        server.login(CONFIG['email']['username'], CONFIG['email']['password'])
        logging.info(f'Sending message:\n{message.as_string()}')
        server.sendmail(message['From'], recipients, message.as_string())


def check_for_update(new_ip):
    update = False
    file_path = CONFIG['params']['wan_ip_file']
    now = datetime.datetime.now()
    if os.path.exists(file_path):
        with open(file_path, 'r', newline='') as csv_file:
            reader = csv.DictReader(csv_file)
            rows = []
            for row in reader:
                rows.append(row)
        latest_row = rows[-1]
        old_ip = latest_row['ip']
        if new_ip != old_ip:
            logging.info(f'IP updated, New ip: {new_ip}, Old ip: {old_ip}')
            update = True
            with open(file_path, 'a', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=FIELD_NAMES)
                writer.writerow({DATETIME_FIELD: now, IP_FIELD: new_ip})
    else:
        logging.info(f'IP created, New ip: {new_ip}')
        update = True
        with open(file_path, 'w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=FIELD_NAMES)
            writer.writeheader()
            writer.writerow({DATETIME_FIELD: now, IP_FIELD: new_ip})
    return update


if __name__ == '__main__':
    ip = input()
    try:
        if check_for_update(ip):
            send_email(ip)
    except:
        logging.error(traceback.format_exc())
