#!/usr/bin/env python3

import configparser
import requests
import os
import socket
import subprocess
import smtplib
from email.mime.text import MIMEText


def read_config():
    global services
    global msg_cfg
    services = configparser.ConfigParser()
    services.read('monitor.ini')
    msg_cfg = configparser.ConfigParser()
    msg_cfg.read('alert.ini')


def check_status():
    for service in services.sections():
        print ("Testing "+service)
        if services[service]['type'] == 'port':
            status = check_port(services[service]['host'], services[service]['port'])
        elif services[service]['type'] == 'ping':
            status = check_ping(services[service]['host'])
        elif services[service]['type'] == 'url':
            status = check_url(services[service]['url'])
        else:
            pass
        if not status:
            print("        Result: Failed")
            alert(service)
        else:
            print("        Result: Success")


def check_port(host, port):
    print("        Establishing connection: "+host+":"+port)
    s = socket.socket()
    try:
        s.connect((host, int(port)))
    except Exception as e:
        s.close()
        return False
    finally:
        s.close()
    return True


def check_ping(host):
    try:
        subprocess.check_output("ping -c 1 " + host, stderr=subprocess.STDOUT, shell=True)
    except subprocess.CalledProcessError as e:
        return False
    return True


def check_url(url):
    r = requests.get(url)
    return requests.codes.ok


def alert(service):
    message = "Warning: " + service + " not available!"
    if services.has_option(service, 'email'):
        for recipient in services[service]['email'].split(' '):
            send_mail(recipient, message)
    if services.has_option(service, 'sms'):
        for recipient in services[service]['sms'].split(' '):
            send_sms(recipient, message)


def send_sms(recipient, message):
    r = requests.post('https://textbelt.com/text', {
      'phone': recipient,
      'message': message,
      'key': msg_cfg['SMS']['textbelt_key'],
    })
    print(r.content)


def send_mail(recipient, message):
    msg = MIMEText('')
    msg['Subject'] = message
    msg['From'] = msg_cfg['EMAIL']['smtp_user']
    msg['To'] = recipient
    if msg_cfg['EMAIL']['smtp_encryption'] == "tls":
        smtp = smtplib.SMTP_SSL(host=msg_cfg['EMAIL']['smtp_host'], port=msg_cfg['EMAIL']['smtp_port'])
    else:
        smtp = smtplib.SMTP(host=msg_cfg['EMAIL']['smtp_host'], port=msg_cfg['EMAIL']['smtp_port'])
    if msg_cfg['EMAIL']['smtp_encryption'] == 'starttls':
        smtp.starttls()
    if msg_cfg['EMAIL']['smtp_user'] and msg_cfg['EMAIL']['smtp_password']:
        smtp.login(msg_cfg['EMAIL']['smtp_user'], msg_cfg['EMAIL']['smtp_password'])
    smtp.send_message(msg)
    smtp.quit() 


read_config()
check_status()
