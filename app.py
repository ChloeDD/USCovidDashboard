# -*- coding: utf-8 -*-
import datetime
import glog
import numpy as np
import os
import pandas as pd
import processData

import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_table
from dash.dependencies import Input, Output
import plotly.express as px


prev_day = datetime.datetime.today() - datetime.timedelta(1)

processData.check_download(
    prev_day,
    processData.usStateDataLink,
    processData.us_state_data_query,
    'US-State-Data',
    'StateData')
processData.check_download(
    prev_day,
    processData.caseSurveillanceData,
    processData.case_surveillance_query,
    'Case-Surveillance',
    'CaseSurveillanceData')

case_surv = processData.consolidate_case_surv_data()
maxdt = case_surv['cdc_report_dt'].max()

usDataDf = processData.consolidate_state_data()
usDataDf['Date'] = usDataDf['Date'].apply(pd.to_datetime)
usDataDf['submission_date'] = usDataDf['submission_date'].apply(pd.to_datetime)

max_state_dt = usDataDf['Date'].max()
data_str = '{}-{}-{:02d}'.format(max_state_dt.year, max_state_dt.month, max_state_dt.day)

external_scripts = ['/assets/style.css']

usDataDf2 = usDataDf[~usDataDf.state.isin(['US'])]

# DataFrame for top new covid cases
topCases = usDataDf2[usDataDf2['Date'] == data_str][
    ['Date','state','tot_cases','tot_death']].sort_values('tot_cases', ascending=False)
topCases['Date'] = topCases['Date'].apply(lambda x : x.date())
for col in ['tot_cases','tot_death']:
    topCases[col]=topCases[col].apply(lambda x: f'{x:,}')

USTotalCases = usDataDf2[usDataDf2['submission_date']==data_str]['tot_cases'].astype(float).sum()
statesNames = usDataDf.sort_values('state')['state'].unique().tolist()
usDataDf['new_case'] = usDataDf['new_case'].astype(float)

USTopNewCases = usDataDf2[usDataDf2['submission_date'] == data_str][['state', 'new_case',
'7 day average new cases','new_death']].sort_values(
    by='new_case', ascending=False)

us_bar = px.bar(USTopNewCases.sort_values(by='new_case',ascending=True), 
    y = 'state', x = 'new_case', text='new_case', orientation='h', color='new_case',
     color_continuous_scale=["orange", "red"], height=1000)
us_bar.update_traces(texttemplate='%{text:.2s}', textposition='outside')
us_bar.update_layout(uniformtext_minsize=6, uniformtext_mode='hide', 
                     xaxis={'categoryorder':'total descending'})

for col in ['new_case', '7 day average new cases']:
    USTopNewCases[col]=USTopNewCases[col].apply(lambda x: f'{x:,}')

# data for death rate 
death_rate_rank = usDataDf[usDataDf['Date'] == data_str].sort_values(
    'death rate', ascending=False, na_position='last')[['state', 'death rate']]
death_rate_rank['death rate'] = death_rate_rank['death rate'].apply(lambda x: '{:.2f}%'.format(x))

# data for total cases animation
us_cases = usDataDf2.copy()
for col in us_cases.columns:
    us_cases[col] = us_cases[col].astype(str)

us_cases = us_cases[['Date', 'submission_date', 'state',
                     'tot_cases', 'tot_death', 'new_case', 'new_death']]

us_cases['Data'] =us_cases['state'] + '<br>' + \
    'Total Cases ' + us_cases['tot_cases'] + '<br>' + 'Total Death ' + us_cases['tot_death'] + '<br>' + \
    'New Case ' + us_cases['new_case'] +'<br>' + 'New Death ' + us_cases['new_death']

glog.info('Plot animation')

us_cases['tot_cases'] = us_cases['tot_cases'].astype(float).astype(int)

fig = px.choropleth(us_cases,
                    scope='usa',
                    locations="state",
                    locationmode='USA-states',
                    color=us_cases['tot_cases'],
                    hover_name="state",
                    featureidkey='properties.state',
                    hover_data=['Data'],
                    animation_frame="Date", animation_group="state",
                    color_continuous_scale='Reds',
                    labels={'tot_cases': 'Total Number of Cases'},
                    title='US Covid Cases'
                    )

fig.update_layout(
    showlegend=True,
    legend_title_text='<b>Total Number of Cases</b>',
    font={"size": 16, "color": "#808080", "family": "calibri"},
    margin={"r": 0, "t": 40, "l": 0, "b": 0},
    legend=dict(orientation='v'),
    geo=dict(bgcolor='rgba(0,0,0,0)', lakecolor='#e0fffe')
)

