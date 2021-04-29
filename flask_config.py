import os


class Config:
    SQLALCHEMY_DATABASE_URI = f"mssql+pyodbc://{os.environ.get('DATABASE_URL')}?driver=ODBC Driver 17 for SQL Server?trusted_connection=yes"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SCHEDULED_JOB_INTERVAL_SECONDS = int(os.environ.get('SCHEDULED_JOB_INTERVAL_SECONDS'))
    FINANCE_PACKAGE_URL = os.environ.get('FINANCE_PACKAGE_URL')
