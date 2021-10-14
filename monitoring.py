'''The script that starts the main DEHC application.'''

import argparse
import sys

import apps.ems as ae
import mods.database as md
import mods.log as ml

import mods.dehc_hardware as hw

import mariadb
import sys

import pprint
import time
from datetime import datetime

# ----------------------------------------------------------------------------


def count_people(indata):
    total_people = 0
    for key, data in indata.items():
        #print(type(data))
        #pprint.pprint(data)
        if isinstance(data, dict):
            total_people += count_people(data)
        else:
            if key[0:6] == "Person":
                total_people += 1
    return total_people

def list_people(indata,result_list):
    for key, data in indata.items():
        #print(type(data))
        #pprint.pprint(data)
        if isinstance(data, dict):
            list_people(data, result_list)
        else:
            if key[0:6] == "Person":
                result_list.append(key)
    #return  result_list

if __name__ == "__main__": # Multiprocessing library complains if this guard isn't used
    
    parser = argparse.ArgumentParser(description='Starts the Digital Evacuation Handling Center')
    parser.add_argument('-a','--auth', type=str, default="db_auth.json", help="relative path to database authentication file", metavar="PATH")
    parser.add_argument('-b','--book', type=str, default="bookmarks.json", help="relative path to EMS screen bookmarks", metavar="PATH")
    parser.add_argument('-l','--logg', type=str, default="WARNING", help="minimum level of logging messages that are printed: DEBUG, INFO, WARNING, ERROR, CRITICAL, or NONE", choices=["DEBUG","INFO","WARNING","ERROR","CRITICAL","NONE"], metavar="LEVL")
    parser.add_argument('-n','--name', type=str, default="dehc", help="which database namespace to use", metavar="NAME")
    parser.add_argument('-s','--sche', type=str, default="db_schema.json", help="relative path to database schema file", metavar="PATH")
    args = parser.parse_args()

    # ----------------------------------------------------------------------------

    logger = ml.get(name="Main", level=args.logg)
    logger.debug("Monitoring has started.")
    db = md.DEHCDatabase(config=args.auth, level=args.logg, namespace=args.name, schema=args.sche, quickstart=True)

 #quit()
    # Connect to MariaDB Platform
    try:
        conn = mariadb.connect(
            user="dehc_admin",
            password="Creative",
            host="10.8.0.1",
            port=3306,
            database="vps_dehc"            
        )
        print("Mariadb Connected")
    except mariadb.Error as e:
        print(f"Error connecting to MariaDB Platform: {e}")
        sys.exit(1)

    # Get Cursor
    cursor = conn.cursor()

    all_containers = db.container_children_all_dict(db.items_query(cat="Evacuation")[0]['_id'])
    #pprint.pprint(all_containers)
    total_count = count_people(all_containers)
    print()
    stations = db.items_list(cat="Station")
    #pprint.pprint(stations)
    containers_current_people = {}
    while True:
        print("Time %s "  % (datetime.now()))
        for station in stations:
            containers = db.container_children_all_dict(station['_id'])
            #cont_ppl = count_people(containers)
            id_list = [] #note this is passed to and mucked with by the list_people function
            ppl_leaving = 0
            ppl_entering = 0
            list_people(containers,id_list)
            if station['_id'] not in containers_current_people:
                containers_current_people[station['_id']] = list()
            else:
                #need to skip counting everybody as entering on the first run through
                for current_person in containers_current_people[station['_id']]:
                    if current_person not in id_list:
                        print("Leaving : " + current_person)
                        ppl_leaving += 1

                for current_person in id_list:
                    if current_person not in containers_current_people[station['_id']]:
                        print("Entering : " + current_person)
                        ppl_entering += 1                

            containers_current_people[station['_id']] = id_list

            cont_ppl = len(id_list)
            #pprint.pprint(id_list)
            print("Id %s Name : %s Qty %s : Enter %s : Leave %s" % (station['_id'], station['Display Name'], cont_ppl,ppl_entering,ppl_leaving))

            try:
                cursor.execute(
                "INSERT INTO container_stats (record_time,container_id,container_name,item_total) VALUES (now(),?,?,?)", 
                (station['_id'],station['Display Name'],cont_ppl))
            except mariadb.Error as e: 
                print(f"Error: {e}")
        #conn.commit()        

        time.sleep(10)
        #input()