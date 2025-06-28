import sqlite3
from typing import Dict, List, Tuple
import pickle
import os
from models import get_embedding_model
from Params import DB_PATH

class DBManager:
    def __init__(self, db_path: str):
        self.setDatabase(db_path)

    def setDatabase(self, db_path : str):
        self.db_path = db_path
        self.db_name = os.path.splitext(os.path.basename(self.db_path))[0]
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.embedding_model = get_embedding_model()
        # New connected database
        if not os.path.isdir(f"history/databases/{self.db_name}"):
            os.makedirs(f"history/databases/{self.db_name}")
            self.schema = self.loadSchema()
            self.primary_keys, self.foreign_keys = self.loadRelationships(self.schema)
            self.embeddings = self.schema
            self.save()
        else: # was connected before
            self.load()


    def loadSchema(self) -> Dict[str, Dict[str, str]]:
        """
        Returns schema as:
        {
            "table1": 
            {
                "column1": "desc1",
                "column2": "desc2",
                ...
            },
            ...
        }
        """
        schema = {}
        # Get all user-defined tables (ignore internal SQLite tables)
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [row["name"] for row in self.cursor.fetchall()]

        for table in tables:
            self.cursor.execute(f"PRAGMA table_info('{table}');")
            columns = self.cursor.fetchall()

            column_info = {}
            for col in columns:
                col_name = col["name"]
                column_info[col_name] = "" # description will be (optionally) set later
            
            schema[table] = column_info

        return schema
    
    def loadRelationships(self, schema: Dict[str, Dict[str, str]]) -> Tuple[Dict[str, List[str]], Dict[str, List[Tuple[str, str]]]]:
        primary_keys: Dict[str, List[str]] = {}
        foreign_keys: Dict[str, List[Tuple[str, str]]] = {}

        for table in schema:
            # Get primary key
            self.cursor.execute(f"PRAGMA table_info('{table}');")
            columns = self.cursor.fetchall()
            if table not in primary_keys:
                primary_keys[table] = []
            for col in columns:
                if col["pk"] == 1:
                    primary_keys[table].append(col["name"])
            
        for table in schema:           
            # Get foreign key relationships
            self.cursor.execute(f"PRAGMA foreign_key_list('{table}');")
            fks = self.cursor.fetchall()
            foreign_keys[table] = []
            for fk in fks:
                from_col = fk["from"]
                to_table = fk["table"]
                to_col = fk["to"]
                foreign_keys[table].append((f"{table}.{from_col}", f"{to_table}.{to_col}"))

        return primary_keys, foreign_keys
    
    def setDescription(self, table_name : str, column_name : str, desc: str):
        self.schema[table_name][column_name] = desc

    def embedDescription(self, table, column, desc):
        if desc != "":
            desc_emb = self.embedding_model.encode(desc, convert_to_tensor=True)
            self.embeddings[table][column] = desc_emb
    
    def saveDescToFile(self):
        with open(f'history/databases/{self.db_name}/embeddings.pkl', 'wb') as f:
            pickle.dump(self.embeddings, f)

    def loadDescFromFile(self):
        with open(f'history/databases/{self.db_name}/embeddings.pkl', 'rb') as f:
            self.embeddings = pickle.load(f)

    def saveSchemaToFile(self):
        with open(f"history/databases/{self.db_name}/schema.pkl", 'wb') as f:
            pickle.dump((self.schema, self.primary_keys, self.foreign_keys), f)

    def loadSchemaFromFile(self):
        with open(f"history/databases/{self.db_name}/schema.pkl", 'rb') as f:
            self.schema, self.primary_keys, self.foreign_keys = pickle.load(f)

    def save(self):
        self.saveSchemaToFile()
        self.saveDescToFile()
    
    def load(self):
        self.loadSchemaFromFile()
        self.loadDescFromFile()
    
if __name__ == '__main__':
    db_manager = DBManager(DB_PATH)
    print(db_manager.schema)
    print(db_manager.primary_keys)
    print(db_manager.foreign_keys)
    # desc_map = {
    # "lists": {
    #           "user_id": "ID related to the user who created the list.",
    #           "list_id": "ID of the list on Mubi",
    #           "list_title": "Name of the list",
    #           "list_movie_number": "Number of movies added to the list",
    #           "list_update_timestamp_utc": "Last update timestamp for the list",
    #           "list_creation_timestamp_utc": "Creation timestamp for the list",
    #           "list_followers": "Number of followers on the list",
    #           "list_url": "URL to the list page on Mubi",
    #           "list_comments": "Number of comments on the list",
    #           "list_description": "List description made by the user",
    #           "list_cover_image_url": "",
    #           "list_first_image_url": "",
    #           "list_second_image_url": "",
    #           "list_third_image_url": "",
    #         },

    # "lists_users": {
    #           "user_id": "ID related to the user who created the list.",
    #           "list_id": "ID of the list on Mubi",
    #           "list_update_date_utc": "Last update date for the list",
    #           "list_create_date_utc": "Creation date for the list",
    #           "user_trialist": "whether the user was a tralist when he created the list ",
    #         }
    # }

    
