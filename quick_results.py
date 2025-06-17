from pymenu import select_menu
from openpyxl import Workbook
import mysql.connector
import sqlite3
import getpass
from os import path, getcwd

quick_reports = {
    "Number of all words": "select sum(times) from {table}",
    "Number of distinct words": "select count(word) from {table}",
    "Number of all words with length n for every n": "select sum(times) from {table} group py length(word)",
    "Number of distinct words with length n for every n": "select count(word) from {table} group by length(word)",
    "Number of all words starting with each letter": "select substr(word, 1, 1), sum(times) from {table} group by substr(word, 1, 1) order by substr(word, 1, 1) asc",
    "Number of distinct words starting with each letter": "select substr(word, 1, 1), count(times) from {table} group by substr(word, 1, 1) order by substr(word, 1, 1) asc",
    "Top 50 words in times found.": "select word, times from {table} order by times desc limit 50",
    "Top 50 longest words": "select word, times from {table} order by length(word) desc limit 50"
}

def ui_yes_or_no(question):
    while True:
        answer = input(question + " [y/n]:")
        if (answer in ["yes", "Yes", "YES", "y", "Y"]):
            return True
        elif (answer in ["no", "No", "NO", "n", "N"]):
            return False

class mysql_abstractions:
    text_sizes = (
        ("TINYTEXT", 255),
        ("TEXT", 65535),
        ("MEDIUMTEXT", 16777215),
        ("LONGTEXT", 4294967295)
    )
    def connect(self):
        while True:
            print("Mysql connection method:")
            if ui_yes_or_no("Use UNIX socket?") == True:
                socketpath = input("Insert the UNIX socket path (default: /run/mysqld/mysqld.sock): ")
                if socketpath == "":
                    socketpath = "/run/mysqld/mysqld.sock"
                username = input("Insert the username to use: ")
                try:
                    self.connection = mysql.connector.connect(
                        unix_socket=socketpath,
                        user=username,
                        password=None
                    )
                    break
                except mysql.connector.errors.Error as e:
                    print("Error connecting to mysql:")
                    print(e.msg)
            else:
                hostname = input("Insert the ip, hostname or url to the mysql server:")
                username = input("Insert the username to use:")
                password = getpass.getpass("Insert the password to use:")
                try:
                    self.connection = mysql.connector.connect(
                        host=hostname,
                        user=username,
                        password=password
                    )
                    break
                except mysql.connector.errors.Error as e:
                    print("Error connecting to mysql:")
                    print(e.msg)
        self.cursor = self.connection.cursor()
        self.cursor.execute("show databases")
        database = select_menu.create_select_menu([i[0] for i in self.cursor], 'Select a database:')
        self.cursor.execute("USE " + database)
        self.cursor.execute("show tables")
        self.table_name = select_menu.create_select_menu([i[0] for i in self.cursor], 'Select a table for the output data:')
    def execute(self, query, *args, **kwards):
        query = query.format(table=self.table_name)
        self.connection.ping(reconnect=True, attempts=3)
        self.cursor.execute(query, *args, **kwards)
    def commit(self):
        self.connection.commit()
    def rollback(self):
        self.connection.rollback()
    def get_max_word_size(self):
        self.execute("describe {table}")
        for column, valuetype, _, _, _, _ in self.cursor:
            if column == "word":
                word_limit = int(valuetype[8:-1])
                self.cursor.fetchall()
                return word_limit
    def resize(self, size):
        for type_text, max_size in self.text_sizes:
            if max_size > size:
                self.execute("alter table {table} modify column word {data_type}".format(data_type=type_text))
                break

class sqlite3_abstractions:
    def connect(self):
        filename = "wikianalysis.db"
        i = 2
        while True:
            if not path.exists(filename):
                print(f"sqlite3 db will be saved with file name {filename} in the script folder")
                break
            filename = f"wikianalysis({i}).db"
            i += 1
        self.connection = sqlite3.connect(filename)
        self.cursor = self.connection.cursor()
        self.cursor.execute(".tables")
        self.table_name = select_menu.create_select_menu([table for table in self.cursor], "Please select the sqlite3 table to use:")
    def execute(self, query, *args, **kwards):
        query = query.replace("%s", "?") # MySQL uses %s for sql-injection-safe values and sqlite uses ?
        self.cursor.execute(query.format(table=self.table_name),*args, **kwards)
    def commit(self):
        self.connection.commit()
    def rollback(self):
        self.connection.rollback()
    def get_max_word_size(self):
        return 1000000000 # Default text sqlite3 max size
    def resize():
        pass

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
    backed_type = select_menu.create_select_menu(["mysql", "sqlite3"], "Please select the database type to use:")
    if backed_type == "mysql":
        database = mysql_abstractions()
    elif backed_type == "sqlite3":
        database = sqlite3_abstractions()
    database.connect()
    workbook = Workbook()
    for i, label, checked in enumerate(ui_check_box(list(quick_reports.keys()))):
        if checked:
            print(f'Executing "{label}"...')
            worksheet = workbook.create_sheet(f"Sheet {i}")
            worksheet.append(label)
            database.execute(quick_reports[label])
            for row in database.cursor:
                worksheet.append(row)
    filename = "quick results.xlsx"
    i = 2
    while path.exists(filename):
        filename = f"quick results ({i}).xlsx"
        i += 1
    workbook.save(filename)

if __name__ == '__main__':
    main()