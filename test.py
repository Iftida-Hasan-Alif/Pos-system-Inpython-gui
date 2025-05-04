import sqlite3
import pandas as pd

def show_all_tables(db_path='pos_system.db'):
    """Display all tables and their contents in the terminal"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get list of all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if not tables:
            print("No tables found in the database.")
            return
            
        print("\n" + "="*50)
        print(f"DATABASE: {db_path}")
        print("="*50)
        
        for table in tables:
            table_name = table[0]
            print(f"\nTABLE: {table_name.upper()}")
            print("-"*50)
            
            # Get and display table data
            df = pd.read_sql(f"SELECT * FROM {table_name};", conn)
            
            if df.empty:
                print("(Table is empty)")
            else:
                # Display all rows without truncation
                with pd.option_context('display.max_rows', None,
                                     'display.max_columns', None,
                                     'display.width', None,
                                     'display.max_colwidth', 20):
                    print(df.to_string(index=False))
            
            print("\n" + "="*50)
            
        conn.close()
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == '__main__':
    show_all_tables()  # Uses default 'pos_database.db'
    # To specify a different path: show_all_tables('your_database.db')