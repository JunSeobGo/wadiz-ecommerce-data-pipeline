from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import boto3
import pandas as pd
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

load_dotenv()

AWS_REGION = os.getenv('AWS_REGION', 'ap-northeast-2')
ATHENA_DATABASE = os.getenv('ATHENA_DATABASE', os.getenv('GOLD_DB', 'wadiz_gold2_db'))
ATHENA_OUTPUT_LOCATION = os.getenv('ATHENA_OUTPUT_LOCATION', 's3://wd-athena-query3/google-sheets-export/')
GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'secrets/google_service_account.json')
GOOGLE_SHEETS_SPREADSHEET_ID = os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID')
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

EXPORT_TARGETS = [
    ('campaign_kpi', 'SELECT * FROM wadiz_gold2_db.campaign_kpi_public'),
    ('campaign_daily_kpi', 'SELECT * FROM wadiz_gold2_db.campaign_daily_kpi_public'),
    ('campaign_conversion_kpi', 'SELECT * FROM wadiz_gold2_db.campaign_conversion_kpi_public'),
    ('comment_nlp_kpi', 'SELECT * FROM wadiz_gold2_db.comment_nlp_kpi_public'),
    ('campaign_response_performance', 'SELECT * FROM wadiz_gold2_db.campaign_response_performance_public'),
    ('campaign_category_benchmark', 'SELECT * FROM wadiz_gold2_db.campaign_category_benchmark_public'),
]


def require_env() -> None:
    if not GOOGLE_SHEETS_SPREADSHEET_ID:
        raise ValueError('GOOGLE_SHEETS_SPREADSHEET_ID가 .env에 필요합니다.')
    if not Path(GOOGLE_APPLICATION_CREDENTIALS).exists():
        raise FileNotFoundError(f'Google service account JSON을 찾을 수 없습니다: {GOOGLE_APPLICATION_CREDENTIALS}')


def wait_for_athena_query(athena: Any, query_execution_id: str, poll_seconds: int = 2) -> None:
    while True:
        result = athena.get_query_execution(QueryExecutionId=query_execution_id)
        status = result['QueryExecution']['Status']
        state = status['State']
        if state == 'SUCCEEDED':
            return
        if state in {'FAILED', 'CANCELLED'}:
            raise RuntimeError(f'Athena query failed. id={query_execution_id}, reason={status.get("StateChangeReason")}')
        time.sleep(poll_seconds)


def run_athena_query_to_dataframe(query: str) -> pd.DataFrame:
    athena = boto3.client('athena', region_name=AWS_REGION)
    response = athena.start_query_execution(
        QueryString=query,
        QueryExecutionContext={'Database': ATHENA_DATABASE},
        ResultConfiguration={'OutputLocation': ATHENA_OUTPUT_LOCATION},
    )
    qid = response['QueryExecutionId']
    print(f'Athena query started: {qid}')
    wait_for_athena_query(athena, qid)

    paginator = athena.get_paginator('get_query_results')
    columns: list[str] | None = None
    rows: list[list[str | None]] = []

    for page in paginator.paginate(QueryExecutionId=qid):
        for row in page['ResultSet']['Rows']:
            values = [cell.get('VarCharValue') for cell in row.get('Data', [])]
            if columns is None:
                columns = values
                continue
            rows.append(values)

    if columns is None:
        return pd.DataFrame()
    df = pd.DataFrame(rows, columns=columns)
    print(f'Athena result loaded. rows={len(df)} columns={len(df.columns)}')
    return df


def build_sheets_service() -> Any:
    credentials = service_account.Credentials.from_service_account_file(GOOGLE_APPLICATION_CREDENTIALS, scopes=SCOPES)
    return build('sheets', 'v4', credentials=credentials)


def get_existing_sheet_names(service: Any, spreadsheet_id: str) -> set[str]:
    metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    return {sheet['properties']['title'] for sheet in metadata.get('sheets', [])}


def ensure_sheet_exists(service: Any, spreadsheet_id: str, sheet_name: str) -> None:
    if sheet_name in get_existing_sheet_names(service, spreadsheet_id):
        return
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={'requests': [{'addSheet': {'properties': {'title': sheet_name}}}]},
    ).execute()


def dataframe_to_sheet_values(df: pd.DataFrame) -> list[list[Any]]:
    clean_df = df.copy().astype('object')
    clean_df = clean_df.where(pd.notnull(clean_df), '')
    return [list(clean_df.columns)] + clean_df.values.tolist()


def overwrite_sheet(service: Any, spreadsheet_id: str, sheet_name: str, df: pd.DataFrame) -> None:
    ensure_sheet_exists(service, spreadsheet_id, sheet_name)
    service.spreadsheets().values().clear(spreadsheetId=spreadsheet_id, range=f"'{sheet_name}'", body={}).execute()
    values = dataframe_to_sheet_values(df)
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"'{sheet_name}'!A1",
        valueInputOption='RAW',
        body={'values': values},
    ).execute()
    print(f'Google Sheet updated. sheet={sheet_name} rows={max(len(values) - 1, 0)}')


def export_all() -> None:
    require_env()
    service = build_sheets_service()
    for sheet_name, query in EXPORT_TARGETS:
        print('=' * 80)
        print(f'Exporting {sheet_name}')
        df = run_athena_query_to_dataframe(query)
        overwrite_sheet(service, GOOGLE_SHEETS_SPREADSHEET_ID, sheet_name, df)
    print('Google Sheets export completed.')


if __name__ == '__main__':
    export_all()
