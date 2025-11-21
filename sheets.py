import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

class SheetsClient:
    def __init__(self, cred_file, spreadsheet_id):
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(cred_file, scope)
        self.client = gspread.authorize(creds)
        self.spreadsheet = self.client.open_by_key(spreadsheet_id)

    # normalize header supaya tidak error
    def normalize_df(self, df):
        df.columns = (
            df.columns
            .str.strip()
            .str.lower()
            .str.replace(" ", "_")
            .str.replace("-", "_")
        )
        return df

    def get_all_records(self, sheet_name):
        sheet = self.spreadsheet.worksheet(sheet_name)
        return sheet.get_all_records(empty2zero=False, head=1)

    def get_dataframe(self, sheet_name):
        records = self.get_all_records(sheet_name)
        df = pd.DataFrame(records)
        if df.empty:
            return df
        return self.normalize_df(df)

    # Lookup child by child_id
    def find_child(self, child_id):
        df = self.get_dataframe('children')
        if df.empty:
            return None
        if 'child_id' not in df.columns:
            return None
        found = df[df['child_id'].astype(str) == str(child_id)]
        if found.empty:
            return None
        return found.iloc[0].to_dict()

    # Register mapping telegram_id -> child_id
    def register_mapping(self, telegram_id, child_id):
        mapping_ws = self.spreadsheet.worksheet('mapping')
        now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        mapping_ws.append_row([str(telegram_id), str(child_id), 'yes', now])
        return True

    # Check if telegram_id already registered
    def get_mapping_for_telegram(self, telegram_id):
        df = self.get_dataframe('mapping')
        if df.empty:
            return None
        if 'telegram_id' not in df.columns:
            return None
        match = df[df['telegram_id'].astype(str) == str(telegram_id)]
        if match.empty:
            return None
        return match.iloc[-1].to_dict()

    # Get history for a child_id
    def get_history(self, child_id):
        df = self.get_dataframe('history')
        if df.empty:
            return []
        if 'child_id' not in df.columns:
            return []
        res = df[df['child_id'].astype(str) == str(child_id)]
        if res.empty:
            return []
        if 'date' in res.columns:
            res['date'] = pd.to_datetime(res['date'], errors='coerce')
            res = res.sort_values(by='date', ascending=False)
        return res.fillna('').to_dict(orient='records')

    def get_latest(self, child_id):
        history = self.get_history(child_id)
        if not history:
            return None
        return history[0]

    def add_mapping_row_if_not_exists(self, telegram_id, child_id):
        existing = self.get_mapping_for_telegram(telegram_id)
        if existing and existing.get('child_id') == str(child_id):
            return False
        return self.register_mapping(telegram_id, child_id)

