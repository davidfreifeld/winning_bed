import streamlit as st
import pandas as pd

from winning_bed import WinningBed, algo_types

## TODO:
## error message instead of crash if no csv file

def on_run_click():

    # reset the results DF and the error message
    st.session_state.results_df = pd.DataFrame(columns=['Person', 'Price'])
    st.session_state.error_msg = ''

    this_winning_bed = WinningBed(bids_df=bids_df, house_cost=house_cost)

    if algo_type in ['Brams Kilgour (Maxsum+Second Price)', 'Sung Vlach (Maxsum+Minsum Prices)']:
        this_winning_bed.init_maxsum_lp_problem()
        maxsum_status = this_winning_bed.solve_maxsum_lp_problem()
        if maxsum_status == 0:
            st.session_state.error_msg = 'Bids are too low - no assignment of beds will meet the cost of the house!'
        else:
            if algo_type == 'Brams Kilgour (Maxsum+Second Price)':
                results_dict = this_winning_bed.calc_prices_brams_kilgour()
            elif algo_type == 'Sung Vlach (Maxsum+Minsum Prices)':
                this_winning_bed.init_minsum_lp_problem()
                results_dict = this_winning_bed.solve_minsum_lp_problem()
        
            st.session_state.results_df = this_winning_bed.get_results_df(results_dict)
        
    
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
    if 'error_msg' in st.session_state:
        st.write(":red[" + st.session_state.error_msg + "]")
