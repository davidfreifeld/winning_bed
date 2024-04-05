import pandas as pd
from pulp import LpMaximize, LpProblem, LpStatus, lpSum, LpVariable

class WinningBed:

    def __init__(self, bids_df, house_cost):
        self.bids_df = bids_df
        self.house_cost = house_cost
        self.beds = self.bids_df.columns
        self.people = self.bids_df.index


    def init_maxsum_lp_problem(self):

        ## TODO: can make this cleaner        
        ## initialize the variables
        self.beds_vars = {}
        for person, row in self.bids_df.iterrows():
            self.beds_vars[person] = {}
            for bed, _ in row.items():
                self.beds_vars[person][bed] = LpVariable(name=f"{person}_{bed}", cat="Binary")

        self.model = LpProblem(name="beds", sense=LpMaximize)

        self.model += lpSum( [ [ self.bids_df.loc[person][bed] * self.beds_vars[person][bed] for person in self.people ] for bed in self.beds ] )

        for person in self.people:
            self.model += lpSum( [self.beds_vars[person][bed] for bed in self.beds ] ) <= 1
            
        for bed in self.beds:
            self.model += lpSum( [self.beds_vars[person][bed] for person in self.people ] ) == 1


    def solve_maxsum_lp_problem(self, print_output=True):
        self.model.solve()

        solved_variables_dict = self.model.variablesDict()

        if print_output:
            print('\t' + '\t'.join(self.beds))
            for person in self.people:
                print(person + '\t' + '\t'.join([str(int(solved_variables_dict[f"{person}_{bed}"].value())) for bed in self.beds]))

        # turn the pulp variables dict into a regular dict, and calculate maxsum
        self.assignments_dict = {}
        for bed in self.beds:
            for person in self.people:
                if int(solved_variables_dict[f"{person}_{bed}"].value()):
                    self.assignments_dict[bed] = person


    def get_bids_from_assignments(self, assignments_dict_p):
        bids_dict = {}
        for bed, person in assignments_dict_p.items():
            bids_dict[bed] = self.bids_df.loc[person][bed]
        return bids_dict


    def get_bids_total(self, bids_dict):
        return sum(bids_dict.values())


    def calc_prices_brams_kilgour(self, print_output=True):

        diffs_from_maxsum = {}
        
        # calculate the maxsum values; these won't change
        maxsum_bids = self.get_bids_from_assignments(self.assignments_dict)
        maxsum = self.get_bids_total(maxsum_bids)
        maxsum_surplus = maxsum - self.house_cost
        
        if print_output:
            print(maxsum_bids)
            print(f"Initial maxsum surplus: {maxsum_surplus}\n")
        
        if maxsum_surplus < 0:
            if print_output:
                print(f"Maxsum is {maxsum}; Problem is infeasible!")
            return
        elif maxsum_surplus == 0:
            if print_output:
                print("Maxsum is equal to house cost - all done!")
            return maxsum_bids

        # initialize the loop variables
        next_highest_bidders = self.assignments_dict.copy()
        next_highest_bids = maxsum_bids.copy()
        current_bids_total = maxsum
        current_surplus = maxsum_surplus

        while current_surplus > 0:
            
            for bed in self.beds:
                
                # is there a lower bid?
                if next_highest_bids[bed] > self.bids_df[bed].min():
                    
                    next_highest_bidder_info = self.bids_df[bed].where(lambda bid: bid < next_highest_bids[bed]).dropna().sort_values(ascending=False)[[0]]
                    next_highest_bidder = next_highest_bidder_info.index[0]
                    next_highest_bid = next_highest_bidder_info.item()
                        
                    next_highest_bidders[bed] = next_highest_bidder
                    next_highest_bids[bed] = next_highest_bid
                
                diffs_from_maxsum[bed] = maxsum_bids[bed] - next_highest_bids[bed]
            
            current_bids_total = self.get_bids_total(self.get_bids_from_assignments(next_highest_bidders))
            current_surplus = current_bids_total - self.house_cost
            diffs_from_maxsum_total = self.get_bids_total(diffs_from_maxsum)
            
            if print_output:
                print(f"Done with loop. Current surplus: {current_surplus}\n")
            
            if current_surplus < 0:
                if print_output:
                    print(f"Surplus is {current_surplus}. Allocating proportionally...")
                
                for bed in self.beds:
                    next_highest_bids[bed] = round(maxsum_bids[bed] - ((diffs_from_maxsum[bed] / diffs_from_maxsum_total) * float(maxsum_surplus)), 2)
                
                if print_output:    
                    print("Found optimal bids!")
                    print(next_highest_bids)
                
                return next_highest_bids
            
            elif current_surplus == 0:
                if print_output:
                    print("Landed on exactly zero surplus - found optimal bids!")
                return next_highest_bids
            

    def get_results_df(self, results_dict):
        results_df = pd.DataFrame([['', 0.0]] * len(self.beds), columns=['Person', 'Price'], index=self.beds)
        
        for bed, price in results_dict.items():
            print(f"Bed: {bed}; Price: {price}")
            results_df['Person'][bed] = self.assignments_dict[bed]
            results_df['Price'][bed] = price

        return results_df