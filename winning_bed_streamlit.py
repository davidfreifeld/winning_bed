import streamlit as st
import pandas as pd

from winning_bed import WinningBed

def on_run_click():
    this_winning_bed = WinningBed(bids_df=bids_df, house_cost=house_cost)
    this_winning_bed.run()

title = 'Winning Bed'
st.set_page_config(page_title=title)
st.title(title)

uploaded_bids_file = st.file_uploader(label='Bids CSV File', type='csv')
if uploaded_bids_file is not None:
    bids_df = pd.read_csv(uploaded_bids_file, index_col=0)

house_cost = st.number_input('Total cost of the rental')

st.button('Run', on_click=on_run_click, type="primary")