#Data for adjusted case rate
data = usDataDf2[usDataDf2['Date'] == data_str]

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.LUMEN])
# app = dash.Dash(__name__, external_stylesheets=external_scripts)
server = app.server

title_shared_style = {'textAlign': 'left', 'marginLeft': 50, 'marginBottom': 30, 'marginTop': 30}

app.layout = html.Div([
    html.H1("US Covid Data Dashboard", style={"textAlign": "center"}), 
    dcc.Markdown('''US covid data visualization using CDC public data''', style={"textAlign": "center"}),
    dcc.Tabs(
        id="tabs", 
        children=[
        dcc.Tab(
            label='Daily Summary',
            className ='custom-tab',
            selected_className ='custom-tab--selected',
            children=[
                html.Div([
                    dcc.Markdown('''### As of ***{}*** US Total Reported Cases: ***{}***'''.format(data_str, 
                    f'{int(USTotalCases):,}'),
                        style={'fontSize':'40','textAlign': 'left', 'fontColor':'black',
                        'marginLeft': 50, 'marginBottom': 30, 
                        'marginTop': 30}),
                    html.H3(
                        "Top 5 States with the Most New Cases Today",
                        style=title_shared_style),
                    dash_table.DataTable(
                        id='table2',
                        columns=[ {'name': i, 'id': i} for i in USTopNewCases.columns],
                        data=USTopNewCases.iloc[0:5, :].to_dict('rows')),
                    html.H3("US New Cases by States", style={"textAlign": "left", 
                    'marginLeft': 50, 'marginBottom': 30, 'marginTop': 30}),
                    dcc.Graph(figure=us_bar),
                    html.H3("US New Cases by States Time Series", style=title_shared_style),
                    html.Div([
                        html.Div([
                            dcc.Dropdown(
                                id='state-selected2',
                                value='US',
                                options=[{'label': i, 'value': i} for i in statesNames]),
                                dcc.RadioItems(
                                id='selected-col',
                                options=[{'label': i, 'value': i} for i in ['new_case', 
                                '7 day average new cases',
                                'New Cases per Population',
                                'Adjusted Case Rate']],
                                value='new_case',
                                labelStyle={'display': 'inline-block'}
                                )
                                ],
                                style={"display": "block",
                                        "marginLeft": "auto",
                                        "marginRight": "auto",
                                        "width": "80%"}),
                            ]),
                    dcc.Graph(id='us_new_cases'),
                    html.H3(
                        "COVID Risk Level",
                        style=title_shared_style),
                    dcc.Markdown('''
                         If we use CA risk level definition(using only Adjusted case rate definition), 
                         we can see how widespread the COVID case growth has been at states level. 

                        Adjusted Case Rate: Calculated as the average daily number of COVID-19+ cases over 7 days 
                        divided by the number of people living in the state then multiplied by 100,000.

                        CA Blueprint for a Safer Economy [links]:(https://covid19.ca.gov/safer-economy/)
                        ''',style=title_shared_style), 
                    html.Div([
                        html.Div([dcc.RadioItems(
                                id='selected-risk-col',
                                options=[{'label': i, 'value': i} for i in 
                                ['Adjusted Case Rate','CA Risk Level Threshold']],
                                value='Adjusted Case Rate',
                                labelStyle={'display': 'inline-block'}
                                )],
                                style={"display": "block",
                                        "marginLeft": "auto",
                                        "marginRight": "auto",
                                        "width": "80%"}),
                            ]),
                    dcc.Graph(id='us_risk_level')
                ])]),
        # First Tab
        dcc.Tab(
            label='US Total Cases',
            className ='custom-tab',
            selected_className ='custom-tab--selected',
            children=[
                html.Div([
                    html.H3(
                        "Top 5 States by Total Covid Cases", 
                        style=title_shared_style),
                    dash_table.DataTable(
                        id='table',
                        columns=[{"name": i, "id": i} for i in topCases.columns],
                        data=topCases.iloc[0:5, :].to_dict("rows")),
                    html.H3(
                        "Covid Cases by States Animation", 
                        style=title_shared_style),
                    dcc.Graph(figure=fig)
                    ])]
        ),
        # Second Tab
        dcc.Tab(
            label='US Death Rate',
            className ='custom-tab',
            selected_className ='custom-tab--selected',
            children=[
                html.Div([
                    html.H3(
                        "Top 5 States with the Highest Death Rate",
                        style=title_shared_style),
                    dash_table.DataTable(
                        id='table4',
                        columns=[ {"name": i, "id": i} for i in death_rate_rank.columns],
                        data=death_rate_rank.iloc[0:5, :].to_dict('rows'),
                        style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                        style_cell={
                            'textAlign': 'center',
                            'font-family' : 'var(--text_font_family)'
                        },
                        style_data={"margin-left": "auto", "margin-right": "auto"}),

                    html.H3("US Death Rate(%) by States", style=title_shared_style),
                    html.Div([
                        
                            dcc.Markdown('''
                            Death Rate(%) is number of death divided by the population.
                            Case Fatality Rate is the number of death divided by the number of confirmed cases.
                            ''',style=title_shared_style),
                            dcc.Dropdown(
                                id='state-selected',
                                value='US',
                                options=[{'label': i, 'value': i} for i in statesNames],
                                style=title_shared_style),
                            dcc.RadioItems(
                                id='death-col',
                                value='death rate',
                                options=[{'label': i, 'value': i} for i in ['death rate', 'case fatality rate']],
                                labelStyle={'display': 'inline-block'},
                                style=title_shared_style),
                            ]),
                        dcc.Graph(id='us_death_rate')])
                    ]),
        # Third Tab
        dcc.Tab(
            label='US Case Surveillance',
            className ='custom-tab',
            selected_className ='custom-tab--selected',
            children=[
                html.Div([
                        html.H3('US Covid Case Surveillance Data',
                                style=title_shared_style),
                        dcc.Markdown(
                            ''' CDC updates this data on montly basis, latest update: {}'''.format(maxdt[:10]),
                            style=title_shared_style),
                        dcc.RadioItems(
                            id='case-selected',
                            value='sex',
                            options=[{'label': i, 'value': i} for i in ['hosp_yn', 'current_status', 'sex',
                                                                        'age_group', 'race_ethnicity_combined', 
                                                                        'icu_yn', 'death_yn','medcond_yn']],
                            style=title_shared_style),
                        dcc.Graph(id='us_case_surv')])
                    ]
            )
        ])
])


