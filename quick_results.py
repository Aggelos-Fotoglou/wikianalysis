from pymenu import select_menu
from openpyxl import Workbook
import time
import mysql.connector
import getpass
from os import path, getcwd

quick_reports = {
    "Number of all words": "select sum(times) from {words_table}",
    "Number of distinct words": "select count(word) from {words_table}",
    "Number of all words with length n for every n": "select sum(times) from {words_table} group py length(word)",
    "Number of distinct words with length n for every n": "select count(word) from {words_table} group by length(word)",
    "Number of all words starting with each letter": "select substr(word, 1, 1), sum(times) from {words_table} group by substr(word, 1, 1) order by substr(word, 1, 1) asc",
    "Number of distinct words starting with each letter": "select substr(word, 1, 1), count(times) from {words_table} group by substr(word, 1, 1) order by substr(word, 1, 1) asc",
    "Top 50 words in times found.": "select word, times from {words_table} order by times desc limit 50",
    "Top 50 longest words": "select word, times from {words_table} order by length(word) desc limit 50"
}

def ui_yes_or_no(question):
    while True:
        answer = input(question + " [y/n]:")
        if (answer in ["yes", "Yes", "YES", "y", "Y"]):
            return True
        elif (answer in ["no", "No", "NO", "n", "N"]):
            return False

def ui_connect_database():
    while True:
        print("Mysql connection method:")
        if ui_yes_or_no("Use UNIX socket?") == True:
            socketpath = input("Insert the UNIX socket path (default: /run/mysqld/mysqld.sock): ")
            if socketpath == "":
                socketpath = "/run/mysqld/mysqld.sock"
            username = input("Insert the username to use: ")
            try:
                db = mysql.connector.connect(
                    unix_socket=socketpath,
                    user=username,
                    password=None
                )
                return db
            except mysql.connector.errors.Error as e:
                print("Error connecting to mysql:")
                print(e.msg)
        else:
            hostname = input("Insert the ip, hostname or url to the mysql server:")
            username = input("Insert the username to use:")
            password = getpass.getpass("Insert the password to use:")
            try:
                db = mysql.connector.connect(
                    host=hostname,
                    user=username,
                    password=password
                )
                return db
            except mysql.connector.errors.Error as e:
                print("Error connecting to mysql:")
                print(e.msg)

def ui_get_table(dbcursor):
    dbcursor.execute("show databases")
    database = str(select_menu.create_select_menu([i[0] for i in dbcursor], 'Select a database:'))
    dbcursor.execute("USE " + database)
    dbcursor.execute("show tables")
    table = select_menu.create_select_menu([i[0] for i in dbcursor], 'Select a table for the output data:')
    return table

def ui_check_box(labels):
    states = dict()
    for label in labels:
        states[label] = False
    while True:
        selection = select_menu.create_select_menu([('☑ ' if states[label] else '☐ ') + label for label in labels] + ["continue ->"], "Please select your options")
        if selection == "continue ->":
            return states
        selection = selection[2:]
        states[selection] = not states[selection]

def main():
    db = ui_connect_database()
    dbcursor = db.cursor()
    wordstable = ui_get_table(dbcursor)
    workbook = Workbook()
    for i, label, checked in enumerate(ui_check_box(list(quick_reports.keys()))):
        if checked:
            print(f'Executing "{label}"...')
            worksheet = workbook.create_sheet(f"Sheet {i}")
            worksheet.append(label)
            dbcursor.execute(quick_reports[label].format({"words_table": wordstable}))
            for row in dbcursor:
                worksheet.append(row)
    filename = "quick results.xlsx"
    i = 2
    while path.exists(filename):
        filename = f"quick results ({i}).xlsx"
        i += 1
    workbook.save(filename)

if __name__ == '__main__':
    main()