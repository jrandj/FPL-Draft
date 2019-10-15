import requests
import pandas as pd
import config
from tabulate import tabulate
pd.options.mode.chained_assignment = None  # default='warn'


# Import data from draft.premierleague.com and members.fantasyfootballscout.co.uk
def import_data(myLeague):
    url = "https://draft.premierleague.com/api/league/" + str(myLeague) + "/element-status"
    r1 = requests.get(url=url)
    r2 = requests.get(url='https://draft.premierleague.com/api/bootstrap-static')
    s1 = requests.session()
    s1.post('https://members.fantasyfootballscout.co.uk/',
            data={'username': config.login['username'], 'password': config.login['password'], 'login': '>+Log+In'})
    r3 = s1.get('https://members.fantasyfootballscout.co.uk/projections/six-game-projections/')
    fplAvailabilityData = r1.json()
    fplPlayerData = r2.json()
    projectionsData = pd.read_html(r3.content)
    return fplAvailabilityData, fplPlayerData, projectionsData


# Remove unicode characters so that names can be compared across fplPlayerData and projectionsData
def strip_unicode(myString):
    myString = myString.translate(str.maketrans({'í': 'i', 'ï': 'i', 'ß': 's', 'á': 'a', 'ä': 'a', 'é': 'e', 'ñ': 'n',
                                                 'ć': 'c', 'š': 's', 'Ö': 'o', 'ö': 'o', 'ó': 'o', 'ø': 'o', 'ü': 'u'}))
    return myString


# Modify projectionsData so that the key matches 1-1 to fplPlayerData when we merge
def clean_projections(projectionsData):
    projectionsData[0]['Team'].loc[projectionsData[0]['Team'] == 'BRI'] = 'BHA'
    projectionsData[0]['Team'].loc[projectionsData[0]['Team'] == 'SOT'] = 'SOU'
    projectionsData[0]['Team'].loc[projectionsData[0]['Team'] == 'WHM'] = 'WHU'
    projectionsData[0]['Pos'].loc[projectionsData[0]['Pos'] == 'GK'] = 'GKP'
    return projectionsData


# Find available players who have a better six game projection than my players
def find_candidates(fplPlayerData, projectionsData):
    df = pd.DataFrame.from_dict(fplPlayerData['elements'])
    sixGameProjection = projectionsData[0].columns.values[-2]
    # NOTE: Need to get the merge to be 1-1
    projectionsData = clean_projections(projectionsData)
    df1 = df.merge(projectionsData[0], left_on=['web_name_clean', 'team_name', 'position_name'],
                   right_on=['Name', 'Team', 'Pos'])
    d1 = df1.to_dict(orient='records')

    for i in range(len(d1)):
        candidates = {}
        sorted_candidates = {}
        if d1[i]['selected'] == 'Yes':
            for j in range(len(d1)):
                # NOTE: The GW column names will change, need to fix
                if (d1[j][sixGameProjection] > d1[i][sixGameProjection]) and (d1[i]['Pos'] == d1[j]['Pos']) and \
                        (d1[j]['selected'] == 'No') and (d1[j]['available'] == 'Yes'):
                    candidates[d1[j]['web_name']] = d1[j][sixGameProjection]
            sorted_candidates = sorted(candidates.items(), key=lambda x: x[1], reverse=True)
            d1[i]['candidates'] = sorted_candidates
        fplPlayerData['elements'] = d1
    return fplPlayerData


# Join data from fplAvailabilityData and myTeam into fplPlayerData
def consolidate_data(fplAvailabilityData, fplPlayerData, myTeam):
    for i in range(len(fplPlayerData['elements'])):
        fplPlayerData['elements'][i]['web_name_clean'] = strip_unicode(fplPlayerData['elements'][i]['web_name'])
        fplPlayerData['elements'][i]['selected'] = 'No'
        fplPlayerData['elements'][i]['available'] = 'No'

        for j in fplPlayerData['teams']:
            if fplPlayerData['elements'][i]['team'] == j['id']:
                fplPlayerData['elements'][i]['team_name'] = j['short_name']

        for j in fplPlayerData['element_types']:
            if fplPlayerData['elements'][i]['element_type'] == j['id']:
                fplPlayerData['elements'][i]['position_name'] = j['singular_name_short']

        for j in fplAvailabilityData['element_status']:
            if fplPlayerData['elements'][i]['id'] == j['element']:
                if j['owner'] == myTeam:
                    fplPlayerData['elements'][i]['selected'] = 'Yes'
                if fplPlayerData['elements'][i]['status'] != 'u' and j['owner'] is None:
                    fplPlayerData['elements'][i]['available'] = 'Yes'

    return fplPlayerData


# Print available players with a higher projected score against my team and their projected score
def print_candidates(fplPlayerData, projectionsData):
    myTeam = []
    printList = []
    sixGameProjection = projectionsData[0].columns.values[-2]

    for i in range(len(fplPlayerData['elements'])):
        if fplPlayerData['elements'][i]['selected'] == 'Yes':
            myTeam.append(fplPlayerData['elements'][i])

    for i in myTeam:
        printDict = {k: v for k, v in i.items() if
                     k in ['web_name', 'position_name', 'team_name', 'candidates', sixGameProjection]}
        printList.append(printDict)

    sortedPrintList = sorted(printList, key=lambda x: (x['position_name'],
                                                       x['team_name'], x['web_name'], x[sixGameProjection]))
    print(tabulate(sortedPrintList, headers="keys", tablefmt="rst"))
    return


# Get team ID
def get_team(myLeague, myTeamName):
    url = "https://draft.premierleague.com/api/league/" + str(myLeague) + "/details"
    r1 = requests.get(url=url)
    leagueData = r1.json()
    for i in leagueData['league_entries']:
        if i['entry_name'] == myTeamName:
            myTeam = i['entry_id']
    return myTeam


def main():
    # REPLACE with own values ##########################################################################################
    myLeague = 48188
    myTeamName = "wearetherunnersup"
    ####################################################################################################################
    myTeam = get_team(myLeague, myTeamName)
    fplAvailabilityData, fplPlayerData, projectionsData = import_data(myLeague)
    fplPlayerData = consolidate_data(fplAvailabilityData, fplPlayerData, myTeam)
    fplPlayerData = find_candidates(fplPlayerData, projectionsData)
    print_candidates(fplPlayerData, projectionsData)


main()
