#!/usr/bin/env python3

"""
Copyright 2024 Mainspring Research

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”),
to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute,
sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
IN THE SOFTWARE.
"""

import math
import sys

import pandas as pd
from matplotlib import pyplot as plt


# My apply lamda
def percOfTotal(value, total):
    return value / total


# My apply lamda
def currencyToFloat(currency):
    return float(currency.replace('$', ''))


# Main
def main(fName, oName):
    # Read the csv file
    df = pd.read_csv(fName)

    # 'Pending Activity has no current value, only changed.  So let's total them all up and add the sum to "CASH"
    pDF = df.loc[df['Symbol'] == 'Pending Activity']
    pending = 0.0
    pDF.set_index('Symbol', inplace=True)

    for i in pDF['Last Price Change']:
        amt = 0.0
        if type(i) is str:
            amt = float(i.replace('$', ''))
        elif type(i) is float:
            amt = i
        if math.isnan(amt):
            amt = 0.0
        amt = float(amt)
        if amt == 0.0:
            if type(i['Current Value']) is str:
                amt = i['Current Value'].replace('$', '')
            elif type(i['Current Value']) is float:
                amt = i['Current Value']
        pending += float(amt)

    # BROKERAGELINK account has the total, and then still lists the individual investments, so remove it.
    df = df[df['Description'] != 'BROKERAGELINK']

    # We only need symbol and current value
    df = df.filter(['Symbol', 'Description', 'Current Value'])

    # Remove the pending activity rows
    df = df[df['Symbol'] != 'Pending Activity']

    # Get rid of any remaining rows that don't have a current value
    df = df[df['Current Value'].notnull()]

    # If any symbols are blank (like RHRP) then change it to *CASH**
    df['Symbol'] = df['Symbol'].fillna('*CASH**')

    # Use a lambda to quickly convert string dollar figures to a float
    df['Current Value'] = df.apply(lambda row: currencyToFloat(row['Current Value']), axis=1)

    # Add "pending' cash row back in
    # Because the indexes may not be sequential, we can't use df.loc[len(df.index)] until we reset the index
    df = df.reset_index(drop=True)
    df.loc[len(df.index)] = ['Pending**', 'Pending cash', pending]

    total = float(df.sum().loc['Current Value'])

    # Change all cash rows to "CASH"
    for index in df.index:
        if '**' in df.loc[index]['Symbol']:
            df.at[index, 'Symbol'] = '*CASH*'
            df.at[index, 'Description'] = 'Money Market'

    # Change all bond and CD rows to cash (they always have a '%' sign in them)
    for index in df.index:
        if '%' in df.loc[index]['Description']:
            df.at[index, 'Symbol'] = 'Fixed Income'
            df.at[index, 'Description'] = 'Bonds and CDs'

    # Now sum all common symbols - "reset_index" ensures that we retain all our index columns
    df = df.groupby(['Symbol', 'Description']).sum().reset_index()

    # Get the portfolio total
    total = float(df.sum().loc['Current Value'])

    # Now get the percent of the total
    df['Perc of total'] = df.apply(lambda row: percOfTotal(row['Current Value'], total), axis=1)

    # We could format it here, or just do it when we use the JSON file
    # df['Perc of total'] = df['Perc of total'].map('{:.2f}'.format)
    df = df.round(4)
    df = df.sort_values(by='Perc of total', ascending=False)

    # Create a dictionary for the pie chart
    pieDict = df.to_dict(orient='index')
    labels = []
    perc = []
    for i in pieDict:
        labels.append(pieDict[i]['Symbol'])
        perc.append(pieDict[i]['Perc of total'])

    # Create pie chart
    # Creating plot
    # fig = plt.figure(figsize=(12, 10), tight_layout=True)
    plt.figure(figsize=(15, 15))
    plt.rcParams.update({'font.size': 18})
    plt.pie(perc, labels=labels, autopct='{:.2f}%'.format)
    # plt.show()
    plt.savefig('{}.{}'.format(oName, 'png'), dpi='figure')

    # Convert to a JSON buffer
    jsonBuff = df.to_json(orient='records', indent=4, index=True)

    # And write it
    f = open('{}.json'.format(oName), 'w')
    f.write(jsonBuff)
    f.close()

    # Write as an Excel file
    df.to_excel('{}.xlsx'.format(oName))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
