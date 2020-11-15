# -*- coding: utf-8 -*-
import datetime
import glog
import numpy as np
import os
import pandas as pd
import processData
import pdb

import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_table
from dash.dependencies import Input, Output

import plotly.express as px
import plotly.graph_objs as go

from ipywidgets import widgets

prev_day = datetime.datetime.today() - datetime.timedelta(1)
data_str = '{}-{}-{:02d}'.format(prev_day.year, prev_day.month, prev_day.day)
usStateDataLink = "9mfq-cb36"
usDeathDataLink = '9bhg-hcku'
caseSurveillanceData = 'vbim-akqf'

us_state_data_query = "SELECT * WHERE submission_date="
case_surveillance_query = "SELECT * WHERE cdc_report_dt="

processData.check_download(
    prev_day,
    usStateDataLink,
    us_state_data_query,
    'US-State-Data',
    'StateData')
processData.check_download(
    prev_day,
    caseSurveillanceData,
    case_surveillance_query,
    'Case-Surveillance',
    'CaseSurveillanceData')

usDataDf = processData.consolidate_state_data()
usDataDf['Date'] = usDataDf['Date'].apply(pd.to_datetime)
usDataDf['submission_date'] = usDataDf['submission_date'].apply(pd.to_datetime)

external_scripts = ['/assets/style.css']

usDataDf2 = usDataDf[~usDataDf.state.isin(['US'])]
# usDataDf = pd.read_csv('./ProdData/USDatabyStates.csv')
# currDate = datetime.dateime(2020,10,24)

topCases = usDataDf2[usDataDf2['Date'] == data_str][
    ['Date','state','tot_cases','tot_death']].sort_values('tot_cases', ascending=False)
USTotalCases = usDataDf2[usDataDf2['submission_date']==data_str]['tot_cases'].astype(float).sum()
statesNames = usDataDf.sort_values('state')['state'].unique().tolist()
usDataDf['new_case'] = usDataDf['new_case'].astype(float)
# pdb.set_trace()
USTopNewCases = usDataDf2[usDataDf2['submission_date'] == data_str][['state', 'new_case']].sort_values(
    'new_case', ascending=False)
# pdb.set_trace()
# tot_cases_growth = usDataDf.pivot_table(
#     'tot_cases',
#     ['Date'],
#     'state').sort_values('Date').pct_change(
#         fill_method='pad')

death_rate_rank = usDataDf[usDataDf['Date'] == data_str].sort_values(
    'death rate', ascending=False, na_position='last')[['state', 'death rate']]

usDataDf['submission_date'] = pd.to_datetime(
    usDataDf['submission_date']).apply(lambda x: x.date())

us_cases = usDataDf.copy()
for col in us_cases.columns:
    us_cases[col] = us_cases[col].astype(str)

us_cases = us_cases[~us_cases.state.isin(['US'])][['Date', 'submission_date', 'state',
                                                   'tot_cases', 'tot_death', 'new_case', 'new_death']]
us_cases['Data'] = ("{state}<br>"
                    "Total Cases {tot_cases}<br>"
                    "Total Death {tot_death}<br>"
                    "New Case {new_case}<br>"
                    "New Death {new_death}".format(
                        state = us_cases['state'], 
                        tot_cases = us_cases['tot_cases'], 
                        tot_death = us_cases['tot_death'],
                        new_case = us_cases['new_case'],
                        new_death = us_cases['new_death']))

glog.info('Plot animcation')

us_cases['tot_cases'] = us_cases['tot_cases'].astype(float).astype(int)

