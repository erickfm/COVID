import streamlit as st
import os
import time
import plotly.express as px
import pandas as pd
from prophet import Prophet
from prophet.plot import plot_plotly, plot_components_plotly
import plotly.graph_objects as go


def get_time_series(confirmed_cases_data, deaths_data, dataset, county_state, test_days, forward_days, agg_option, avg_window, predictive_analytics):
    county_dict = {k: v for k, v in
                   zip(list(confirmed_cases_data['Admin2'] + ', ' + confirmed_cases_data['Province_State']),
                       list(confirmed_cases_data['Admin2']))}
    county = county_dict[county_state]

    # Load the data
    if dataset == 'Deaths':
        df = deaths_data
    else:
        df = confirmed_cases_data
    # Filter the data for Los Angeles
    df_la = df[df['Admin2'] == county]
    # Drop the non-date columns
    if dataset == 'Deaths':
        df_la = df_la.drop(
        columns=['UID', 'iso2', 'iso3', 'code3', 'FIPS', 'Admin2', 'Province_State', 'Country_Region', 'Lat', 'Long_',
                 'Combined_Key', 'Population'])
    else:
        df_la = df_la.drop(
            columns=['UID', 'iso2', 'iso3', 'code3', 'FIPS', 'Admin2', 'Province_State', 'Country_Region', 'Lat',
                     'Long_',
                     'Combined_Key'])


    # Convert the data from wide to long format
    df_la_long = df_la.melt(var_name='Date', value_name='Cumulative Count')
    # Convert the 'Date' column to datetime format
    df_la_long['Date'] = pd.to_datetime(df_la_long['Date'])
    # Calculate the daily counts
    df_la_long['Daily Count'] = df_la_long['Cumulative Count'].diff()
    # If the first row is NaN due to the diff() operation, remove it
    la_data = df_la_long.copy()
    # Sort the data by date
    la_data = la_data.sort_values('Date')

    # Rename the columns
    if agg_option == "Cumulative":
        la_data.columns = ['ds', 'y', 'y_daily']
    if agg_option == "Daily":
        la_data.columns = ['ds', 'y_cum', 'y']
    if agg_option == "Daily Rolling Average":
        la_data['moving_average'] = la_data['Daily Count'].rolling(window=avg_window).mean()
        la_data.columns = ['ds', 'y_cum', 'y_daily', 'y']

    # Convert the 'ds' column to datetime format
    la_data['ds'] = pd.to_datetime(la_data['ds'])

    if predictive_analytics:
        # Split the data into a training set and a test set
        if test_days:
            train = la_data[:-test_days]
            test = la_data[-test_days:]
        else:
            train = la_data
            test = []

        # Define the model
        model = Prophet()

        # Fit the model to the training data
        model.fit(train)

        # Define a dataframe to hold the dates for which we want to make predictions
        future = model.make_future_dataframe(periods=test_days + forward_days)

        # Use the model to make predictions
        forecast = model.predict(future)

        # Create the figure
        fig = plot_plotly(model, forecast)

        if test_days:
            # Add the scatter plot for actual counts
            fig.add_trace(go.Scatter(x=test['ds'], y=test['y'], mode='markers', name='Actual ',
                                     marker=dict(color='red', size=4)))

        # Customize the layout
        fig.update_layout(
            title=f'Forecast and Actual COVID-19 {dataset} Counts for {county_state}',
            title_x=0.4,
            xaxis_title='Date',
            yaxis_title='Counts',
            showlegend=True,
            legend=dict(x=0, y=1),
            width=800,
            height=500,
            margin={"r": 0, "t": 0, "l": 0, "b": 0}
        )
        if test_days:
            # Reorder the traces
            fig.data = tuple([fig.data[0], fig.data[4], fig.data[1], fig.data[2], fig.data[3]])
    else:
        # Create a time series plot
        fig = go.Figure(data=go.Scatter(x=la_data['ds'], y=la_data['y']))

        # Add title and labels
        fig.update_layout(title=f'COVID-19 {dataset} in {county_state}',
                          xaxis_title='Date',
                          yaxis_title='Number of Cases')

    return fig


