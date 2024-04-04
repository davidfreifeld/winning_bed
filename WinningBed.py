from pulp import LpMaximize, LpProblem, LpStatus, lpSum, LpVariable
import pandas as pd

house_cost = 1900

bids_df = pd.read_csv('bed_bids.csv', index_col=0)
beds = bids_df.columns
people = bids_df.index
bids_df

beds_vars = {}
for person, row in bids_df.iterrows():
    beds_vars[person] = {}
    for bed, bid in row.items():
        beds_vars[person][bed] = LpVariable(name=f"{person}_{bed}", cat="Binary")

model = LpProblem(name="beds", sense=LpMaximize)

model += lpSum( [ [ bids_df.loc[person][bed] * beds_vars[person][bed] for person in people ] for bed in beds ] )

for person in people:
    model += lpSum( [beds_vars[person][bed] for bed in beds ] ) <= 1
    
for bed in beds:
    model += lpSum( [beds_vars[person][bed] for person in people ] ) == 1

model.solve()

variables_dict = model.variablesDict()
print('\t' + '\t'.join(beds))
for person in people:
    print(person + '\t' + '\t'.join([str(int(variables_dict[f"{person}_{bed}"].value())) for bed in beds]))

def get_bids_from_assignments(bids_df_p, assignments_dict_p):
    bids_dict = {}
    for bed, person in assignments_dict_p.items():
        bids_dict[bed] = bids_df_p.loc[person][bed]
    return bids_dict

def get_bids_total(assignments_dict_p):
    return sum(assignments_dict_p.values())

# turn the pulp variables dict into a regular dict, and calculate maxsum
assignments_dict = {}
for bed in beds:
    for person in people:
        if int(variables_dict[f"{person}_{bed}"].value()):
            assignments_dict[bed] = person
# assignments_dict

def calc_final_bid_prices(bids_df_p, assignments_dict_p, house_cost_p):
    
    print(f"House cost: {house_cost_p}")

    diffs_from_maxsum = {}
    
    # calculate the maxsum values; these won't change
    maxsum_bids = get_bids_from_assignments(bids_df_p, assignments_dict_p)
    maxsum = get_bids_total(maxsum_bids)
    maxsum_surplus = maxsum - house_cost_p
    print(maxsum_bids)
    print(f"Initial maxsum surplus: {maxsum_surplus}\n")
    
    if maxsum_surplus < 0:
        print(f"Maxsum is {maxsum}; Problem is infeasible!")
        return
    elif maxsum_surplus == 0:
        print("Maxsum is equal to house cost - all done!")
        return maxsum_bids

    # initialize the loop variables
    next_highest_bidders = assignments_dict_p.copy()
    next_highest_bids = maxsum_bids.copy()
    current_bids_total = maxsum
    current_surplus = maxsum_surplus

    while current_surplus > 0:
        
        for bed in beds:
            # print(f"Processing bed: {bed}...")
            
            # is there a lower bid?
            if next_highest_bids[bed] > bids_df_p[bed].min():
                
                next_highest_bidder_info = bids_df[bed].where(lambda bid: bid < next_highest_bids[bed]).dropna().sort_values(ascending=False)[[0]]
                next_highest_bidder = next_highest_bidder_info.index[0]
                next_highest_bid = next_highest_bidder_info.item()
                # print(f"Next highest bidder: {next_highest_bidder}")
                # print(f"Next highest bid: {next_highest_bid}")
                      
                next_highest_bidders[bed] = next_highest_bidder
                next_highest_bids[bed] = next_highest_bid
            else:
                pass
                # print("No lower bidder")
            
            diffs_from_maxsum[bed] = maxsum_bids[bed] - next_highest_bids[bed]
        
        current_bids_total = get_bids_total(get_bids_from_assignments(bids_df_p, next_highest_bidders))
        current_surplus = current_bids_total - house_cost_p
        diffs_from_maxsum_total = get_bids_total(diffs_from_maxsum)
        # print(f"Diffs from maxsum total: {diffs_from_maxsum_total}")
        
        print(f"Done with loop. Current surplus: {current_surplus}\n")
        
        if current_surplus < 0:
            print(f"Surplus is {current_surplus}. Allocating proportionally...")
            
            
            for bed in beds:
                next_highest_bids[bed] = round(maxsum_bids[bed] - ((diffs_from_maxsum[bed] / diffs_from_maxsum_total) * float(maxsum_surplus)), 2)
                
            print("Found optimal bids!")
            print(next_highest_bids)
            return next_highest_bids
        elif current_surplus == 0:
            print("Landed on exactly zero surplus - found optimal bids!")
            return next_highest_bids


final_bids = calc_final_bid_prices(bids_df, assignments_dict, house_cost)

get_bids_total(final_bids)