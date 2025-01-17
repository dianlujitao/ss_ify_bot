#!/usr/bin/ python3
# -*- coding:utf-8 -*-
import base64
import json
import os
import re
import telebot
import requests

bot = telebot.TeleBot("")

def to_bytes(s):
    if bytes != str:
        if type(s) == str:
            return s.encode('utf-8')
    return s


def to_str(s):
    if bytes != str:
        if type(s) == bytes:
            return s.decode('utf-8')
    return s


def b64decode(data):
    if b':' in data:
        return data
    if len(data) % 4 == 2:
        data += b'=='
    elif len(data) % 4 == 3:
        data += b'='
    return base64.urlsafe_b64decode(data)


def decode_ssr_subscription(ssr_subscription):
    ssr_subscription = to_bytes(ssr_subscription)
    ssr_profiles = to_str(b64decode(ssr_subscription))
    return ssr_profiles.split()


def decode_ssr_profile(ssr_profile):
    if ssr_profile[:6] != 'ssr://':
        raise ValueError('Invalid SSR profile URI!')

    ssr_profile = to_bytes(ssr_profile[6:])
    ssr_profile = to_str(b64decode(ssr_profile))

    ssr_profile_params = {}

    if '/' in ssr_profile:
        ssr_profile, extra_params = ssr_profile.split('/', 1)

        delimiter_pos = extra_params.find('?')
        if delimiter_pos >= 0:
            extra_params = extra_params[delimiter_pos + 1:]

        extra_params = extra_params.split('&')
        for param in extra_params:
            k, v = param.split('=', 1)

            if k in ['obfsparam', 'protoparam', 'group', 'remarks']:
                v = to_str(b64decode(to_bytes(v)))

            key_mapping = {'obfsparam': 'obfs_param',
                           'protoparam': 'protocol_param'}
            k = key_mapping.get(k, k)

            ssr_profile_params[k] = v

    ssr_profile = ssr_profile.split(':')
    if len(ssr_profile) != 6:
        raise ValueError('Invalid SSR profile configuration!')

    ssr_profile_params.update({
        'server': ssr_profile[0],
        'server_port': int(ssr_profile[1]),
        'protocol': ssr_profile[2],
        'method': ssr_profile[3],
        'obfs': ssr_profile[4],
        'password': to_str(b64decode(to_bytes(ssr_profile[5]))),
        'local_address': '127.0.0.1',
        'local_port': 1080
    })

    return ssr_profile_params


def to_ss_qt5(ssr_profile_params):
    if ssr_profile_params['protocol'] != 'origin':
        return None

    ss_conf_key = ['method', 'password', 'remarks', 'server', 'server_port']
    return dict((k, ssr_profile_params[k]) for k in ss_conf_key if k in ssr_profile_params)


def ss_ify_decode(ssr_subscription):
    ssr_profiles = decode_ssr_subscription(ssr_subscription)
    ss_qt5_params = {
        'configs': [],
        'localPort': 1080,
        'shareOverLan': False
    }
    for ssr_profile in ssr_profiles:
        ssr_profile_params = decode_ssr_profile(ssr_profile)
        ss_profile_params = to_ss_qt5(ssr_profile_params)
        if ss_profile_params is not None:
            ss_qt5_params['configs'].append(ss_profile_params)
    with open('gui-config.json', 'w') as f:
        json.dump(ss_qt5_params, f, indent=4,
                  sort_keys=True, ensure_ascii=False)

@bot.message_handler(func=lambda message: True)
def send_request(message):
    ssr_sub_url = message.text
    if ssr_sub_url[0:7] == 'http://' or ssr_sub_url[0:8] == 'https://':
        bot.send_message(message.chat.id, "Requesting...")
        url_information = requests.get(ssr_sub_url).text
        bot.edit_message_text("Decoding...", message.chat.id, message.message_id + 1)
        ss_ify_decode(url_information)
        doc = open('gui-config.json', 'rb')
        bot.edit_message_text("Sending file...", message.chat.id, message.message_id + 1)
        bot.send_document(message.chat.id, doc)
        os.system('rm -f gui-config.json')
    else:
        bot.send_message(message.chat.id, "Bad Request...")

bot.polling(none_stop=True)