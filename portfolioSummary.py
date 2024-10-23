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

import numpy
import pandas as pd
from matplotlib import pyplot as plt
from dateutil.parser import parse


# My apply lamda
def percOfTotal(value, total):
    return value / total


# My apply lamda
def currencyToFloat(currency, default=None):
    if default is not None and type(currency) is str and len(currency) == 0:
        if type(default) is str:
            return float(default.replace('$', '').replace(',', ''))
        else:
            return default
    elif currency is numpy.nan:
        return default
    else:
        if '--' in currency:
            print('One of your equities has not yet been completely settled and the \n'
                  '"Total Gain/Loss Dollar" and/or "Cost Basis Total" is not yet available.\n'
                  'When this information becomes available the result will be more accurate.')
            return default
        return float(currency.replace('$', '').replace(',', ''))


# See if the string contains a date
def checkForDate(desc):
    dList = desc.split(' ')
    hasDate = False
    for d in dList:
        try:
            parse(d)
            hasDate = True
            break
        except ValueError:
            pass

    return hasDate


# Main
def main(fName, oDir):
    # Extract base file name
    if fName[-4:] != '.csv':
        print('Input file must have a csv extension')
        exit(-1)
    fBaseName = fName[:len(fName)-4]
    i = fBaseName.rfind('/')
    if i != -1:
        fBaseName = fBaseName[i + 1:]

    # Create full path for output
    oName = oDir
    if oName[len(oName) - 1] != '/':
        oName += '/'
    oName += fBaseName

    # Read the csv file
    df = pd.read_csv(fName)

    # 'Pending Activity has no current value, only changed.  So let's total them all up and add the sum to "CASH"
    pDF = df.loc[df['Symbol'] == 'Pending Activity']
    pending = 0.0
    pDF.set_index('Symbol', inplace=True)

    for iX, iRow in pDF.iterrows():
        i = iRow['Last Price Change']
        amt = 0.0
        if type(i) is str:
            amt = currencyToFloat(i)
        elif type(i) is float:
            amt = i
        if math.isnan(amt):
            amt = 0.0
        amt = float(amt)
        if amt == 0.0:
            if type(iRow['Current Value']) is str:
                amt = currencyToFloat(iRow['Current Value'])
            elif type(iRow['Current Value']) is float:
                amt = iRow['Current Value']
        pending += float(amt)

    # BROKERAGELINK account has the total, and then still lists the individual investments, so remove it.
    df = df[df['Description'] != 'BROKERAGELINK']

    # We only need symbol and current value
    # df = df.filter(['Symbol', 'Description', 'Quantity', 'Current Value', 'Cost Basis Total'])
    df = df.filter(['Symbol', 'Description', 'Quantity', 'Current Value', 'Cost Basis Total'])

    # Remove the pending activity rows
    df = df[df['Symbol'] != 'Pending Activity']

    # Get rid of any remaining rows that don't have a current value
    df = df[df['Current Value'].notnull()]

    # If any symbols are blank (like RHRP) then change it to *CASH**
    df['Symbol'] = df['Symbol'].fillna('*CASH**')

    # Get rid of nans
    df['Quantity'] = df['Quantity'].fillna(1.0)
    df['Cost Basis Total'] = df['Cost Basis Total'].fillna(df['Current Value'])

    # Use a lambda to quickly convert string dollar figures to a float
    df['Current Value'] = df.apply(lambda row: currencyToFloat(row['Current Value']), axis=1)
    # df['Last Price'] = df.apply(lambda row: currencyToFloat(row['Last Price'], 1.0), axis=1)
    df['Cost Basis Total'] = df.apply(lambda row: currencyToFloat(row['Cost Basis Total'], row['Current Value']), axis=1)

    # Add "pending" cash row back in
    # Because the indexes may not be sequential, we can't use df.loc[len(df.index)] until we reset the index
    df = df.reset_index(drop=True)
    df.loc[len(df.index)] = ['Pending**', 'Pending cash', 1.0, pending, pending]

    # Change all cash rows to "CASH"
    for index in df.index:
        if '**' in df.loc[index]['Symbol']:
            df.at[index, 'Symbol'] = '*CASH*'
            df.at[index, 'Description'] = 'Fixed Income'

    # Change all bond and CD rows to Fixed Income. They always have a '%' sign in them and a date.
    for index in df.index:
        if '%' in df.loc[index]['Description'] and checkForDate(df.loc[index]['Description']):
            if ' CD ' in df.loc[index]['Description']:
                df.at[index, 'Symbol'] = 'CDs'
            else:
                df.at[index, 'Symbol'] = 'Bonds'
            df.at[index, 'Description'] = 'Fixed Income'

    # Now sum all common symbols - "reset_index" ensures that we retain all our index columns
    df = df.groupby(['Symbol', 'Description']).sum().reset_index()

    # Get the portfolio total
    total = float(df.sum().loc['Current Value'])

    # *CASH*, CDs, and Fixed Income are special cases
    df.loc[df['Description'] == 'Fixed Income', 'Quantity'] = 1.0
    # df.loc[df['Description'] == 'Fixed Income', 'Last Price'] = df['Current Value']

    df.insert(3, 'Last Price', df['Current Value'] / df['Quantity'])

    # Figure out average cost bases
    df.insert(5, 'Average Cost Basis', df['Cost Basis Total'] / df['Quantity'])

    # Figure out Gain-Loss
    df['Gain-Loss'] = df['Current Value'] - df['Cost Basis Total']

    # Figure out Gain-Loss %
    df['Gain-Loss %'] = df['Gain-Loss'] / df['Cost Basis Total']

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
    jsonBuff = df.to_json(orient='records', indent=4)

    # And write it
    f = open('{}.json'.format(oName), 'w')
    f.write(jsonBuff)
    f.close()

    stock_current = df.loc[(df['Description'] != 'Fixed Income'), 'Current Value'].sum()
    stock_cost_basis = df.loc[(df['Description'] != 'Fixed Income'), 'Cost Basis Total'].sum()
    stock_gain_loss = stock_current - stock_cost_basis
    stock_gl_perc = stock_gain_loss / stock_cost_basis if stock_cost_basis > 0.0 else 0.0

    df.loc[len(df.index)] = ['', 'Total (not incl interest and dividends)', '', '', df['Current Value'].sum(), '',
                             df['Cost Basis Total'].sum(), df['Gain-Loss'].sum(), '', '']

    df['Gain-Loss %'] = df['Gain-Loss'] / df['Cost Basis Total']

    # Stock percentage of total
    stockPercOfTtotal = stock_current / total
    df.loc[len(df.index)] = ['', 'Total stocks', '', '', stock_current, '',
                             stock_cost_basis, stock_gain_loss, stock_gl_perc, stockPercOfTtotal]

    # Fixed income totals
    fixed_cost_basis = df.loc[(df['Description'] == 'Fixed Income'), 'Cost Basis Total'].sum()
    fixed_current = df.loc[(df['Description'] == 'Fixed Income'), 'Current Value'].sum()
    fixed_gain_loss = fixed_current - fixed_cost_basis
    fixed_gl_perc = fixed_gain_loss / fixed_cost_basis if fixed_cost_basis > 0.0 else 0.0
    df.loc[len(df.index)] = ['', 'Total fixed income (not incl int. and div.)', '', '', total - stock_current, '',
                             fixed_cost_basis, fixed_gain_loss, fixed_gl_perc, 1.0 - stockPercOfTtotal]

    # Write as an Excel file
    with pd.ExcelWriter('{}.xlsx'.format(oName), engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Investment Summary", index=False)
        workbook = writer.book
        worksheet = writer.sheets['Investment Summary']
        format1 = workbook.add_format({"num_format": "$#,##0.00"})
        format2 = workbook.add_format({"num_format": "0.00%"})
        worksheet.set_column(1, 1, 34, format1)
        worksheet.set_column(3, 7, 18, format1)
        worksheet.set_column(8, 9, 14, format2)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("USAGE: portfolioSummary.py input_file output_directory")
    main(sys.argv[1], sys.argv[2])
