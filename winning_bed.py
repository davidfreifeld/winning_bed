import pandas as pd
import re
from pulp import LpMaximize, LpMinimize, LpProblem, LpStatus, lpSum, LpVariable

algo_types = ['Brams Kilgour (Maxsum+Second Price)', 'Sung Vlach (Maxsum+Minsum Prices)']

class WinningBed:

    def __init__(self, bids_df, house_cost, allow_multiperson_beds, mp_bids_df=None, mp_capacity_df=None):
        self.bids_df = bids_df
        self.house_cost = house_cost
        
        self.beds_dict = {}

        self.people_dict = {}
        for person in self.bids_df.index.to_list():
            self.people_dict[person] = ""

        self.allow_multiperson_beds = allow_multiperson_beds
        
        print('\n\n')
        print('====================================')
        print('Initializing Winning Bed Object')
        print('====================================')
        print('\n')

        if self.allow_multiperson_beds:
            self.mp_bids_df = mp_bids_df
            self.mp_capacity_df = mp_capacity_df
            self.couples = self.mp_bids_df.index.to_list()

            print("Multiperson Bed Capacity Data Frame:")
            print(mp_capacity_df)
            print('\n')

            for bed, row in self.mp_capacity_df.iterrows():
                self.beds_dict[bed] = int(row['Capacity'])

            couple_pattern = re.compile("(.*)\\+(.*)")

            for couple in self.mp_bids_df.index.to_list():
                couple_match = couple_pattern.match(couple)
                self.people_dict[couple_match[1]] = couple
                self.people_dict[couple_match[2]] = couple
            
            print("Couples list:")
            print(self.couples)
            print('\n')
        
        else:
            for bed in self.bids_df.columns:
                self.beds_dict[bed] = 1

        print('People and couples dictionary:')
        print(self.people_dict)
        print('\n')
        print('Beds and capacities dictionary:')
        print(self.beds_dict)
        print('\n\n')


    def init_maxsum_lp_problem(self, print_model=False):    
        ## initialize the variables
        self.maxsum_vars = {}
        for person in self.people_dict.keys():
            self.maxsum_vars[person] = {}
            for bed in self.beds_dict.keys():
                self.maxsum_vars[person][bed] = LpVariable(name=f"{person}_{bed}", cat="Binary")

        if self.allow_multiperson_beds:
            for couple in self.couples:
                self.maxsum_vars[couple] = {}
                for bed, capacity in self.beds_dict.items():
                    if capacity == 2:
                        self.maxsum_vars[couple][bed] = LpVariable(name=f"{couple}_{bed}", cat="Binary")

        self.maxsum_model = LpProblem(name="maxsum", sense=LpMaximize)

        ## single person beds and bids
        objective_list = [ [ self.bids_df.loc[person][bed] * self.maxsum_vars[person][bed] for person in self.people_dict.keys() ] for bed in self.beds_dict.keys() ]

        ## couples beds and bids
        if self.allow_multiperson_beds:
            objective_list += [ [ self.mp_bids_df.loc[couple][bed] * self.maxsum_vars[couple][bed] for couple in self.couples ] for bed, capacity in self.beds_dict.items() if capacity == 2 ]

        self.maxsum_model += lpSum(objective_list)

        # each person needs a bed
        for person, couple in self.people_dict.items():

            person_constraint = [ self.maxsum_vars[person][bed] for bed in self.beds_dict.keys() ]

            if self.allow_multiperson_beds and couple != '':
                person_constraint += [ self.maxsum_vars[couple][bed] for bed, capacity in self.beds_dict.items() if capacity == 2 ]

            self.maxsum_model += lpSum( person_constraint ) == 1
        
        for bed, capacity in self.beds_dict.items():
            
            # each bed can have at most its capacity number of people in it
            bed_constraint = [ self.maxsum_vars[person][bed] for person in self.people_dict.keys() ]

            if self.allow_multiperson_beds and capacity == 2:
                bed_constraint += [ 2 * self.maxsum_vars[couple][bed] for couple in self.couples ]

                # two people who are not a couple can't be in the same bed
                for this_person, this_couple in self.people_dict.items():
                    for that_person, that_couple in self.people_dict.items():
                        if this_person != that_person and this_couple != that_couple:
                            self.maxsum_model += self.maxsum_vars[this_person][bed] + self.maxsum_vars[that_person][bed] <= 1
            
            self.maxsum_model += lpSum( bed_constraint ) <= capacity

        if print_model:
            print('\n\n')
            print(self.maxsum_model)
            print('\n\n')


    def solve_maxsum_lp_problem(self, print_output=True):
        self.maxsum_model.solve()

        solved_variables_dict = self.maxsum_model.variablesDict()

        if print_output:
            print('\t' + '\t'.join(self.beds_dict.keys()))
            for person, couple in self.people_dict.items():
                bed_result_list = []
                for bed, capacity in self.beds_dict.items():
                    is_in_bed_int = int(solved_variables_dict[f"{person}_{bed}"].value())
                    if capacity == 2 and couple != '':
                        is_in_bed_int += int(solved_variables_dict[f"{couple.replace('+', '_')}_{bed}"].value())
                    bed_result_list += [ str(is_in_bed_int) ]
                print(person + '\t' + '\t'.join(bed_result_list))

        # turn the pulp variables dict into a regular dict
        self.assignments_dict = {}
        for bed in self.beds_dict.keys():
            for person in self.people_dict.keys():
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
        for bed in self.beds_dict.keys():
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
        self.minsum_model += lpSum( [ self.minsum_vars[bed] for bed in self.beds_dict.keys() ] ) >= self.house_cost

        self.minsum_model += lpSum( [ self.minsum_vars[bed] for bed in self.beds_dict.keys() ] )

    
    def solve_minsum_lp_problem(self):
        self.minsum_model.solve()

        solved_variables_dict = self.minsum_model.variablesDict()

        # turn the pulp variables dict into a regular dict
        minsum_prices_dict = {}
        for bed in self.beds_dict.keys():
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
            
            for bed in self.beds_dict.keys():
                
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
                
                for bed in self.beds_dict.keys():
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
        results_df = pd.DataFrame([['', 0.0]] * len(self.beds_dict.keys()), columns=['Person', 'Price'], index=self.beds_dict.keys())
        
        for bed, price in results_dict.items():
            print(f"Bed: {bed}; Price: {price}")
            results_df['Person'][bed] = self.assignments_dict[bed]
            results_df['Price'][bed] = price

        return results_df