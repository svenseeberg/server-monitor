#!/usr/bin/env python3

import requests # non-native dependency
import configparser
import os
import socket
import subprocess
import smtplib
import json
from email.mime.text import MIMEText

failed_file = "/tmp/server-monitor-failed"
failed = []
notify_cycles = 1


def read_config():
    global services
    global msg_cfg
    services = configparser.ConfigParser()
    services.read('monitor.ini')
    msg_cfg = configparser.ConfigParser()
    msg_cfg.read('alert.ini')


def read_failed():
    global prev_failed
    prev_failed = {}
    if os.path.isfile(failed_file):
        with open(failed_file) as f:
            lines = f.read().splitlines()
            for line in lines:
                line = line.split(',')
                prev_failed[line[0]] = {'cycles': line[1]}
    else:
        prev_failed = {}

def write_failed():
    with open(failed_file, "w") as f:
        for line in failed:
            if line in prev_failed:
                f.write(line+','+str(int(prev_failed[line]['cycles'])+1))
            else:
                f.write(line + ',1')
            f.write("\n")


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
    print("        Pinging: "+host)
    try:
        subprocess.check_output("ping -c 1 " + host, stderr=subprocess.STDOUT, shell=True)
    except subprocess.CalledProcessError as e:
        return False
    return True


def check_url(url):
    print("        Downloading: "+url)
    r = requests.get(url)
    return requests.codes.ok


def alert(service):
    failed.append(service)
    if not service in prev_failed or not int(prev_failed[service]['cycles'])+1 == int(services[service]['cycles']):
        return
    message = "Warning: " + service + " not available!"
    if services.has_option(service, 'email'):
        for recipient in services[service]['email'].split(' '):
            send_mail(recipient, message)
    if services.has_option(service, 'sms'):
        for recipient in services[service]['sms'].split(' '):
            send_sms(recipient, message)
    if services.has_option(service, 'slack'):
        for recipient in services[service]['slack'].split(' '):
            send_slack(recipient, message)

def send_sms(recipient, message):
    r = requests.post('https://textbelt.com/text', {
      'phone': recipient,
      'message': message,
      'key': msg_cfg['SMS']['textbelt_key'],
    })
    result = json.loads(r.content.decode('utf-8'))
    if result['success'] == True:
        print("        Notified: "+recipient)
        return True
    else:
        return False


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
    result = smtp.quit()
    if result[0] == 221:
        print("        Notified: "+recipient)
        return True
    else:
        return False


def send_slack(recipient, message):
    r = requests.post('https://hooks.slack.com/services/T00000000/B00000000/'+recipient, {
      'text': message,
    })
    result = json.loads(r.content.decode('utf-8'))
    if result['success'] == True:
        print("        Notified: Slack token "+recipient)
        return True
    else:
        return False


def main():
    read_config()
    read_failed()
    check_status()
    write_failed()


main()
