import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials # 여기가 바뀌었습니다!
import json

# 1. 페이지 설정
st.set_page_config(page_title="비즈니스 파트너 (Google)", layout="wide")

# --- 🔐 비밀번호 확인 기능 ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]:
        return True
    
    st.title("🔒 로그인이 필요합니다")
    password = st.text_input("비밀번호를 입력하세요", type="password")
    
    if st.button("로그인"):
        if "PASSWORD" in st.secrets and password == st.secrets["PASSWORD"]:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("비밀번호가 틀렸습니다.")
    return False

if not check_password():
    st.stop()

# --- ☁️ 구글 시트 연결 설정 (최신 google-auth 방식) ---
@st.cache_resource
def get_google_sheet_connection():
    try:
        # Secrets 설정 확인
        if "gcp_json" not in st.secrets:
            st.error("⚠️ Secrets 설정에 'gcp_json'이 없습니다.")
            return None

        # JSON 문자열을 사전(Dictionary)으로 변환
        json_string = st.secrets["gcp_json"]
        credentials_dict = json.loads(json_string, strict=False)
        
        # 권한 설정 (Scope)
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # ⭐ 여기가 최신 방식으로 변경됨 ⭐
        creds = Credentials.from_service_account_info(credentials_dict, scopes=scopes)
        client = gspread.authorize(creds)
        
        # 엑셀 파일 열기
        sh = client.open("비즈니스_데이터베이스")
        return sh
        
    except Exception as e:
        st.error(f"⚠️ 연결 오류 발생!\n에러 내용: {e}")
        return None

# 연결 시도
sh = get_google_sheet_connection()
if sh is None:
    st.stop()

# 시트 가져오기
try:
    worksheet_customers = sh.worksheet("고객목록")
    worksheet_history = sh.worksheet("상담기록")
    worksheet_todo = sh.worksheet("할일목록")
except:
    st.error("엑셀 시트 탭 이름(고객목록, 상담기록, 할일목록)을 확인해주세요!")
    st.stop()

# --- 데이터 읽기/쓰기 도우미 함수 ---
def read_data(worksheet):
    try:
        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

def append_data(worksheet, row_data):
    worksheet.append_row(row_data)

def update_checkbox(worksheet, task_name, new_status):
    try:
        cell = worksheet.find(task_name)
        worksheet.update_cell(cell.row, 2, "TRUE" if new_status else "FALSE")
    except:
        pass 

def delete_completed_todos(worksheet):
    data = worksheet.get_all_values()
    if not data: return
    headers = data[0]
    new_rows = [headers] + [row for row in data[1:] if len(row) > 1 and row[1] != "TRUE"]
    worksheet.clear()
    worksheet.update(new_rows)

# --- 사이드바 메뉴 ---
st.sidebar.title("☁️ 사장님 메뉴")
menu = st.sidebar.radio("이동하기", ["📇 비즈니스 카드", "✅ 할 일 목록"])

# --- 기능 1: 비즈니스 카드 ---
if menu == "📇 비즈니스 카드":
    st.title("📇 비즈니스 카드 시스템")
    
    # 헤더 자동 생성
    if not worksheet_customers.row_values(1):
        worksheet_customers.append_row(["고객명", "담당자", "등록일"])
    if not worksheet_history.row_values(1):
        worksheet_history.append_row(["고객명", "날짜", "시간", "내용"])

    tab1, tab2 = st.tabs(["🆕 신규 고객 등록", "📂 고객 검색 및 기록"])

    with tab1:
        st.subheader("새로운 고객 등록")
        with st.form("new_customer"):
            new_name = st.text_input("고객명 (업체명)")
            manager_info = st.text_input("담당자 (연락처)")
            submitted = st.form_submit_button("등록하기")

            if submitted and new_name:
                df = read_data(worksheet_customers)
                if not df.empty and "고객명" in df.columns and new_name in df["고객명"].values:
                    st.error("이미 등록된 고객입니다.")
                else:
                    append_data(worksheet_customers, [new_name, manager_info, str(datetime.now().date())])
                    st.success(f"'{new_name}' 저장 완료!")
                    st.rerun()

    with tab2:
        st.subheader("상담 기록 관리")
        df_customers = read_data(worksheet_customers)
        
        if df_customers.empty:
            st.info("등록된 고객이 없습니다.")
        else:
            customer_list = df_customers["고객명"].tolist()
            selected_customer = st.selectbox("고객 선택", customer_list)
            
            with st.form("log_form"):
                col1, col2 = st.columns(2)
                d = st.date_input("날짜")
                t = st.time_input("시간")
                memo = st.text_area("내용")
                if st.form_submit_button("기록 저장"):
                    append_data(worksheet_history, [selected_customer, str(d), str(t), memo])
                    st.success("저장되었습니다!")
                    st.rerun()
            
            st.divider()
            df_history = read_data(worksheet_history)
            if not df_history.empty and "고객명" in df_history.columns:
                my_history = df_history[df_history["고객명"] == selected_customer]
                if not my_history.empty:
                    st.dataframe(my_history[["날짜", "시간", "내용"]].sort_values("날짜", ascending=False), use_container_width=True)
                else:
                    st.info("기록이 없습니다.")
            else:
                st.info("기록이 없습니다.")

# --- 기능 2: 할 일 목록 ---
elif menu == "✅ 할 일 목록":
    st.title("✅ 오늘의 할 일")
    
    if not worksheet_todo.row_values(1):
        worksheet_todo.append_row(["업무", "상태"])

    c1, c2 = st.columns([3, 1])
    new_task = c1.text_input("새 업무", label_visibility="collapsed", placeholder="할 일 입력...")
    if c2.button("추가"):
        if new_task:
            append_data(worksheet_todo, [new_task, "FALSE"])
            st.rerun()

    df_todo = read_data(worksheet_todo)
    if not df_todo.empty:
        for i, row in df_todo.iterrows():
            is_done = (str(row["상태"]) == "TRUE")
            checked = st.checkbox(str(row["업무"]), value=is_done, key=f"todo_{i}")
            if checked != is_done:
                update_checkbox(worksheet_todo, row["업무"], checked)
                st.rerun()
        
        if st.button("완료된 항목 삭제"):
            delete_completed_todos(worksheet_todo)
            st.rerun()
    else:
        st.info("할 일이 없습니다. ☕")