fig = px.choropleth(us_cases,
                    scope='usa',
                    locations="state",
                    locationmode='USA-states',
                    color=us_cases['tot_cases'],
                    hover_name="state",
                    featureidkey='properties.state',
                    hover_data=['Data'],
                    animation_frame="submission_date", animation_group="state",
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

data = usDataDf2[usDataDf2['Date'] == data_str]

fig2 = px.choropleth(data,
                     scope='usa',
                     locations="state",
                     locationmode='USA-states',
                     color=data['Risk Level'],
                     hover_name="state",
                     featureidkey='properties.state',
                     hover_data=['7 day average new cases with 7 day lag'],
                     # animation_frame="submission_date", animation_group="state",
                     color_continuous_scale='Reds',
                     labels={
                         'Risk Level': 'Risk level based on 7 day average new cases with 7 day lag'},
                     title='State Risk Level'
                     )

fig2.update_layout(
    showlegend=True,
    legend_title_text='<b>Risk Level</b>',
    font={"size": 16, "color": "#808080", "family": "calibri"},
    margin={"r": 0, "t": 40, "l": 0, "b": 0},
    legend=dict(orientation='v'),
    geo=dict(bgcolor='rgba(0,0,0,0)', lakecolor='#e0fffe')
)


app = dash.Dash(__name__, external_stylesheets=[dbc.themes.LUMEN])
# app = dash.Dash(__name__, external_stylesheets=external_scripts)

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
                    html.H2(
                        "As of {} US Total Reported Cases: {}".format(data_str, USTotalCases),
                        style={'textAlign': 'center', 'marginLeft': 50, 'marginBottom': 30, 'marginTop': 30}),
                        # todo: unify units here
                    html.H4(
                        "Top 5 States with the Most New Cases Today",
                        style={'textAlign': 'left', 'marginLeft': 50, 'marginBottom': 30, 'marginTop': 30}),
                    dash_table.DataTable(
                        id='table2',
                        columns=[ {'name': i, 'id': i} for i in USTopNewCases.columns],
                        data=USTopNewCases.iloc[0:5, :].to_dict('rows'),
                        style_header={'backgroundColor': 'rgb(230, 230, 230)','fontWeight': 'bold'},
                        style_cell={
                            'textAlign': 'center',
                            'font-family' : 'var(--text_font_family)'
                        },
                        style_data={"margin-left": "auto","margin-right": "auto"}),
                    html.H3(
                        "Top 5 States with the Highest Death Rate",
                        style={'textAlign': 'left', 'marginLeft': 50, 'marginBottom': 30, 'marginTop': 30}),
                    dash_table.DataTable(
                        id='table3',
                        columns=[ {"name": i, "id": i} for i in death_rate_rank.columns],
                        data=death_rate_rank.iloc[0:5, :].to_dict('rows'),
                        style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                        style_cell={
                            'textAlign': 'center',
                            'font-family' : 'var(--text_font_family)'
                        },
                        style_data={"margin-left": "auto", "margin-right": "auto"}),
                    html.H3(
                        "Covid Risk Level",
                        style={"textAlign": "left", 'marginBottom': 30, 'marginTop': 30}),
                    dcc.Graph(figure=fig2)])
                    ]
                ),
        # First Tab
        dcc.Tab(
            label='US Total Cases',
            className ='custom-tab',
            selected_className ='custom-tab--selected',
            children=[
                html.Div([
                    html.H3(
                        "Top 5 States by Total Covid Cases", 
                        style={'textAlign': 'left','marginBottom': 100, 'marginTop': 100}),
                    dash_table.DataTable(
                        id='table',
                        columns=[{"name": i, "id": i} for i in topCases.columns],
                        data=topCases.iloc[0:5, :].to_dict("rows"),
                        style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                        style_cell={'textAlign': 'center'},
                        style_data={"margin-left": "auto", "margin-right": "auto"}),
                    html.H3(
                        "Covid Cases by States Animation", 
                        style={"textAlign": "left", 'marginBottom': 100, 'marginTop': 100}),
                    dcc.Graph(figure=fig)
                    ])
            ]),
        # Second Tab
        dcc.Tab(
            label='US Death Rate',
            className ='custom-tab',
            selected_className ='custom-tab--selected',
            children=[
                html.Div([
                    html.H1("US Death Rate by States", style={"textAlign": "center"}),
                    html.Div([
                        html.Div([
                            dcc.Dropdown(
                                id='state-selected',
                                value='state',
                                options=[{'label': i, 'value': i} for i in statesNames])],
                                style={"display": "block",
                                        "marginLeft": "auto",
                                        "marginRight": "auto",
                                        "width": "60%"}),
                            ]),
                        dcc.Graph(id='us_death_rate')])
                    ]),
        # Third Tab
        dcc.Tab(
            label='US Case Surveillance',
            className ='custom-tab',
            selected_className ='custom-tab--selected')
    ])
])


@ app.callback(Output('us_death_rate', 'figure'),
               [Input('state-selected', 'value')])
def update_graph(selected_dropdown):

    chart_title = 'State Death Rate Time Series: {}'.format(selected_dropdown)
    figure = px.line(usDataDf[usDataDf['state'] == selected_dropdown],
                     x="submission_date",
                     y="death rate",
                     title=chart_title)

    return figure


if __name__ == '__main__':
    app.run_server(debug=True)
