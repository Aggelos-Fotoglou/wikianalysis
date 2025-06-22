try:
    from lxml import html
    import mwxml
    from os import stat, listdir, path, getcwd
    from pymenu import select_menu, Menu
    from time import sleep
    import getpass
    import datetime
    import sqlite3
    import mysql.connector
except ImportError as e:
    print("Failed importing required modules. Did you install requirement.txt?")
    print("Error message:", e.msg)
    exit()

# Languages
def validate_gr(character):
    return (
        ord('Α') <= ord(character) <= ord('Ρ') or
        ord('Σ') <= ord(character) <= ord('ώ') or
        character in ['Ά', 'Έ', 'Ί', 'Ή', 'Ύ', 'Ό', 'Ώ'] or
        character in ['ά', 'έ', 'ί', 'ή', 'ύ', 'ό', 'ώ'] or
        character in ['Ϊ', 'Ϋ'] or
        character in ['ϊ', 'ϋ', 'ΐ', 'ΰ'] or
        ord('ἀ') <= ord(character) <= ord('ᾼ') or
        ord('ῂ') <= ord(character) <= ord('ῌ') or
        ord('ῐ') <= ord(character) <= ord('Ί') or
        ord('ῠ') <= ord(character) <= ord('Ῥ') or
        ord('ῲ') <= ord(character) <= ord('ῼ')
    )

def validate_de(character):
    return (
        ord('a') <= ord(character) <= ord('z') or
        ord('A') <= ord(character) <= ord('Z') or
        character in ['ö', 'Ö', 'ä', 'Ä', 'ü', 'Ü']
    )

def validate_en(character):
    return (
        ord('a') <= ord(character) <= ord('z') or
        ord('A') <= ord(character) <= ord('Z')
    )
wiki_language = {
    "enwiki": "English",
    "dewiki": "German",
    "elwiki": "Greek"
}
language_validator = {
    "English": validate_en,
    "German": validate_de,
    "Greek": validate_gr
}

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
        self.database = select_menu.create_select_menu([i[0] for i in self.cursor], 'Select a database:')
        self.cursor.execute("USE " + self.database)
        self.cursor.execute("show tables")
        self.table_name = select_menu.create_select_menu([i[0] for i in self.cursor], 'Select a table for the output data:')
    def execute(self, query, *args, **kwards):
        query = query.format(table=self.table_name)
        if not self.connection.is_connected():
            self.connection.reconnect()
            self.cursor.execute("USE " + self.database)
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
                self.execute("alter table {table} modify column word " + type_text)
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
        self.table_name = dump.site_info.dbname
        self.execute("CREATE TABLE {table} (word TEXT, times INTEGER)")
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
def ui_get_language():
    global language_validator
    global dump
    return select_menu.create_select_menu(language_validator.keys(), f"Seems like the programm does not know the language of {dump.site_info.dbname}. Languages with no special alphabetical characters cat use the English option. Please specifiy one of the following languages:")

def ui_get_file(dir, hidden=False):
    while True:
        if hidden:
            dlist = listdir(dir)
        else:
            dlist = [i for i in listdir(dir) if not i.startswith(".")]
        if not dir == "/":
            dlist.append(" <- Back ")
        dlist.append("< Create a new file here >")
        item = select_menu.create_select_menu(dlist, "Please select a file to open!\nDirectory Listing of " + dir)
        if item == " <- Back ":
            dir = path.dirname(dir)
        elif item == "< Create a new file here >":
            filename = input("Please insert the filename: ")
            filename = path.join(dir, filename)
            if path.isdir(filename):
                print(f"{filename} allready exists as a directory!")
                sleep(2)
                continue
            if path.isfile(filename):
                if not ui_yes_or_no(f"{filename} allready exists. Replace it?"):
                    continue
            try:
                return open(filename, "w")
            except Exception as e:
                print(f"Error opening file {filename}!")
                print(f"Error message: {e.msg}")
                sleep(2)
        else:
            dir = path.join(dir, item)
            if path.isfile(dir):
                try:
                    return open(dir, "w")
                except Exception as e:
                    print(f"Error opening file {filename}!")
                    print(f"Error message: {e.msg}")
                    sleep(2)
                    dir = path.dirname(dir)

def ui_get_dump(dir, hidden=False):
    while True:
        if hidden:
            dlist = listdir(dir)
        else:
            dlist = [i for i in listdir(dir) if not i.startswith(".")]
        if not dir == "/":
            dlist.append(" <- Back ")
        item = select_menu.create_select_menu(dlist, "Please select a database dump to open!\nDirectory Listing of " + dir)
        if item == " <- Back ":
            dir = path.dirname(dir)
        else:
            dir = path.join(dir, item)
            if path.isfile(dir):
                try:
                    dump = mwxml.Dump.from_file(open(dir, "rb"))
                    return (dir, dump)
                except Exception as e:
                    print("Unable to parse database dump!")
                    print("mwxml error | ", type(e).__name__, " | ",  e)
                    sleep(2)
                    dir = path.dirname(dir)

