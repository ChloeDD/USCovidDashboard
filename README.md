# USCovidDashboard

This project pulls public US COVID data available on CDC website and produce a dashboard that captures daily US COVID cases. 

Data Source: data.cdc.gov

To access the live dashboard [click here](https://uscovid-sample-dashboard.herokuapp.com/)

![](dashboard_gif.gif)

The dashboard use CDC state level data and case surveillance data to provide summary statistics on US COVID cases. 
There are four tabs on the dashboard, Daily Summary, US Total Cases, US Death Rate, and US Case Sueveillance. 

The Daily Summary tab captures the latest new cases and new deaths published by CDC on daily basis. 
There is a time series chart that shows daily new COVID cases from Mar 2020, can specify the specifc State in the dropdown menu.
The COVID Risk Level chart plots the data of confirmed cases per population. It uses CA adjusted case rate definition to define the risk level. 

The US Total Cases tab shows the cumulative cases by states. There is an animation that shows how state level cumulative cases develop over time. 

The Death Rate tab shows the death rate and case fatality rate for each state over time. 

The Case Surveillance tab shows demographic data that is published by CDC. This data is updated on monthly basis. 
