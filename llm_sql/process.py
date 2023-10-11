import os
import argparse
import sqlite3
import pandas as pd
from utils import *


parser = argparse.ArgumentParser(description='A python script to process the doctors file and launch a gradio app')

#Define the command-line arguments
parser.add_argument('file', type=str, help='path to the csv file to be processed with the doctor data')

#Parse the command-line arguments
args = parser.parse_args()


df = pd.read_csv(args.file, index_col = 0)

clean_df = pd.DataFrame()
clean_df["profile_id"] = df.Physician_Profile_ID
clean_df["name"] = df.Physician_First_Name + " " + df.Physician_Middle_Name + " " + df.Physician_Last_Name

clean_df["state"] = df.Recipient_State.apply(abbrevs.get)
clean_df["city"] = df.Recipient_City
clean_df["amount_invested"] = df.Total_Amount_Invested_USDollars

doctor_specialities = df.set_index("Physician_Profile_ID").Physician_Specialty.apply(lambda x : x.split("|"))

all_specialities = set()
for speciality_list in doctor_specialities:
    for s in speciality_list:
        all_specialities.add(s)

vectors = []
for i, specialities in enumerate(doctor_specialities):
    vectors.append({name : name in specialities for name in all_specialities})

specialities_df = pd.DataFrame(vectors)

clean_df = pd.concat([clean_df, specialities_df], axis = 1)

new_name = args.file.removesuffix(".csv") + "_transformed.csv"
clean_df.to_csv(new_name)

# Connect to the SQLite database (it will create a new one if it doesn't exist)
conn = sqlite3.connect('gradio/doctors.db')

# Replace 'table_name' with the name of the table you want to create in the database
table_name = 'Doctors'

# Use the `to_sql` method to save the DataFrame to the database
clean_df.to_sql(table_name, conn, if_exists='replace', index=False)
print("Data processed succesfully")