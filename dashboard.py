import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import numpy as np

class DataHandler:
#Stateless application (i.e everything should be determined by the google sheet)
    
    def __init__(self):
        self.load_data()
        self.find_award_pos()

    def load_data(self):
        conn = st.connection("gsheets", type=GSheetsConnection)
        self.entries = conn.read(index_col=0,
                                 usecols=range(24),
                                 ttl=0)
        self.entries = self.entries.replace(np.nan, None)
        self.entries.index = self.entries.index.rename('Entrant')
        self.entries = self.entries[self.entries.index.notnull()]
        self.winners = self.entries.loc['WINNERS'].to_dict()
        self.points = self.entries.loc['Points'].to_dict()
        #Convert strings to ints
        self.points = dict([a, int(x)] for a, x in self.points.items())

        #Get list of awards in announcement order
        self.order = self.entries.loc['Order'].to_dict()
        self.order = list(dict(sorted(self.order.items(), key=lambda item: item[1])).keys())
        self.entries = self.entries.drop(['WINNERS', 'Points', 'Order'])


    def find_award_pos(self):
        #Current Award is the next award that has not been announced
        self.curr_award_index = 0
        while self.winners[self.order[self.curr_award_index]] != None:
            self.curr_award_index += 1

    def previous_award(self):
        #Display previous award's entries and winner, with red or greed if they won or not
        previous_award = self.order[self.curr_award_index - 1]
        return previous_award, self.entries[previous_award], self.winners[previous_award]
        

    def next_award(self):        
        return self.order[self.curr_award_index], self.entries[self.order[self.curr_award_index]]

    def assign_value(self, row, winners):
        if row.loc['Entry'] == winners[row['Category']]:
            return self.points[row['Category']]
        else:
            return 0
    
    def calculate_scores(self,winners):
        scored_df = self.entries.copy()
        scored_df = scored_df.melt(ignore_index=False, var_name='Category', value_name='Entry')
        scored_df['Points'] = scored_df.apply(lambda row: self.assign_value(row, winners), axis=1)
        scored_df = scored_df.groupby('Entrant').sum().sort_values('Points', ascending=False)
        scored_df['Place'] = scored_df['Points'].rank(method='average', ascending=False)
        return scored_df

    def highest_place_possible(self, entrant):
        #Create best possible winners dict
        test_case_dict = self.winners.copy()
        for category, winner in test_case_dict.items():
            if winner == None:
                test_case_dict[category] = entrant[category]
        #Get rank
        best_possible_result = self.calculate_scores(test_case_dict)
        return best_possible_result.loc[entrant.name, 'Place'].item()

    def standings(self):
        standings = self.calculate_scores(self.winners)
        best_place_possible = self.entries.apply(lambda x : self.highest_place_possible(x), axis=1)
        best_place_possible.name = 'Best Place Possible'
        return standings.merge(best_place_possible, on='Entrant').drop(['Category', 'Entry'], axis=1)

if __name__ == '__main__':
    reduce_header_height_style = """
    <style>
        div.block-container {padding-top:1rem;}
        div.st-emotion-cache-16txtl3 {padding-top:1rem;}
    </style>
    """
    st.markdown(reduce_header_height_style, unsafe_allow_html=True)
    dash = DataHandler()
    #st.write(dash.winners)
    # st.write(dash.scores)
    # st.write(dash.entries)
    #st.write(dash.calculate_scores(dash.winners))
    #st.write(dash.highest_place_possible(dash.entries.groupby('Entrant').get_group('Christian')))
    st.title("Oscar Pool Tracker")
    st.header("Standings")
    stand1, stand2 = st.columns([1,2])
    stand1.markdown(f"""
       ### :first_place_medal: {dash.standings().iloc[0].name} \n
       #### :second_place_medal: {dash.standings().iloc[1].name}\n
       #### :third_place_medal: {dash.standings().iloc[2].name}\n
    """)
    stand2.write(dash.standings())  
    st.sidebar.header("*Previous Award*: " + dash.previous_award()[0])
    st.sidebar.write("*Winner*: " + dash.previous_award()[2])
    def highlighter(row):
        if row == dash.previous_award()[2]:
            return "background-color: darkgreen"

        else:
            return "background-color: maroon"

    st.sidebar.write(pd.DataFrame(dash.previous_award()[1]).style.applymap(lambda x: highlighter(x)))
    st.sidebar.header("*Next Award*: " + dash.next_award()[0])
    st.sidebar.write(dash.next_award()[1])
    if st.button('Load Data'):
        st.rerun()