def ui_yes_or_no(question):
    while True:
        answer = input(question + " [y/n]:")
        if (answer in ["yes", "Yes", "YES", "y", "Y"]):
            return True
        elif (answer in ["no", "No", "NO", "n", "N"]):
            return False

def ui_progress_add(num):
    global progress
    progress += num

def ui_progress_print(i):
    global progress
    global max_progress
    print(f"Words Processed: {i}. Progress: {progress * 100 / max_progress}%", end="\r")

def ui_handle_too_long_words(database, max_length):
    options = [
        f"Resize mysql database column words to varchar({max_length})",
        "Write too long words to a seperate .txt file"
    ]
    selection = select_menu.create_select_menu(options,
        "Analysis is almost complete!\nTurns out some words where too long for mysql column words."
    )
    if selection == options[0]:
        print(f"Resizing database column to {max_length}")
        database.resize(max_length)
        return None
    elif selection == options[1]:
        return ui_get_file(getcwd())

def text_loader():
    global dump
    for page in dump:
        for revision in page:
            if revision.text == None:
                continue
            try:
               ui_progress_add(revision.bytes)
            except Exception as e:
                print("Error incrementing progress counter:", e.msg, "Execution will continue normally...")
                pass
            text = revision.text
            text = text.replace("&lt;", "<")
            text = text.replace("&gt;", ">")
            text = html.fromstring(text).text_content()
            yield text

def parser():
    global language
    for text in text_loader():
        startid = 0
        for endid, character in enumerate(text):
            if not language_validator[language](character):
                if startid != endid:
                    yield text[startid:endid]
                startid = endid + 1
    # If article ends with a word (not a symbol)
    if (startid != endid + 1):
        yield text[startid:endid]

dump = None
max_progress = None
progress = 0
language = None
database = None
try:
    def main():
        starttime = datetime.datetime.now()
        global dump
        global max_progress
        global i
        global language
        global database

        backed_type = select_menu.create_select_menu(["mysql", "sqlite3"], "Please select the database type to use:")
        if backed_type == "mysql":
            database = mysql_abstractions()
        elif backed_type == "sqlite3":
            database = sqlite3_abstractions()

        dumppath, dump = ui_get_dump(getcwd())

        language_code = dump.site_info.dbname
        if language_code in wiki_language and wiki_language[language_code] in language_validator:
            language = wiki_language[language_code]
            print(f"Auto detected wiki language {language}")
        else:
            language = ui_get_language()
        max_progress = stat(dumppath).st_size

        database.connect() # Uses UI to connect the database backend
        cache = dict()
        lasti = 0
        largestword = 0
        for i, word in enumerate(parser()):
            if len(word) > largestword:
                largestword = len(word)
            try:
                cache[word] += 1
            except KeyError:
                cache[word] = 1
            if i - lasti > 100000:
                lasti = i
                ui_progress_print(i)

        db_word_limit = database.get_max_word_size()
        cache_length = len(cache)
        if largestword > db_word_limit:
            too_long_words_file = ui_handle_too_long_words(database, largestword)
            if too_long_words_file is None:
                # Handled with resize
                print("Resized Completed! Dumping cache to database...")
                for i, (word, times) in enumerate(cache.items()):
                    database.execute("insert into {table} (word, times) values (%s, %s)", (word, times))
                    print(f"Progress: {i}/{cache_length}. {i * 100 / cache_length}% Completed!", end="\r")
            else:
                # Handled with file
                print("File Opened! Dumping cache to database...")
                for i, (word, times) in enumerate(cache.items()):
                    if (len(word) > db_word_limit):
                        too_long_words_file.write(f"{word} {times}")
                    else:
                        database.execute("insert into {table} (word, times) values (%s, %s)", (word, times))
                    print(f"Progress: {i}/{cache_length}. {i * 100 / cache_length}% Completed!", end="\r")
        else:
            # No need to handle
            print("No word exceeds the maximum length limit. Dumping cache to database...")
            for i, (word, times) in enumerate(cache.items()):
                database.execute("insert into {table} (word, times) values (%s, %s)", (word, times))
                print(f"Progress: {i}/{cache_length}. {i * 100 / cache_length}% Completed!", end="\r")
        database.commit()
        endtime = datetime.datetime.now()
        print(f"Analysis Ended! Started at: {starttime}. Ended at: {endtime}")
except KeyboardInterrupt:
    print("Recieved ctrl + c. Exiting...")
    if ui_yes_or_no("Keep words found until this point?"):
        print("Commiting changes...")
        database.commit()
    else:
        print("Rolling back changes...")
        database.rollback()

if __name__ == '__main__':
    main()
