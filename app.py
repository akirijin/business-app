import streamlit as st
import pandas as pd
import os
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="비즈니스 파트너", layout="wide")

# --- 🔐 비밀번호 확인 기능 (새로 추가됨) ---
def check_password():
    """비밀번호가 맞는지 확인하는 함수"""
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True # 이미 로그인 성공함

    # 비밀번호 입력창 보여주기
    st.title("🔒 로그인이 필요합니다")
    password = st.text_input("비밀번호를 입력하세요", type="password")
    
    if st.button("로그인"):
        # st.secrets는 클라우드에 저장된 비밀번호를 가져옵니다
        if password == st.secrets["PASSWORD"]:
            st.session_state["password_correct"] = True
            st.rerun() # 화면 새로고침해서 앱 보여주기
        else:
            st.error("비밀번호가 틀렸습니다.")
    return False

if not check_password():
    st.stop() # 비밀번호 틀리면 여기서 멈춤 (아래 코드 실행 안 함)
# -------------------------------------------

# 고객 데이터가 저장될 메인 폴더 생성
BASE_DIR = "고객폴더"
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

# 데이터 불러오기/저장하기 함수
def load_data(filepath, columns):
    if not os.path.exists(filepath):
        return pd.DataFrame(columns=columns)
    return pd.read_csv(filepath)

def save_data(df, filepath):
    df.to_csv(filepath, index=False)

# 사이드바 메뉴
st.sidebar.title("사장님 메뉴")
menu = st.sidebar.radio("이동하기", ["📇 비즈니스 카드 (고객관리)", "✅ 할 일 목록"])

# --- 기능 1: 비즈니스 카드 (고객 관리 시스템) ---
if menu == "📇 비즈니스 카드 (고객관리)":
    st.title("📇 비즈니스 카드 시스템")

    tab1, tab2 = st.tabs(["🆕 신규 고객 등록", "📂 고객 검색 및 기록 추가"])

    # [탭 1] 신규 고객 등록
    with tab1:
        st.subheader("새로운 고객 등록")
        with st.form("new_customer_form"):
            new_name = st.text_input("고객명 (업체명)")
            manager_info = st.text_input("담당자 (연락처)")
            create_btn = st.form_submit_button("고객 폴더 생성")

            if create_btn and new_name:
                customer_folder = os.path.join(BASE_DIR, new_name)
                
                if os.path.exists(customer_folder):
                    st.error("이미 등록된 고객명입니다!")
                else:
                    os.makedirs(customer_folder)
                    info_df = pd.DataFrame({'고객명': [new_name], '담당자': [manager_info], '등록일': [datetime.now().strftime('%Y-%m-%d')]})
                    info_df.to_csv(os.path.join(customer_folder, "info.csv"), index=False)
                    st.success(f"'{new_name}' 폴더가 생성되었습니다!")

    # [탭 2] 기존 고객 검색 및 기록 추가
    with tab2:
        st.subheader("고객 기록 관리")
        
        customer_list = [f for f in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, f))]
        
        if not customer_list:
            st.info("아직 등록된 고객이 없습니다.")
        else:
            selected_customer = st.selectbox("고객을 선택하세요", customer_list)
            
            current_folder = os.path.join(BASE_DIR, selected_customer)
            history_file = os.path.join(current_folder, "history.csv")
            
            st.markdown(f"### ✏️ '{selected_customer}' 미팅/AS 기록")
            with st.form("add_log_form"):
                col1, col2 = st.columns(2)
                with col1:
                    log_date = st.date_input("미팅, AS 날짜")
                with col2:
                    log_time = st.time_input("예약 시간")
                
                log_memo = st.text_area("미팅 내용 (메모)", height=100)
                save_log = st.form_submit_button("기록 저장하기")

                if save_log:
                    df_history = load_data(history_file, ['날짜', '시간', '내용'])
                    new_record = pd.DataFrame({'날짜': [log_date], '시간': [log_time], '내용': [log_memo]})
                    df_history = pd.concat([df_history, new_record], ignore_index=True)
                    save_data(df_history, history_file)
                    st.success("기록이 저장되었습니다!")
                    st.rerun()

            st.divider()
            st.markdown(f"### 📖 '{selected_customer}' 히스토리")
            df_view = load_data(history_file, ['날짜', '시간', '내용'])
            if not df_view.empty:
                df_view = df_view.sort_values(by=['날짜', '시간'], ascending=False)
                st.dataframe(df_view, use_container_width=True)
            else:
                st.info("아직 저장된 기록이 없습니다.")

# --- 기능 2: 할 일 목록 ---
elif menu == "✅ 할 일 목록":
    st.title("✅ 오늘의 할 일")
    
    new_task = st.text_input("새로운 업무 추가")
    if st.button("추가"):
        if new_task:
            file_todo = 'todo.csv'
            df_todo = load_data(file_todo, ['업무', '상태'])
            new_row = pd.DataFrame({'업무': [new_task], '상태': [False]})
            df_todo = pd.concat([df_todo, new_row], ignore_index=True)
            save_data(df_todo, file_todo)
            st.rerun()

    file_todo = 'todo.csv'
    df_todo = load_data(file_todo, ['업무', '상태'])
    
    if not df_todo.empty:
        for i, row in df_todo.iterrows():
            done = st.checkbox(row['업무'], value=row['상태'], key=i)
            if done != row['상태']:
                df_todo.at[i, '상태'] = done
                save_data(df_todo, file_todo)
                st.rerun()
        
        if st.button("완료된 업무 삭제"):
            df_todo = df_todo[df_todo['상태'] == False]
            save_data(df_todo, file_todo)
            st.rerun()