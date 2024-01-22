# Fidelity Portfolio Summary

The Fidelity Portfolio page allows you to download positions for all your accounts.

This program organizes and summarizes your positions across all of these accounts.  For example, it will 
summarize all cash and money market entries (including "Pending Activity") into "\*CASH\*" and all bonds and CDs 
into "Fixed Income".  It will then aggregate the stocks positions from all accounts so you can see your total
position in each stock.
 
## Program

### Dependencies

As you can see, the script is named 'portfolioSummary.py'. It has been tested on Python 3.10 but should work on Python 3.8+
There is a requirements.txt file that you can use to install the required modules, pandas and matplotlib.

### Usage

Log into your Fidelity account and select "All accounts" on the left, and then
click on "Positions".  On the right you'll see a download icon to download a CSV
file.


Then run: 

    python3 portfolioSummary.py downloaded_fidelity_portfolio.cxv output_directory  

### Output

Three files are created: a spreadsheet (xlsx), a piechart (png), and a JSON file that has the same values
as the spreadasheet.

Note that at this time the spreadsheet columns are not formatted.  In the future I may use the pandas "ExcelWriter"
capability to pretty the spreadsheet up.  

