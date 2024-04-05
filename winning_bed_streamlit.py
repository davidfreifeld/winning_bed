import streamlit as st
import pandas as pd

from winning_bed import WinningBed, algo_types

def on_run_click():
    this_winning_bed = WinningBed(bids_df=bids_df, house_cost=house_cost, algo_type=algo_type)
    st.session_state.results_df = this_winning_bed.run()
    
title = 'Wrong Side of the Bid'
st.set_page_config(page_title=title)
st.title(title)

st.write('See [here](%s) for information about the algorithms.' % 'https://en.wikipedia.org/wiki/Rental_harmony')

left_col, right_col = st.columns(2)

uploaded_bids_file = st.file_uploader(label='Bed Bids CSV File', type='csv')
if uploaded_bids_file is not None:
    bids_df = pd.read_csv(uploaded_bids_file, index_col=0)

with left_col:
    house_cost = st.number_input('Total cost of the rental', step=1, value=1900)

with right_col:
    algo_type = st.selectbox('Algo to Use', algo_types)

st.button('Run', on_click=on_run_click, type="primary", use_container_width=True)

left_col, mid_col, right_col = st.columns(3)
with mid_col:
    if 'results_df' in st.session_state:
        st.header('Results:')
        st.dataframe(st.session_state.results_df, column_config={'Price': st.column_config.NumberColumn("Price", format="$ %d")})
