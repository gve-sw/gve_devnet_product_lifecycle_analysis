# !/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Copyright (c) 2022 Cisco and/or its affiliates.
This software is licensed to you under the terms of the Cisco Sample
Code License, Version 1.1 (the "License"). You may obtain a copy of the
License at
               https://developer.cisco.com/docs/licenses
All use of the material herein must be in accordance with the terms of
the License. All rights not expressly granted by the License are
reserved. Unless required by applicable law or agreed to separately in
writing, software distributed under the License is distributed on an "AS
IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
or implied.
"""

__author__ = "Simon Fang <sifang@cisco.com>"
__copyright__ = "Copyright (c) 2022 Cisco and/or its affiliates."
__license__ = "Cisco Sample Code License, Version 1.1"

# Import Section
from flask import Flask, render_template, request, make_response
from dotenv import load_dotenv
import requests
from werkzeug.utils import secure_filename
import csv
import os
import json
import pandas as pd
import datetime

# Load environment variables
load_dotenv()

# Global variables
app = Flask(__name__)
SUPPORT_API_BASE_URL = "https://api.cisco.com"
SUPPORT_API_ACCESS_TOKEN = ""
product_infos = []

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

# Methods

def get_serial_numbers_from_csv(filename):
    serial_numbers = []
    print('*** now going to read csv file ***')

    # try to read csv file, if not, read an excel file and convert it to csv
    with open(filename, 'r') as csv_file:
        csv_reader = csv.reader(csv_file)
        for row_number, row in enumerate(csv_reader):
            if row_number == 0:
                print("*** do not record this row - Headers ***")
                continue
            serial_number = row[0]
            serial_numbers.append(serial_number)
    return serial_numbers

def get_product_info_by_serial_number(serial_number):
    url = f"{SUPPORT_API_BASE_URL}/product/v1/information/serial_numbers/{serial_number}"
    headers= {
        "Accept": "application/json",
        "Authorization": f"Bearer {SUPPORT_API_ACCESS_TOKEN}"
    }
    response = requests.get(url, headers=headers)
    # print(json.dumps(response.json(), indent=2))
    return response.json()

def get_eox_by_serial_number(serial_number):
    url = f"{SUPPORT_API_BASE_URL}/supporttools/eox/rest/5/EOXBySerialNumber/1/{serial_number}?responseencoding=json"
    headers= {
        "Accept": "application/json",
        "Authorization": f"Bearer {SUPPORT_API_ACCESS_TOKEN}"
    }
    response = requests.get(url, headers=headers)
    # print(json.dumps(response.json(), indent=2))
    return response.json()


def get_csv_from_product_infos(product_infos):
    df = pd.DataFrame(product_infos)
    columns_order = ['serial_number', 'product_name', 'product_id', 'release_date', 'EOXExternalAnnouncementDate', 
    'EndOfSaleDate', 'EndOfSWMaintenanceReleases', 'EndOfSecurityVulSupportDate', 'EndOfRoutineFailureAnalysisDate', 'EndOfServiceContractRenewal', 'LastDateOfSupport', 'EndOfSvcAttachDate']
    df = df[columns_order]
    df.columns = ['Serial Number', 'Product Name', 'Product ID', 'Release Date', 'EoX External Announcement Date', 
    'End of Sales Date', 'End of SW Maintenance Release', 'EndOfSecurityVulSupportDate','End of Routine Failure Analysis Date', 'End of Service Contract Renewal',
    'Last Date of Support', 'End of Svc Attach Date']
    csv = df.to_csv(index=False)
    return csv

# Routes

## Main page
@app.route('/')
def main():
    return render_template('login.html')

## Login
@app.route('/login', methods=['POST'])
def login():
    global SUPPORT_API_ACCESS_TOKEN

    url = "https://cloudsso.cisco.com/as/token.oauth2"
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
    }
    body = {
        'grant_type': 'client_credentials',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }

    response = requests.post(url, data=body, headers=headers)
    SUPPORT_API_ACCESS_TOKEN = response.json()['access_token']
    print(SUPPORT_API_ACCESS_TOKEN)

    return render_template('upload_page.html')

@app.route('/uploader', methods=['POST'])
def upload_file():
    global product_infos
    if request.method == 'POST':
        f = request.files['file']
        filename = f.filename
        f.save(secure_filename(f.filename))
        serial_numbers = get_serial_numbers_from_csv(filename)
        
        for serial_number in serial_numbers:
            product_info_response = get_product_info_by_serial_number(serial_number)
            eox_info = get_eox_by_serial_number(serial_number)
            product_info = {}
            product_info['serial_number'] = product_info_response['product_list'][0]['sr_no']
            product_info['product_name'] = product_info_response['product_list'][0]['product_name']
            product_info['product_id'] = product_info_response['product_list'][0]['orderable_pid']
            product_info['release_date'] = product_info_response['product_list'][0]['release_date']
            product_info['EOXExternalAnnouncementDate'] = eox_info['EOXRecord'][0]['EOXExternalAnnouncementDate']['value']
            product_info['EndOfSaleDate'] = eox_info['EOXRecord'][0]['EndOfSaleDate']['value']
            product_info['EndOfSWMaintenanceReleases'] = eox_info['EOXRecord'][0]['EndOfSWMaintenanceReleases']['value']
            if 'EndOfSecurityVulSupportDate' in eox_info['EOXRecord'][0]:
                product_info['EndOfSecurityVulSupportDate'] = eox_info['EOXRecord'][0]['EndOfSecurityVulSupportDate']['value']
            product_info['EndOfRoutineFailureAnalysisDate'] = eox_info['EOXRecord'][0]['EndOfRoutineFailureAnalysisDate']['value']
            product_info['EndOfServiceContractRenewal'] = eox_info['EOXRecord'][0]['EndOfServiceContractRenewal']['value']
            product_info['LastDateOfSupport'] = eox_info['EOXRecord'][0]['LastDateOfSupport']['value']
            product_info['EndOfSvcAttachDate'] = eox_info['EOXRecord'][0]['EndOfSvcAttachDate']['value']
            product_infos.append(product_info)

        return render_template('product_info.html', product_infos=product_infos)

@app.route('/download_csv', methods=['POST'])
def download_csv():
    form_data = request.form
    # User clicked button to download csv
    form_data['download_button']

    # convert json to csv
    csv = get_csv_from_product_infos(product_infos)

    response = make_response(csv)

    filename = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M')}_product_info.csv"

    response.headers.set("Content-Disposition", "attachment", filename=filename)

    return response

# Run app
if __name__ == "__main__":
    app.run(host='127.0.0.1', debug=True)
