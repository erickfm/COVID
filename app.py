import streamlit as st
import pandas as pd
from dashboard.constants import github_image_path
import os

from dashboard.functions import get_mapbox, get_time_series
from dashboard.constants import margins_css

st.set_page_config(page_title='COVID-19 Dashboard', page_icon="🌎", layout="wide", initial_sidebar_state='collapsed')
st.markdown(margins_css, unsafe_allow_html=True)


with st.sidebar:
    main_page = st.button('COVID-19 Dashboard', use_container_width=1)
    about_page = st.button('About', use_container_width=1)
    if not about_page:
        main_page = True

if main_page:
    # Load data
    confirmed_cases_data = pd.read_csv('https://raw.githubusercontent.com/erickfm/COVID/main/data/time_series_covid19_confirmed_US.csv')
    deaths_data = pd.read_csv('https://raw.githubusercontent.com/erickfm/COVID/main/data/time_series_covid19_deaths_US.csv')

    st.write('## COVID-19 Dashboard')
    col_1, col_2 = st.columns([23, 10])
    col_1a, col_1b = col_1.columns([1, 1])
    col_3, col_4 = st.columns([35, 10])
    size = col_1a.selectbox('size', ['Fatality Rate', 'Deaths'], index=1)
    color = col_1b.selectbox('color', ['Fatality Rate', 'Deaths'], index=0)
    county_state = col_4.selectbox('County', confirmed_cases_data['Admin2']+', '+confirmed_cases_data['Province_State'], index=234)
    agg_option = col_4.selectbox('Aggregation Options', ['Cumulative', 'Daily', 'Daily Rolling Average'])
    if agg_option == 'Daily Rolling Average':
        avg_window = col_4.slider('Average Window', 2, 30, value=7)
    else:
        avg_window = None

    predictive_analytics = col_4.checkbox('Predictive Analytics')
    if predictive_analytics:
        forward_days = col_4.slider('Forecast Length', 0, None, 1095)
        test_days = col_4.slider('Test Length', 0, 1095, 0)
    else:
        forward_days = None
        test_days = None

    fig, data = get_mapbox(confirmed_cases_data, deaths_data, size, color)
    fig_ts = get_time_series(confirmed_cases_data,
                             deaths_data,
                             county_state,
                             test_days,
                             forward_days,
                             agg_option,
                             avg_window,
                             predictive_analytics)
    col_1.plotly_chart(fig, use_container_width=True, theme=None, height=100)
    table = data.sort_values('Fatality Rate', ascending=0).drop(columns=['Lat', 'Long_', 'County, State'])
    table = table.rename(columns={'Admin2': 'County', 'Province_State':'State', 'Confirmed Cases': 'Cases'})
    col_2.write('##### US Counties')
    col_2.dataframe(table, use_container_width=True, hide_index=True, height=400)
    col_3.plotly_chart(fig_ts, use_container_width=True)



if about_page:
    st.markdown('# About \n')
    st.write(
        "Built by [Erick Martinez](https://github.com/erickfm)."
        "")
    st.markdown(f"""<div><a href="https://github.com/erickfm/Dewey"><img src="{github_image_path}" style="padding-right: 10px;" width="6%" height="6%"></a>""",
                unsafe_allow_html=1)
