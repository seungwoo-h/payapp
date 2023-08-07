from oauth2client.service_account import ServiceAccountCredentials
import gspread
import pandas as pd
import json
import yaml
import streamlit as st

# configs
# with open('./config.yaml') as f:
#     args = yaml.load(f, Loader=yaml.FullLoader)
# scope = args["scope"]
# json_key_path = args["json_key_path"]
# users = args["users"]
# spreadsheet_url = args["spreadsheet_url"]
# sheetname = args["sheet_name"]

scope = st.secrets['scope']
json_key_path = st.secrets['json_key_path']
users = st.secrets["users"]
spreadsheet_url = st.secrets["spreadsheet_url"]
sheetname = st.secrets["sheet_name"]

# google cloud api
credential = ServiceAccountCredentials.from_json_keyfile_name(json_key_path, scope)
gc = gspread.authorize(credential)

# read spreadsheet
doc = gc.open_by_url(spreadsheet_url)
worksheet = doc.worksheet(sheetname)
records = worksheet.get_all_records()

# init dataframe
df = pd.DataFrame(records)
# 정산 여부 체크
df['정산 여부'] = False
for user in users:
    df[f'user_{user}'] = 0
status_dct = json.load(open("./status.json"))
pay_done = status_dct['pay_done']
df['정산 여부'] = df['타임스탬프'].apply(lambda x: x in pay_done)
# 컬럼 분리
for idx, row in df.iterrows():
    assigned_users = row[5].split(", ")
    amount_per_person = float(row[4]) / len(assigned_users)
    for user in assigned_users:
        if row[1] == user:
            continue
        df.loc[idx, f"user_{user}"] = amount_per_person

# FRONTEND
st.set_page_config(layout="wide")

page_bg_img = f"""
<style>
[data-testid="stAppViewContainer"] > .main {{
background-image: url("https://www.6amgroup.com/wp-content/uploads/2016/05/MusicOn1.jpg");
background-size: 180%;
background-position: top left;
background-repeat: repeat;
background-attachment: local;
}}

[data-testid="stHeader"] {{
background: rgba(0,0,0,0);
}}
</style>
"""

st.markdown(page_bg_img, unsafe_allow_html=True)

st.title("🏝️ 이비자 정산기 2023 🏝️")
st.write("https://docs.google.com/forms/d/e/1FAIpQLScXiG0G7ZzBS08sag5lfleqUMTWB0E8twY4MB_o0rL49JmZ2A/viewform")
st.header("💰 정산 결제 내역")
st.write("구글독스에서 실시간 연동 됨. 정산 여부 반드시 체크하고, 저장까지 누르세요.")
df = st.data_editor(df, disabled=[i for i in df.columns if i != "정산 여부"])
save_status = st.button("정산 현황 저장 (정산 여부 체크후 반드시 눌러야 저장됨)")
if save_status:
    status_dct['pay_done'] = df[df['정산 여부']==True]['타임스탬프'].to_list()
    json.dump(status_dct, open("./status.json", 'w'))

st.header("💰 주고 받을 돈")
df_groupby = df[df['정산 여부']==False].groupby(['결제한 사람', "결제 통화"]).sum().reset_index()[['결제한 사람', "결제 통화", "결제 금액 (숫자만 표기) 취소시 (-)로 표기하세요"]+[f"user_{i}" for i in users]]
df_groupby = df_groupby.rename(columns={f"user_{i}": f"{i}에게 받을 금액" for i in users})
df_groupby = df_groupby.rename(columns={"결제 금액 (숫자만 표기) 취소시 (-)로 표기하세요": "통화별 총 결제액"})
st.write(df_groupby)

st.header("💰 현재까지 갖다 버린 돈")
krw_total = df[df['결제 통화']=="한화"]['결제 금액 (숫자만 표기) 취소시 (-)로 표기하세요'].sum()
eur_total = df[df['결제 통화']=="유로"]['결제 금액 (숫자만 표기) 취소시 (-)로 표기하세요'].sum()
usd_total =df[df['결제 통화']=="달러"]['결제 금액 (숫자만 표기) 취소시 (-)로 표기하세요'].sum()

st.metric(label="KRW TOTAL", value=f"{krw_total:,} ₩")
st.metric(label="EUR TOTAL", value=f"{eur_total:,} €")
st.metric(label="USD TOTAL", value=f"{usd_total:,} $")