@ app.callback(Output('us_death_rate', 'figure'),
               [Input('state-selected', 'value'),
                Input('death-col', 'value')
               ])
def update_graph(selected_dropdown, death_col):


    chart_title = 'State Death Rate Time Series: {}'.format(selected_dropdown)
    figure = px.line(usDataDf[usDataDf['state'] == selected_dropdown],
                     x="Date",
                     y=death_col,
                     title=chart_title)

    return figure

@ app.callback(Output('us_new_cases', 'figure'),
               [Input('state-selected2', 'value'),
                Input('selected-col', 'value')])

def update_newcases_graph(selected_dropdown, selected_col):

    chart_title = 'State New Cases Time Series: {}'.format(selected_dropdown)
    figure = px.line(usDataDf[usDataDf['state'] == selected_dropdown],
                     x="Date",
                     y=selected_col,
                     title=chart_title)

    return figure

@ app.callback(Output('us_risk_level', 'figure'),
               [Input('selected-risk-col', 'value')])

def update_usrisk_chart(selected_risk_col):

    if selected_risk_col =='CA Risk Level Threshold':
        col = 'Risk Level'
    else:
        col = 'Adjusted Case Rate'

    figure = px.choropleth(data,
                        scope='usa',
                        locations="state",
                        locationmode='USA-states',
                        color=data[col],
                        hover_name="state",
                        featureidkey='properties.state',
                        hover_data=['Adjusted Case Rate'],
                        color_continuous_scale='Reds',
                        labels={
                            'Risk Level': 'Risk level based on Adjusted Case Rate'},
                        title='State Risk Level'
                        )

    figure.update_layout(
        showlegend=True,
        legend_title_text='<b>Risk Level</b>',
        font={"size": 16, "color": "#808080", "family": "calibri"},
        margin={"r": 0, "t": 40, "l": 0, "b": 0},
        legend=dict(orientation='v'),
        geo=dict(bgcolor='rgba(0,0,0,0)', lakecolor='#e0fffe')
    )

    return figure

@ app.callback(Output('us_case_surv', 'figure'),
               [Input('case-selected', 'value')])

def update_casesurv_chart(case_selected):

    
    datadf=case_surv.groupby(case_selected).count()/case_surv.shape[0]
    datadf=datadf.reset_index()
    datadf['% Count'] = datadf['cdc_report_dt'].apply(lambda x: '{}%'.format(round(100.0*x,2)))
    figure = px.bar(datadf, x=case_selected, y='% Count', color=case_selected)

    return figure

if __name__ == '__main__':
    app.run_server(debug=True)
