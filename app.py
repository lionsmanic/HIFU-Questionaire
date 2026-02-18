import streamlit as st
import pandas as pd
from datetime import datetime, date
import io
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os

# --- 1. 頁面設定 ---
st.set_page_config(
    page_title="海扶治療中心 - 患者追蹤問卷",
    page_icon="🏥",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- 2. CSS 美化工程 (字體放大、配色柔和、間距調整) ---
st.markdown("""
    <style>
    /* 全局字體設定 */
    html, body, [class*="css"] {
        font-family: "Microsoft JhengHei", "微軟正黑體", sans-serif;
    }
    
    /* 1. 標題樣式 */
    .main-header {
        font-size: 32px !important;
        font-weight: 800;
        color: #00695C; /* 專業深藍綠 */
        text-align: center;
        padding: 20px;
        background-color: #E0F2F1; /* 淺綠底 */
        border-radius: 15px;
        margin-bottom: 25px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .step-header {
        font-size: 24px !important;
        font-weight: bold;
        color: #004D40;
        background-color: #fff;
        border-left: 8px solid #26A69A;
        padding: 15px 20px;
        margin-bottom: 25px;
        border-radius: 0 10px 10px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }

    /* 2. 輸入框與標籤放大 (關鍵) */
    /* 標籤文字 (Label) */
    .stTextInput label, .stNumberInput label, .stSelectbox label, .stDateInput label {
        font-size: 20px !important;
        font-weight: 600 !important;
        color: #37474F !important;
    }
    
    /* 單選/複選框文字 */
    .stRadio label, .stCheckbox label {
        font-size: 18px !important;
    }
    
    /* 輸入框內的文字 */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
        font-size: 18px !important; 
        height: 50px; /* 加高輸入框 */
    }

    /* 3. 按鈕優化 */
    .stButton > button {
        width: 100%;
        height: 60px; /* 按鈕加高 */
        font-size: 20px !important;
        font-weight: bold;
        border-radius: 12px;
        transition: all 0.3s ease;
    }
    
    /* 主要按鈕 (下一步/送出) - 珊瑚紅 */
    div[data-testid="stHorizontalBlock"] > div:nth-child(2) button {
        background-color: #FF7043; 
        color: white;
        border: none;
        box-shadow: 0 4px 0 #D84315; /* 立體感 */
    }
    div[data-testid="stHorizontalBlock"] > div:nth-child(2) button:hover {
        background-color: #FF5722;
        transform: translateY(2px);
        box-shadow: 0 2px 0 #D84315;
    }

    /* 次要按鈕 (上一步) - 簡潔灰 */
    div[data-testid="stHorizontalBlock"] > div:nth-child(1) button {
        background-color: #ECEFF1;
        color: #455A64;
        border: 1px solid #CFD8DC;
    }

    /* 4. 進度條顏色 */
    .stProgress > div > div > div > div {
        background-color: #26A69A;
    }
    
    /* 5. 調整 Expander (展開區) 字體 */
    .streamlit-expanderHeader {
        font-size: 18px !important;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 核心邏輯函數 ---

def calculate_blood_score(pad_light, pad_medium, pad_heavy,
                          tampon_light, tampon_medium, tampon_heavy,
                          small_clot, large_clot, accident):
    return (pad_light*1 + pad_medium*5 + pad_heavy*20 +
            tampon_light*1 + tampon_medium*5 + tampon_heavy*10 +
            small_clot*1 + large_clot*5 + accident*5)

def send_email_via_gmail(subject, content, df, filename):
    try:
        smtp_user = st.secrets["EMAIL_USER"]
        smtp_password = st.secrets["EMAIL_PASSWORD"]
        smtp_receiver = st.secrets["EMAIL_RECEIVER"]
    except Exception:
        st.error("❌ 設定錯誤：請檢查 secrets.toml 中的 Email 設定")
        return False

    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = smtp_receiver
    msg['Subject'] = subject
    msg.attach(MIMEText(content, 'html'))

    try:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
        output.seek(0)
        
        part = MIMEApplication(output.read(), Name=filename)
        part['Content-Disposition'] = f'attachment; filename="{filename}"'
        msg.attach(part)
    except Exception as e:
        st.error(f"❌ 附件製作失敗: {e}")
        return False

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"❌ 郵件發送失敗: {e}")
        return False

# --- 4. Session State ---
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'patient_data' not in st.session_state:
    st.session_state.patient_data = {}

def next_step(): st.session_state.step += 1
def prev_step(): st.session_state.step -= 1
def reset_app():
    st.session_state.step = 1
    st.session_state.patient_data = {}

# --- 5. 主程式 ---

st.markdown("<div class='main-header'>🏥 海扶治療中心 - 患者追蹤問卷</div>", unsafe_allow_html=True)
progress_val = {1: 10, 2: 40, 3: 70, 4: 100}
st.progress(progress_val[st.session_state.step])

# ================= STEP 1: 基本資料 =================
if st.session_state.step == 1:
    st.markdown("<div class='step-header'>Step 1: 基本資料填寫</div>", unsafe_allow_html=True)
    
    with st.container():
        # 增加 gap 讓左右間距寬一點
        col1, col2 = st.columns(2, gap="large")
        
        with col1:
            p_id = st.text_input("病歷號碼", value=st.session_state.patient_data.get("id", ""), placeholder="請輸入病歷號")
            p_name = st.text_input("姓名", value=st.session_state.patient_data.get("name", ""), placeholder="請輸入姓名")
        
        with col2:
            # === 修改重點：使用 date_input ===
            # 預設值邏輯：如果有填過就用填過的，沒有則預設 1980/1/1 (方便選取)
            default_date = date(1980, 1, 1)
            if "birth" in st.session_state.patient_data:
                try:
                    # 嘗試將字串轉回 date 物件顯示
                    default_date = datetime.strptime(st.session_state.patient_data["birth"], "%Y-%m-%d").date()
                except:
                    pass

            p_birth_date = st.date_input(
                "出生年月日 (可點選日曆)",
                value=default_date,
                min_value=date(1920, 1, 1),
                max_value=date.today()
            )
            
            # 選項邏輯
            options = ["海扶術前", "海扶術後", "術後3個月", "6個月", "1年", "2年", "3年", "4年以上"]
            idx = 0
            if "followup" in st.session_state.patient_data and st.session_state.patient_data["followup"] in options:
                idx = options.index(st.session_state.patient_data["followup"])
            
            p_followup = st.selectbox("追蹤期間", options, index=idx)

    st.markdown("<br>", unsafe_allow_html=True) # 增加垂直間距
    
    _, col_next = st.columns([3, 1])
    with col_next:
        if st.button("下一步 ➡️"):
            if not p_id or not p_name:
                st.warning("⚠️ 請填寫 病歷號 與 姓名")
            else:
                # 將日期物件轉為字串儲存
                birth_str = p_birth_date.strftime("%Y-%m-%d")
                st.session_state.patient_data.update({
                    "id": p_id, "name": p_name, "birth": birth_str, "followup": p_followup
                })
                next_step()
                st.rerun()

# ================= STEP 2: 經血量評估 (PBAC) =================
elif st.session_state.step == 2:
    st.markdown("<div class='step-header'>Step 2: 經血量評估 (PBAC Score)</div>", unsafe_allow_html=True)
    st.info("💡 請參考左側圖示，填寫您在一個經期內的「總使用量」。")

    c_img, c_input = st.columns([1, 1.5], gap="medium")
    
    with c_img:
        if os.path.exists("blood_chart.png"):
            st.image("blood_chart.png", caption="經血量參考圖", use_column_width=True)
        else:
            st.warning("⚠️ 圖片載入失敗 (blood_chart.png)")

    with c_input:
        # 使用 markdown 加大 checkbox 字體
        st.markdown("""<style>.stCheckbox label {font-size: 20px !important; color: #D84315 !important;}</style>""", unsafe_allow_html=True)
        no_blood = st.checkbox("我目前無月經 / 無經血困擾", value=st.session_state.patient_data.get("no_blood", False))
        
        if not no_blood:
            with st.expander("📝 點擊展開填寫 (請填寫數字)", expanded=True):
                st.markdown("#### 🩸 衛生棉 (片/週期)")
                c1, c2, c3 = st.columns(3)
                pl = c1.number_input("輕微 (1分)", 0, 100, value=st.session_state.patient_data.get("pl", 0))
                pm = c2.number_input("中等 (5分)", 0, 100, value=st.session_state.patient_data.get("pm", 0))
                ph = c3.number_input("大量 (20分)", 0, 100, value=st.session_state.patient_data.get("ph", 0))
                
                st.markdown("#### 🧶 棉條 (支/週期)")
                c4, c5, c6 = st.columns(3)
                tl = c4.number_input("棉-輕 (1分)", 0, 100, value=st.session_state.patient_data.get("tl", 0))
                tm = c5.number_input("棉-中 (5分)", 0, 100, value=st.session_state.patient_data.get("tm", 0))
                th = c6.number_input("棉-大 (10分)", 0, 100, value=st.session_state.patient_data.get("th", 0))
                
                st.markdown("#### ⚠️ 血塊與意外")
                c7, c8, c9 = st.columns(3)
                cs = c7.number_input("小血塊 (1分)", 0, 100, value=st.session_state.patient_data.get("cs", 0))
                cl = c8.number_input("大血塊 (5分)", 0, 100, value=st.session_state.patient_data.get("cl", 0))
                ac = c9.number_input("滲漏 (5分)", 0, 100, value=st.session_state.patient_data.get("ac", 0))

            score = calculate_blood_score(pl, pm, ph, tl, tm, th, cs, cl, ac)
            
            # 分數顯示美化
            st.markdown(f"""
            <div style="background-color:#E3F2FD; padding:15px; border-radius:10px; text-align:center; border: 2px solid #90CAF9;">
                <h3 style="margin:0; color:#1565C0;">目前總分：{score} 分</h3>
            </div>
            """, unsafe_allow_html=True)
            
        else:
            pl=pm=ph=tl=tm=th=cs=cl=ac=0
            score = 0
            st.info("已選擇無經血困擾。")

    st.markdown("<br>", unsafe_allow_html=True)
    col_back, col_next = st.columns([1, 1])
    with col_back:
        if st.button("⬅️ 上一步"):
            prev_step()
            st.rerun()
    with col_next:
        if st.button("下一步 ➡️"):
            st.session_state.patient_data.update({
                "no_blood": no_blood, "blood_score": score,
                "pl": pl, "pm": pm, "ph": ph,
                "tl": tl, "tm": tm, "th": th,
                "cs": cs, "cl": cl, "ac": ac
            })
            next_step()
            st.rerun()

# ================= STEP 3: 疼痛與頻尿 =================
elif st.session_state.step == 3:
    st.markdown("<div class='step-header'>Step 3: 症狀評估</div>", unsafe_allow_html=True)

    # --- 經痛 ---
    st.markdown("### 1. 經痛程度 (VAS Score)")
    st.caption("請滑動選擇痛感：0=無痛，10=無法忍受")
    
    no_pain = st.checkbox("無經痛困擾", value=st.session_state.patient_data.get("no_pain", False))
    if not no_pain:
        pain_val = st.slider("", 0, 10, value=st.session_state.patient_data.get("pain_val", 0))
    else:
        pain_val = 0

    st.markdown("---")

    # --- 頻尿 ---
    st.markdown("### 2. 頻尿/漏尿評估 (UDI-6)")
    st.markdown("""
    <div style='background-color:#FFF3E0; padding:10px; border-radius:5px; margin-bottom:15px;'>
    <b>困擾程度：</b> 0=無困擾，1=稍微，2=中度，3=極度
    </div>
    """, unsafe_allow_html=True)
    
    no_udi = st.checkbox("無頻尿/排尿困擾", value=st.session_state.patient_data.get("no_udi", False))
    
    udi_labels = ["頻尿 (小便次數多)", "尿急導致漏尿", "咳嗽/打噴嚏/運動時漏尿", "滴尿 (解完還有)", "排尿困難 (需用力)", "下腹/骨盆疼痛"]
    udi_scores = []

    if not no_udi:
        for i, label in enumerate(udi_labels):
            st.markdown(f"**{label}**")
            val = st.radio(f"label_{i}", [0, 1, 2, 3], index=st.session_state.patient_data.get(f"udi_{i}", 0), 
                           key=f"radio_udi_{i}", horizontal=True, label_visibility="collapsed")
            udi_scores.append(val)
        udi_total = sum(udi_scores)
    else:
        udi_scores = [0]*6
        udi_total = 0

    st.markdown("<br>", unsafe_allow_html=True)
    col_back, col_next = st.columns([1, 1])
    with col_back:
        if st.button("⬅️ 上一步"):
            prev_step()
            st.rerun()
    with col_next:
        if st.button("完成並預覽 ➡️"):
            udi_data = {f"udi_{i}": v for i, v in enumerate(udi_scores)}
            st.session_state.patient_data.update({
                "no_pain": no_pain, "pain_val": pain_val,
                "no_udi": no_udi, "udi_total": udi_total
            })
            st.session_state.patient_data.update(udi_data)
            next_step()
            st.rerun()

# ================= STEP 4: 確認與提交 =================
elif st.session_state.step == 4:
    st.markdown("<div class='step-header'>Step 4: 確認資料與送出</div>", unsafe_allow_html=True)
    
    d = st.session_state.patient_data
    
    with st.container():
        st.markdown(f"""
        <div style="background-color:#fff; padding:20px; border-radius:10px; border:1px solid #ddd; font-size:18px;">
            <p><b>👤 姓名：</b> {d.get('name')}</p>
            <p><b>📅 出生日期：</b> {d.get('birth')}</p>
            <p><b>🏥 病歷號：</b> {d.get('id')}</p>
            <p><b>🕒 追蹤期：</b> {d.get('followup')}</p>
            <hr>
            <p><b>🩸 經血分數：</b> <span style="color:#D84315; font-weight:bold;">{d.get('blood_score')} 分</span></p>
            <p><b>⚡ 經痛分數：</b> <span style="color:#D84315; font-weight:bold;">{d.get('pain_val')} 分</span></p>
            <p><b>🚽 頻尿分數：</b> <span style="color:#D84315; font-weight:bold;">{d.get('udi_total')} 分</span></p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_back, col_submit = st.columns([1, 1])
    
    with col_back:
        if st.button("⬅️ 返回修改"):
            prev_step()
            st.rerun()
    
    with col_submit:
        if st.button("✅ 確認送出 (Submit)"):
            with st.spinner("📩 正在發送報告，請稍候..."):
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                raw_data = {
                    "病歷號碼": [d['id']],
                    "姓名": [d['name']],
                    "出生年月日": [d['birth']],
                    "追蹤期間": [d['followup']],
                    "填寫時間": [now_str],
                    "經血分數(PBAC)": [d['blood_score']],
                    "經痛分數(VAS)": [d['pain_val']],
                    "頻尿分數(UDI)": [d['udi_total']],
                    "經血明細": [f"Pad:{d['pl']}/{d['pm']}/{d['ph']}, Tam:{d['tl']}/{d['tm']}/{d['th']}, Clot:{d['cs']}/{d['cl']}"],
                    "頻尿明細": [str([d[f'udi_{i}'] for i in range(6)])]
                }
                df = pd.DataFrame(raw_data)
                
                filename = f"{d['name']}_{d['followup']}_Report.xlsx"
                email_content = f"""
                <h2 style="color:#00695C;">海扶中心 - 問卷回覆通知</h2>
                <hr>
                <p><b>姓名：</b>{d['name']}</p>
                <p><b>病歷號：</b>{d['id']}</p>
                <p><b>追蹤期間：</b>{d['followup']}</p>
                <p><b>總結分數：</b></p>
                <ul>
                    <li>經血: {d['blood_score']}</li>
                    <li>經痛: {d['pain_val']}</li>
                    <li>頻尿: {d['udi_total']}</li>
                </ul>
                <p>詳細數據請查閱附件 Excel。</p>
                """
                
                success = send_email_via_gmail(
                    subject=f"【問卷】{d['name']} - {d['followup']}",
                    content=email_content,
                    df=df,
                    filename=filename
                )
                
                if success:
                    st.success("✅ 問卷已成功送出！")
                    st.balloons()
                    if st.button("填寫下一位"):
                        reset_app()
                        st.rerun()
                else:
                    st.error("❌ 傳送失敗，請聯繫管理員。")