def get_mapbox(confirmed_cases_data, deaths_data, demographics_data, size, color):
    # Take the most recent date from the datasets
    recent_date = confirmed_cases_data.columns[-1]
    day_before_recent = confirmed_cases_data.columns[-2]

    # Calculate the fatality rate
    fatality_rate = deaths_data[recent_date] / confirmed_cases_data[recent_date] * 100

    # Calculate Daily stats
    daily_deaths = (deaths_data[recent_date] - deaths_data[day_before_recent])
    daily_fatality_rate = 100 * ((deaths_data[recent_date] - deaths_data[day_before_recent]) /
                                 (confirmed_cases_data[recent_date] - confirmed_cases_data[day_before_recent]))

    # Prepare a DataFrame for plotting
    data = confirmed_cases_data[["Admin2", "Province_State", "Lat", "Long_"]].copy()
    data["Confirmed Cases"] = confirmed_cases_data[recent_date]
    data["Deaths"] = deaths_data[recent_date]
    data["Fatality Rate"] = fatality_rate
    data["Daily Fatality Rate"] = daily_fatality_rate
    data["Daily Deaths"] = daily_deaths
    data["County, State"] = data["Admin2"] + ', ' + data['Province_State']

    # Clean Demographics data
    demographics_data = demographics_data[['Age.Percent 65 and Older',
                                           'Income.Median Houseold Income',
                                           'Population.Population per Square Mile',
                                           'County',
                                           'State']]
    demographics_data['County, State'] = demographics_data['County'] + ', ' + demographics_data['State']
    data = pd.merge(data, demographics_data, on='County, State')

    # Some Data Cleaning
    data = data[data["Confirmed Cases"] > 0]
    data = data[(data['Lat'] != 0) & (data['Long_'] != 0)]
    data = data[data['Deaths'] != 0]

    # Better Column Names
    data.rename(columns={'Age.Percent 65 and Older': 'Percent 65+',
                         'Income.Median Houseold Income': 'Median Income',
                         'Population.Population per Square Mile': 'Population Density'}, inplace=True)

    try:
        # Create a scatter_mapbox plot
        fig = px.scatter_mapbox(
            data,
            lat="Lat",
            lon="Long_",
            color=color,
            size=size,
            hover_name="County, State",
            hover_data=["Confirmed Cases", "Deaths", "Fatality Rate"],
            zoom=3.5,
            title=f"COVID-19 Dashboard as of {recent_date}",
            height=880,
        )

        fig.update_layout(mapbox_style="open-street-map")
        fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
    except ValueError:
        data.dropna(inplace=True)
        data[data['Daily Fatality Rate'] < 0] = 0
        # Create a scatter_mapbox plot
        fig = px.scatter_mapbox(
            data,
            lat="Lat",
            lon="Long_",
            color=color,
            size=size,
            hover_name="County, State",
            hover_data=["Confirmed Cases", "Deaths", "Fatality Rate"],
            zoom=3.5,
            title=f"COVID-19 Dashboard as of {recent_date}",
            height=880,
        )

        fig.update_layout(mapbox_style="open-street-map")
        fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})

    return fig, data


def get_3D_scatter(data):
    data.dropna(inplace=True)
    # Create the 3D scatter plot
    fig = px.scatter_3d(data,
                        x='Population Density',
                        y='Percent 65+',
                        z='Median Income',
                        color='Fatality Rate',
                        size='Fatality Rate',
                        hover_name='County, State',
                        color_continuous_scale=px.colors.sequential.Plasma,
                        log_x=True)

    # Update layout
    fig.update_layout(title='',
                      scene=dict(
                          xaxis_title='Population Density',
                          yaxis_title='Percent 65+',
                          zaxis_title='Median Income'),
                      autosize=False,
                      width=1000, height=920)
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
    return fig
