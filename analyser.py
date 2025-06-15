try:
    from lxml import html
    import mwxml
    import mysql.connector
    from os import stat, listdir, path, getcwd
    from pymenu import select_menu, Menu
    from time import sleep
    import getpass
    import datetime
except ImportError as e:
    print("Failed importing required modules. Did you install requirement.txt?")
    print("Error message:", e.msg)
    exit()

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

def ui_progress_add(num):
    global progress
    progress += num

def ui_progress_print(i):
    global progress
    global max_progress
    print(f"Words Processed: {i}. Progress: {progress * 100 / max_progress}%", end="\r")

def ui_handle_too_long_words(dbcursor, wordtable, max_length):
    options = [
        f"Resize mysql database column words to varchar({max_length})",
        "Write too long words to a seperate .txt file"
    ]
    selection = select_menu.create_select_menu(options,
        "Analysis is almost complete!\nTurns out some words where too long for mysql column words."
    )
    if selection == options[0]:
        print(f"Resizing database column to {max_length}")
        dbcursor.execute("alter table " + wordtable + " modify column word varchar(%s)", (max_length,))
        return None
    elif selection == options[1]:
        return ui_get_file(getcwd())

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

def validate(character):
    return (
        ord('a') <= ord(character) <= ord('z') or
        ord('A') <= ord(character) <= ord('Z')
    )

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
            yield revision.text

def parser():
    for text in text_loader():
        startid = 0
        for endid, character in enumerate(text):
            if not validate(character):
                if startid != endid:
                    yield text[startid:endid]
                startid = endid + 1
    # If article ends with a word (not a symbol)
    if (startid != endid + 1):
        yield text[startid:endid]

dump = None
db = None
wordtable = None
dbcursor = None
max_progress = None
progress = 0
try:
    def main():
        starttime = datetime.datetime.now()
        global dump
        global db
        global wordtable
        global dbcursor
        global max_progress
        global i
        dumppath, dump = ui_get_dump(getcwd())
        max_progress = stat(dumppath).st_size
        db = ui_connect_database()
        dbcursor = db.cursor()
        wordtable = ui_get_table(dbcursor)
        cache = dict()
        toolongwords = dict()
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
        
        dbcursor.execute("describe " + wordtable)
        for column, valuetype, _, _, _, _ in dbcursor:
            if column == "word":
                mysql_word_limit = int(valuetype[8:-1])
                dbcursor.fetchall()
                break
        cache_length = len(cache)
        if largestword > mysql_word_limit:
            too_long_words_file = ui_handle_too_long_words(dbcursor, wordtable, largestword)
            if too_long_words_file is None:
                # Handled with resize
                print("Resized Completed! Dumping cache to database...")
                for i, (word, times) in enumerate(cache.items()):
                    dbcursor.execute("insert into " + wordtable + " (word, times) values (%s, %s)", (word, times))
                    print(f"Progress: {i}/{cache_length}. {i * 100 / cache_length}% Completed!", end="\r")
            else:
                # Handled with file
                print("File Opened! Dumping cache to database...")
                for i, (word, times) in enumerate(cache.items()):
                    if (len(word) > mysql_word_limit):
                        too_long_words_file.write(f"{word} {times}")
                    else:
                        dbcursor.execute("insert into " + wordtable + " (word, times) values (%s, %s)", (word, times))
                    print(f"Progress: {i}/{cache_length}. {i * 100 / cache_length}% Completed!", end="\r")
        else:
            # No need to handle
            print("No word exceeds the maximum length limit. Dumping cache to database...")
            for i, (word, times) in enumerate(cache.items()):
                dbcursor.execute("insert into " + wordtable + " (word, times) values (%s, %s)", (word, times))
                print(f"Progress: {i}/{cache_length}. {i * 100 / cache_length}% Completed!", end="\r")
        db.commit()
        endtime = datetime.datetime.now()
        print(f"Analysis Ended! Started at: {starttime}. Ended at: {endtime}")
except KeyboardInterrupt:
    print("Recieved ctrl + c. Exiting...")
    if ui_yes_or_no("Keep words found until this point?"):
        print("Commiting changes...")
        db.commit()
    else:
        print("Rolling back changes...")
        db.rollback()

if __name__ == '__main__':
    main()