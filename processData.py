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

    # Create folder if not exist
    if not os.path.exists(folder):
        os.makedirs(folder)
    # Download State Data
    daterange = pd.date_range('2020-01-24', date)
    
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
    cols = ['Date', 'state', 'tot_cases', 'new_case', 'tot_death', 'new_death',
       'submission_date', 'case fatality rate', 'State or Region Code',
       'Population', 'death rate', 'Total Cases per Population',
       'New Cases per Population']
    if os.path.exists('./ProdData/USDatabyStates.csv') and os.stat('./ProdData/USDatabyStates.csv').st_size > 4:
        usDataDf = pd.read_csv('./ProdData/USDatabyStates.csv')
    else:
        usDataDf = pd.DataFrame(columns=cols)

    datelist = usDataDf.Date.unique()
    stateDataDtList = [os.path.basename(file).split('.')[0][-10:] for file in os.listdir('./StateData')]
    missingdates = [i for i in stateDataDtList if i not in datelist]
    missingFiles = ['US-State-Data-{}.csv'.format(dt) for dt in missingdates]
    
    if len(missingFiles)>0:
        for file in missingFiles:
            if os.stat(os.path.join(path,file)).st_size <= 4:
                glog.info('File {} is empty'.format(file))
            else:
                dt = os.path.basename(file).split('.')[0][-10:]
                df = pd.read_csv(os.path.join(path, file))
                df['Date'] = dt
                
                df[['tot_cases', 'new_case', 'tot_death', 'new_death']] = df[[
                    'tot_cases', 'new_case', 'tot_death', 'new_death']].apply(pd.to_numeric)
                df.loc['US'] = df.sum(numeric_only=True)
                df.loc['US', 'state'] = 'US'
                df.loc['US', 'Date'] = dt
                df.loc['US', 'submission_date'] = dt

                df['case fatality rate'] = df['tot_death'].astype(float) / df['tot_cases'].astype(float)
                df['case fatality rate'] = df['case fatality rate'].fillna(0)
                
                pop = process_population_data('./data/pop.html')
                newrow = {'State or Region Code': 'NYC', 'Population': 8336817}
                pop = pop.append(newrow, ignore_index=True)
                test = pd.merge(
                    left=df,
                    right=pop,
                    left_on='state',
                    right_on='State or Region Code',
                    how='outer')

                test['death rate'] = round((100.0*test['tot_death'].astype(float)) / test['Population'],8)
                test['death rate'] = test['death rate'].fillna(0)

                test['Total Cases per Population'] = test['tot_cases'] / test['Population']
                test['New Cases per Population'] = test['new_case'] / test['Population']
                
                usDataDf = usDataDf.append(test[cols])

        usDataDf['Date'] = usDataDf['Date'].apply(pd.to_datetime)
        usDataDf = usDataDf.sort_values(by='Date')
        usDataDf = usDataDf.set_index('Date')

        usDataDf['7 day average new cases'] = usDataDf.groupby('state')['new_case'].transform(lambda x: x.rolling(7, 1).mean())
        usDataDf['7 day average new cases'] = round(usDataDf['7 day average new cases'],0)
        usDataDf['Adjusted Case Rate'] = round(100000 * usDataDf['7 day average new cases'] / usDataDf['Population'],0)
        usDataDf = usDataDf.reset_index()

        col = 'Adjusted Case Rate'
        conditions = [(usDataDf[col] < 1.0),
                    (usDataDf[col] >= 1.0) & (usDataDf[col] < 4.0),
                    (usDataDf[col] >= 4.0) & (usDataDf[col] < 7.0),
                    (usDataDf[col] >= 7.0)]
        values = ['Minimal Tier 4', 'Moderate Tier 3', 'Substantial Tier 2', 'Widespread Tier 1']
        usDataDf['Risk Level'] = np.select(conditions, values)
        usDataDf = usDataDf.dropna(subset=['Population', 'State or Region Code'])


        prod_data_folder = './ProdData'
        if not os.path.exists(prod_data_folder):
            os.makedirs(prod_data_folder)
        
        cols += ['7 day average new cases','Adjusted Case Rate','Risk Level']
        usDataDf[cols].to_csv('{}/USDatabyStates.csv'.format(prod_data_folder), index=False)

    return usDataDf


def consolidate_case_surv_data():
    """ consolidate case surveillance data"""

    path = './CaseSurveillanceData'
    cols = ['Date','cdc_report_dt', 'onset_dt', 'current_status', 'sex',
       'age_group', 'race_ethnicity_combined', 'hosp_yn', 'icu_yn', 'death_yn',
       'medcond_yn']

    if os.path.exists('./ProdData/CaseSurvData.csv') and os.stat('./ProdData/CaseSurvData.csv').st_size > 4:
        cons_df = pd.read_csv('./ProdData/CaseSurvData.csv')
    else:
        cons_df = pd.DataFrame(columns=cols)

    datelist = cons_df.Date.unique()
    caseDataDtList = [os.path.basename(file).split('.')[0][-10:] for file in os.listdir(path)]
    missingdates = [i for i in caseDataDtList if i not in datelist]
    missingFiles = ['Case-Surveillance-{}.csv'.format(dt) for dt in missingdates]

    if len(missingFiles)>0:
        for file in missingFiles:
            if os.stat(os.path.join(path,file)).st_size <= 4:
                glog.info('File {} is empty'.format(file))
                
            else:
                dt = os.path.basename(file).split('.')[0][-10:]
                df = pd.read_csv(os.path.join(path, file))
                df['Date'] = dt
            
                cons_df = cons_df.append(df[cols])
    
        cons_df.to_csv('./ProdData/CaseSurvData.csv', index=False)
    
    return cons_df