from superset import db
from superset.models.core import Database
from superset.connectors.sqla.models import SqlaTable

def setup_geodata():
    # 1. Connect Database
    db_name = "Geodata_PostGIS"
    sqlalchemy_uri = "postgresql://geo_admin:geo_password@postgis:5432/geodata"
    
    database = db.session.query(Database).filter_by(database_name=db_name).first()
    if not database:
        print(f"Creating database connection: {db_name}")
        database = Database(database_name=db_name, sqlalchemy_uri=sqlalchemy_uri)
        db.session.add(database)
        db.session.commit()
        database = db.session.query(Database).filter_by(database_name=db_name).first()
    else:
        print(f"Database {db_name} already exists.")

    # 2. Add Datasets
    tables = ["buildings", "roads", "rainfall"]
    for table_name in tables:
        table = db.session.query(SqlaTable).filter_by(table_name=table_name).first()
        if not table:
            print(f"Adding dataset: {table_name}")
            table = SqlaTable(table_name=table_name, database=database)
            db.session.add(table)
            db.session.commit()
        else:
            print(f"Dataset {table_name} already exists.")

if __name__ == "__main__":
    setup_geodata()
