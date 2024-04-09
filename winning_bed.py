import pandas as pd
from pulp import LpMaximize, LpMinimize, LpProblem, LpStatus, lpSum, LpVariable

algo_types = ['Brams Kilgour (Maxsum+Second Price)', 'Sung Vlach (Maxsum+Minsum Prices)']

class WinningBed:

    def __init__(self, bids_df, house_cost):
        self.bids_df = bids_df
        self.house_cost = house_cost
        self.beds = self.bids_df.columns
        self.people = self.bids_df.index


    def init_maxsum_lp_problem(self):    
        ## initialize the variables
        self.maxsum_vars = {}
        for person in self.people:
            self.maxsum_vars[person] = {}
            for bed in self.beds:
                self.maxsum_vars[person][bed] = LpVariable(name=f"{person}_{bed}", cat="Binary")

        self.maxsum_model = LpProblem(name="maxsum", sense=LpMaximize)

        self.maxsum_model += lpSum( [ [ self.bids_df.loc[person][bed] * self.maxsum_vars[person][bed] for person in self.people ] for bed in self.beds ] )

        for person in self.people:
            self.maxsum_model += lpSum( [self.maxsum_vars[person][bed] for bed in self.beds ] ) <= 1
            
        for bed in self.beds:
            self.maxsum_model += lpSum( [self.maxsum_vars[person][bed] for person in self.people ] ) == 1


    def solve_maxsum_lp_problem(self, print_output=True):
        self.maxsum_model.solve()

        solved_variables_dict = self.maxsum_model.variablesDict()

        if print_output:
            print('\t' + '\t'.join(self.beds))
            for person in self.people:
                print(person + '\t' + '\t'.join([str(int(solved_variables_dict[f"{person}_{bed}"].value())) for bed in self.beds]))

        # turn the pulp variables dict into a regular dict
        self.assignments_dict = {}
        for bed in self.beds:
            for person in self.people:
                if int(solved_variables_dict[f"{person}_{bed}"].value()):
                    self.assignments_dict[bed] = person

        # calculate the maxsum values; these won't change
        self.maxsum_bids = self.get_bids_from_assignments(self.assignments_dict)
        self.maxsum = self.get_bids_total(self.maxsum_bids)
        self.maxsum_surplus = self.maxsum - self.house_cost
        
        if print_output:
            print(self.maxsum_bids)
            print(f"Initial maxsum surplus: {self.maxsum_surplus}\n")
        
        if self.maxsum_surplus < 0:
            if print_output:
                print(f"Maxsum is {self.maxsum}; Problem is infeasible!")
            return 0
        else:
            print(f"Maxsum is {self.maxsum}")
            return 1


    def init_minsum_lp_problem(self):
        # initialize the variables, which are the prices for each bed. we already have the assignments
        self.minsum_vars = {}
        for bed in self.beds:
            ## TODO: lowBound?
            self.minsum_vars[bed] = LpVariable(name=f"{bed}")

        self.minsum_model = LpProblem(name="minsum", sense=LpMinimize)

        # no one should have envy
        for this_bed in self.beds:
            this_person = self.assignments_dict[this_bed]
            this_person_bid = self.bids_df[this_bed][this_person]
            this_person_surplus = this_person_bid - self.minsum_vars[this_bed]
            
            for other_bed in self.beds:
                if this_bed != other_bed:
                    other_person = self.assignments_dict[other_bed]
                    other_person_bid = self.bids_df[other_bed][other_person]
                    other_person_surplus = other_person_bid - self.minsum_vars[other_bed]
                    
                    # my "surplus" should be at least as good as the other person's
                    self.minsum_model += this_person_surplus - other_person_surplus >= 0

        # prices should be at least the cost of the house
        self.minsum_model += lpSum( [ self.minsum_vars[bed] for bed in self.beds ] ) >= self.house_cost

        self.minsum_model += lpSum( [ self.minsum_vars[bed] for bed in self.beds ] )

    
    def solve_minsum_lp_problem(self):
        self.minsum_model.solve()

        solved_variables_dict = self.minsum_model.variablesDict()

        # turn the pulp variables dict into a regular dict
        minsum_prices_dict = {}
        for bed in self.beds:
            minsum_prices_dict[bed] = solved_variables_dict[f"{bed}"].value()
        
        return minsum_prices_dict
            
        
    def get_bids_from_assignments(self, assignments_dict_p):
        bids_dict = {}
        for bed, person in assignments_dict_p.items():
            bids_dict[bed] = self.bids_df.loc[person][bed]
        return bids_dict


    def get_bids_total(self, bids_dict):
        return sum(bids_dict.values())


    def calc_prices_brams_kilgour(self, print_output=True):

        diffs_from_maxsum = {}
        
        if self.maxsum_surplus == 0:
            if print_output:
                print("Maxsum is equal to house cost - all done!")
            return self.maxsum_bids

        # initialize the loop variables
        next_highest_bidders = self.assignments_dict.copy()
        next_highest_bids = self.maxsum_bids.copy()
        current_bids_total = self.maxsum
        current_surplus = self.maxsum_surplus

        while current_surplus > 0:
            
            for bed in self.beds:
                
                # is there a lower bid?
                if next_highest_bids[bed] > self.bids_df[bed].min():
                    
                    next_highest_bidder_info = self.bids_df[bed].where(lambda bid: bid < next_highest_bids[bed]).dropna().sort_values(ascending=False)[[0]]
                    next_highest_bidder = next_highest_bidder_info.index[0]
                    next_highest_bid = next_highest_bidder_info.item()
                        
                    next_highest_bidders[bed] = next_highest_bidder
                    next_highest_bids[bed] = next_highest_bid
                
                diffs_from_maxsum[bed] = self.maxsum_bids[bed] - next_highest_bids[bed]
            
            current_bids_total = self.get_bids_total(self.get_bids_from_assignments(next_highest_bidders))
            current_surplus = current_bids_total - self.house_cost
            diffs_from_maxsum_total = self.get_bids_total(diffs_from_maxsum)
            
            if print_output:
                print(f"Done with loop. Current surplus: {current_surplus}\n")
            
            if current_surplus < 0:
                if print_output:
                    print(f"Surplus is {current_surplus}. Allocating proportionally...")
                
                for bed in self.beds:
                    next_highest_bids[bed] = round(self.maxsum_bids[bed] - ((diffs_from_maxsum[bed] / diffs_from_maxsum_total) * float(self.maxsum_surplus)), 2)
                
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