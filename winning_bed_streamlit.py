import streamlit as st
import pandas as pd

from winning_bed import WinningBed

if 'results_df' not in st.session_state:
    st.session_state.results_df = pd.DataFrame()

def on_run_click():
    this_winning_bed = WinningBed(bids_df=bids_df, house_cost=house_cost)
    this_winning_bed.init_maxsum_lp_problem()
    this_winning_bed.solve_maxsum_lp_problem()
    results_dict = this_winning_bed.calc_prices_brams_kilgour()
    st.session_state.results_df = this_winning_bed.get_results_df(results_dict)
    
title = 'Winning Bed'
st.set_page_config(page_title=title)
st.title(title)

left_col, right_col = st.columns(2)

with left_col:
    uploaded_bids_file = st.file_uploader(label='Bids CSV File', type='csv')
    if uploaded_bids_file is not None:
        bids_df = pd.read_csv(uploaded_bids_file, index_col=0)

with right_col:
    house_cost = st.number_input('Total cost of the rental', step=1, value=1900)

st.button('Run', on_click=on_run_click, type="primary")

st.dataframe(st.session_state.results_df, column_config={'Price': st.column_config.NumberColumn("Price", format="$ %d")})