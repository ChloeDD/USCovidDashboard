import datetime
import glog
import numpy as np
import os
import pandas as pd
import pdb
from sodapy import Socrata

usStateDataLink = "9mfq-cb36"
usDeathDataLink = '9bhg-hcku'
caseSurveillanceData = 'vbim-akqf'

us_state_data_query = "SELECT * WHERE submission_date="
case_surveillance_query = "SELECT * WHERE cdc_report_dt="


def download_file(date, filesource, dataquery, filename_prefix, folder):
    """Download data from CDC website"""

    client = Socrata("data.cdc.gov", None)
    results = client.get(filesource, query=dataquery)
    results_df = pd.DataFrame.from_records(results)
    filename = './{}/{}-{}.csv'.format(folder, filename_prefix, date)
    results_df.to_csv(filename)


def process_population_data(input_file):
    """function to convert wikipedia us population data"""

    df = pd.read_html(input_file)
    newdf = df[0][['State', 'Population estimate, July 1, 2019[2]']]
    newdf.columns = ['State', 'Population']
    code = pd.read_csv('StateCode.csv')
    merge = pd.merge(left=newdf, right=code, left_on='State', right_on='Name', how='outer')
    merge.loc[merge['State'] == 'U.S. Virgin Islands', 'State or Region Code'] = 'VI'
    merge.loc[merge['State'] == 'District of Columbia', 'State or Region Code'] = 'DC'
    merge.loc[merge['State'] ==
              'Total U.S. (including D.C. and territories)', 'State or Region Code'] = 'US'
    output = merge[(merge['State or Region Code'].isnull() == False) & (
        merge['Population'].isnull() == False)][['State or Region Code', 'Population']]

    output.to_csv('./data/US_Population.csv')

    return output


def check_download(date, filesource, dataquery, filenamePrefix, folder):
    """Daily checker to see how if files have been updated on CDC website"""

    # Crate folder if not exist
    if not os.path.exists(folder):
        os.makedirs(folder)
    # Download State Data
    daterange = pd.date_range('2020-01-24', date)
    # for file in os.listdir(folder):
    #     print(file.split('.')[0][-10:])
    #     pdb.set_trace()
    #     print(datetime.datetime.strptime(file[-10:], '%Y-%m-%d'))
    datelist = [datetime.datetime.strptime(file.split(
        '.')[0][-10:], '%Y-%m-%d') for file in os.listdir(folder)]
    missing_dates = [d for d in daterange if d not in datelist]
    glog.info('Missing dates {}'.format(missing_dates))
    for dt in missing_dates:
        query = "{}'{}'".format(dataquery, dt.date())
        download_file(dt.date(), filesource, query, filenamePrefix, folder)
    glog.info('Done Downloading files')


def consolidate_state_data():
    """combine daily files to one consolidated file """

    path = './StateData'
    usDataDf = pd.DataFrame(
        columns=[
            'Date',
            'state',
            'tot_cases',
            'new_case',
            'tot_death',
            'new_death'])
    for file in os.listdir('./StateData'):
        dt = os.path.basename(file).split('.')[0][-10:]
        df = pd.read_csv(os.path.join(path, file))
        df['Date'] = dt
        df[['Date', 'submission_date']] = df[['Date', 'submission_date']].apply(pd.to_datetime)
        df[['tot_cases', 'new_case', 'tot_death', 'new_death']] = df[[
            'tot_cases', 'new_case', 'tot_death', 'new_death']].apply(pd.to_numeric)
        df.loc['US'] = df.sum(numeric_only=True)
        df.loc['US', 'state'] = 'US'
        df.loc['US', 'Date'] = dt
        df.loc['US', 'submission_date'] = dt
        usDataDf = usDataDf.append(
            df[['Date', 'submission_date', 'state', 'tot_cases', 'new_case', 'tot_death', 'new_death']])

    usDataDf['death rate'] = usDataDf['tot_death'].astype(float) / usDataDf['tot_cases'].astype(float)
    usDataDf['death rate'] = usDataDf['death rate'].fillna(0)

    pop = process_population_data('./data/pop.html')
    newrow = {'State or Region Code': 'NYC', 'Population': 8336817}
    pop = pop.append(newrow, ignore_index=True)
    test = pd.merge(
        left=usDataDf,
        right=pop,
        left_on='state',
        right_on='State or Region Code',
        how='outer')
    test['Total Cases per Population'] = test['tot_cases'] / test['Population']
    test['New Cases per Population'] = test['new_case'] / test['Population']
    test['7 day average new cases with 7 day lag'] = 100000 * \
        (test['new_case'].shift(7).rolling(window=7).mean()) / test['Population']
    col = '7 day average new cases with 7 day lag'
    conditions = [(test[col] < 1.0),
                  (test[col] >= 1.0) & (test[col] < 4.0),
                  (test[col] >= 4) & (test[col] < 7),
                  (test[col] >= 7)]
    values = ['Minimal Tier 4', 'Moderate Tier 3', 'Substantial Tier 2', 'Widespread Tier 1']
    test['Risk Level'] = np.select(conditions, values)
    test = test.dropna(subset=['Population', 'State or Region Code'])

    prod_data_folder = './ProdData'
    if not os.path.exists(prod_data_folder):
        os.makedirs(prod_data_folder)
    test.to_csv('{}/USDatabyStates.csv'.format(prod_data_folder))

    return test
