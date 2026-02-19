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
    initial_sidebar_state="expanded"
)

# --- 2. CSS 美化工程 (含卡片樣式) ---
st.markdown("""
    <style>
    /* 全局字體設定 */
    html, body, [class*="css"] {
        font-family: "Microsoft JhengHei", "微軟正黑體", sans-serif;
    }
    
    /* 標題樣式 */
    .main-header {
        font-size: 32px !important;
        font-weight: 800;
        color: #00695C;
        text-align: center;
        padding: 20px;
        background-color: #E0F2F1;
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

    /* Step 2 問題區塊樣式 */
    .question-box {
        background-color: #F8F9FA;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #E0E0E0;
        border-left: 6px solid #00695C;
        margin-bottom: 25px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .question-title {
        font-size: 20px;
        font-weight: bold;
        color: #2E4053;
        margin-bottom: 10px;
        border-bottom: 1px solid #eee;
        padding-bottom: 5px;
    }

    /* Step 3 卡片樣式 (UDI-6) */
    .udi-card {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #B2DFDB; /* 淺綠框 */
        margin-bottom: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .udi-title { font-size: 18px; font-weight: bold; color: #00695C; }
    .udi-desc { font-size: 15px; color: #546E7A; margin-bottom: 10px; }

    /* 輸入框與標籤放大 */
    .stTextInput label, .stNumberInput label, .stSelectbox label, .stDateInput label {
        font-size: 20px !important;
        font-weight: 600 !important;
        color: #37474F !important;
    }
    .stRadio label, .stCheckbox label {
        font-size: 18px !important;
    }
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
        font-size: 18px !important; 
        height: 50px;
    }

    /* 按鈕優化 */
    .stButton > button {
        width: 100%;
        height: 60px;
        font-size: 20px !important;
        font-weight: bold;
        border-radius: 12px;
        transition: all 0.3s ease;
    }
    
    /* 下一步/送出按鈕 (右邊) - 珊瑚紅 */
    div[data-testid="stHorizontalBlock"] > div:nth-child(2) button {
        background-color: #FF7043; 
        color: white;
        border: none;
        box-shadow: 0 4px 0 #D84315;
    }
    div[data-testid="stHorizontalBlock"] > div:nth-child(2) button:hover {
        background-color: #FF5722;
        transform: translateY(2px);
        box-shadow: 0 2px 0 #D84315;
    }

    /* 上一步按鈕 (左邊) - 簡潔灰 */
    div[data-testid="stHorizontalBlock"] > div:nth-child(1) button {
        background-color: #ECEFF1;
        color: #455A64;
        border: 1px solid #CFD8DC;
    }
    
    /* 側邊欄按鈕特別樣式 */
    section[data-testid="stSidebar"] button {
        background-color: #ef5350 !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 4px 0 #c62828 !important;
    }

    /* 進度條顏色 */
    .stProgress > div > div > div > div {
        background-color: #26A69A;
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

# --- 4. Session State & Reset ---
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'patient_data' not in st.session_state:
    st.session_state.patient_data = {}

def next_step(): st.session_state.step += 1
def prev_step(): st.session_state.step -= 1

def reset_app():
    """清空所有資料並回到第一頁"""
    st.session_state.step = 1
    st.session_state.patient_data = {}
    # 清除送出成功的狀態
    if 'submit_success' in st.session_state:
        del st.session_state['submit_success']

# --- 5. 側邊欄功能區 ---
with st.sidebar:
    st.title("⚙️ 功能選單")
    st.info("此按鈕可隨時清除目前所有資料，並回到第一頁，方便下一位患者填寫。")
    
    if st.button("🔄 清空資料 / 下一位"):
        reset_app()
        st.rerun()

# --- 6. 主程式 ---

st.markdown("<div class='main-header'>🏥 海扶治療中心 - 患者追蹤問卷</div>", unsafe_allow_html=True)
progress_val = {1: 10, 2: 40, 3: 70, 4: 100}
st.progress(progress_val[st.session_state.step])

# ================= STEP 1: 基本資料 =================
if st.session_state.step == 1:
    st.markdown("<div class='step-header'>Step 1: 基本資料填寫</div>", unsafe_allow_html=True)
    
    with st.container():
        col1, col2 = st.columns(2, gap="large")
        
        with col1:
            p_id = st.text_input("病歷號碼", value=st.session_state.patient_data.get("id", ""), placeholder="請輸入病歷號")
            p_name = st.text_input("姓名", value=st.session_state.patient_data.get("name", ""), placeholder="請輸入姓名")
        
        with col2:
            default_date = date(1980, 1, 1)
            if "birth" in st.session_state.patient_data:
                try:
                    default_date = datetime.strptime(st.session_state.patient_data["birth"], "%Y-%m-%d").date()
                except:
                    pass

            p_birth_date = st.date_input(
                "出生年月日 (可點選日曆)",
                value=default_date,
                min_value=date(1920, 1, 1),
                max_value=date.today()
            )
            
            options = ["海扶術前", "海扶術後", "術後3個月", "6個月", "1年", "2年", "3年", "4年以上"]
            idx = 0
            if "followup" in st.session_state.patient_data and st.session_state.patient_data["followup"] in options:
                idx = options.index(st.session_state.patient_data["followup"])
            
            p_followup = st.selectbox("追蹤期間", options, index=idx)

    st.markdown("<br>", unsafe_allow_html=True)
    
    _, col_next = st.columns([3, 1])
    with col_next:
        if st.button("下一步 ➡️"):
            if not p_id or not p_name:
                st.warning("⚠️ 請填寫 病歷號 與 姓名")
            else:
                birth_str = p_birth_date.strftime("%Y-%m-%d")
                st.session_state.patient_data.update({
                    "id": p_id, "name": p_name, "birth": birth_str, "followup": p_followup
                })
                next_step()
                st.rerun()

# ================= STEP 2: 經血量評估 (PBAC) =================
elif st.session_state.step == 2:
    st.markdown("<div class='step-header'>Step 2: 經血量評估</div>", unsafe_allow_html=True)
    
    st.info("""
    **填寫說明：**
    請回想您 **「最近這一次經期」** 的情況。
    請對照左邊（或上方）的圖片，計算您總共使用了幾片衛生棉/棉條，以及發生過幾次血塊/滲漏。
    **請填寫「數量」（片數/次數），系統會自動幫您算分。**
    """)

    col_img, col_form = st.columns([1, 1.2], gap="large")
    
    with col_img:
        st.markdown("### 🖼️ 參考圖示")
        if os.path.exists("blood_chart.png"):
            st.image("blood_chart.png", caption="請對照此圖評估血量", use_column_width=True)
        else:
            st.error("⚠️ 圖片 blood_chart.png 未找到")
            st.markdown("請確認圖片已上傳至專案資料夾。")

    with col_form:
        no_blood = st.checkbox("我目前無月經 / 無經血困擾", value=st.session_state.patient_data.get("no_blood", False))

        if not no_blood:
            # ---區塊 1: 衛生棉---
            st.markdown('<div class="question-box">', unsafe_allow_html=True)
            st.markdown('<div class="question-title">🩸 1. 衛生棉 (使用總片數)</div>', unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown("**輕微 (1分)**")
                st.caption("僅沾染一點點")
                pl = st.number_input("輕微-片數", 0, 100, key="pl", label_visibility="collapsed", value=st.session_state.patient_data.get("pl", 0))
            with c2:
                st.markdown("**中等 (5分)**")
                st.caption("沾染約一半")
                pm = st.number_input("中等-片數", 0, 100, key="pm", label_visibility="collapsed", value=st.session_state.patient_data.get("pm", 0))
            with c3:
                st.markdown("**大量 (20分)**")
                st.caption("整片全濕")
                ph = st.number_input("大量-片數", 0, 100, key="ph", label_visibility="collapsed", value=st.session_state.patient_data.get("ph", 0))
            st.markdown('</div>', unsafe_allow_html=True)

            # ---區塊 2: 棉條---
            st.markdown('<div class="question-box">', unsafe_allow_html=True)
            st.markdown('<div class="question-title">🧶 2. 棉條 (使用總支數)</div>', unsafe_allow_html=True)
            st.markdown("*若無使用請留白或填 0*")
            
            c4, c5, c6 = st.columns(3)
            with c4:
                st.markdown("**輕微 (1分)**")
                st.caption("僅一點點")
                tl = st.number_input("棉輕-支數", 0, 100, key="tl", label_visibility="collapsed", value=st.session_state.patient_data.get("tl", 0))
            with c5:
                st.markdown("**中等 (5分)**")
                st.caption("約一半")
                tm = st.number_input("棉中-支數", 0, 100, key="tm", label_visibility="collapsed", value=st.session_state.patient_data.get("tm", 0))
            with c6:
                st.markdown("**大量 (10分)**")
                st.caption("整根全濕")
                th = st.number_input("棉大-支數", 0, 100, key="th", label_visibility="collapsed", value=st.session_state.patient_data.get("th", 0))
            st.markdown('</div>', unsafe_allow_html=True)

            # ---區塊 3: 血塊與意外---
            st.markdown('<div class="question-box">', unsafe_allow_html=True)
            st.markdown('<div class="question-title">⚠️ 3. 血塊與滲漏 (發生次數)</div>', unsafe_allow_html=True)
            
            c7, c8, c9 = st.columns(3)
            with c7:
                st.markdown("**小血塊 (1分)**")
                st.caption("像1元硬幣大小")
                cs = st.number_input("小血塊-次數", 0, 100, key="cs", label_visibility="collapsed", value=st.session_state.patient_data.get("cs", 0))
            with c8:
                st.markdown("**大血塊 (5分)**")
                st.caption("大於1元硬幣")
                cl = st.number_input("大血塊-次數", 0, 100, key="cl", label_visibility="collapsed", value=st.session_state.patient_data.get("cl", 0))
            with c9:
                st.markdown("**滲漏 (5分)**")
                st.caption("溢出沾到褲子")
                ac = st.number_input("滲漏-次數", 0, 100, key="ac", label_visibility="collapsed", value=st.session_state.patient_data.get("ac", 0))
            st.markdown('</div>', unsafe_allow_html=True)

            # 即時計算分數
            score = calculate_blood_score(pl, pm, ph, tl, tm, th, cs, cl, ac)
            st.success(f"📊 目前計算總分： **{score} 分**")
            
        else:
            pl=pm=ph=tl=tm=th=cs=cl=ac=0
            score = 0
            st.info("已選擇無經血困擾，分數為 0 分。")

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

    # --- 1. 經痛評估 (視覺化改良版) ---
    st.markdown("""
    <div style="background-color:#FFEBEE; padding:15px; border-radius:10px; border-left:5px solid #E57373; margin-bottom:20px;">
        <h3 style="color:#C62828; margin:0;">⚡ 1. 經痛程度</h3>
        <p style="color:#555; margin-top:5px;">請依照您<b>「最痛的時候」</b>的感覺，滑動下方拉桿選擇。</p>
    </div>
    """, unsafe_allow_html=True)

    no_pain = st.checkbox("😊 我完全沒有經痛困擾", value=st.session_state.patient_data.get("no_pain", False))

    if not no_pain:
        # 定義表情符號
        pain_options = {
            0: "0 (無痛) 😊", 1: "1 😐", 2: "2 (輕微) 🙂", 3: "3 😐",
            4: "4 (中等) 😣", 5: "5 😣", 6: "6 (強烈) 😖", 7: "7 😖",
            8: "8 (劇烈) 😭", 9: "9 😭", 10: "10 (無法忍受) 🚑"
        }
        
        default_val = st.session_state.patient_data.get("pain_val", 0)
        
        pain_selection = st.select_slider(
            label="請左右滑動選擇痛感：",
            options=list(pain_options.keys()),
            format_func=lambda x: pain_options[x],
            value=default_val
        )
        st.info(f"您選擇的是： **{pain_options[pain_selection]}**")
        pain_val = pain_selection
    else:
        pain_val = 0
        st.success("已記錄：無經痛。")

    st.markdown("---")

    # --- 2. 頻尿/漏尿評估 (卡片式改良版) ---
    st.markdown("""
    <div style="background-color:#E3F2FD; padding:15px; border-radius:10px; border-left:5px solid #2196F3; margin-bottom:20px;">
        <h3 style="color:#1565C0; margin:0;">🚽 2. 排尿與頻尿狀況</h3>
        <p style="color:#555; margin-top:5px;">請勾選以下症狀對您生活的<b>「困擾程度」</b>。</p>
    </div>
    """, unsafe_allow_html=True)
    
    no_udi = st.checkbox("🌟 我排尿都很正常，無任何困擾", value=st.session_state.patient_data.get("no_udi", False))
    
    # 題目定義
    udi_items = [
        {"icon": "🏃‍♀️", "title": "頻尿", "desc": "覺得小便次數太頻繁？"},
        {"icon": "🌊", "title": "急迫性漏尿", "desc": "有尿意時來不及跑到廁所就漏出來？"},
        {"icon": "🤧", "title": "應力性漏尿", "desc": "咳嗽、打噴嚏或運動時會漏尿？"},
        {"icon": "💧", "title": "滴尿", "desc": "小便量少，滴滴答答解不乾淨？"},
        {"icon": "😣", "title": "排尿困難", "desc": "小便排不出來，需要用力壓肚子？"},
        {"icon": "💥", "title": "疼痛", "desc": "下腹部或骨盆會感到疼痛或不舒服？"}
    ]
    option_map = {0: "完全沒有", 1: "有一點", 2: "滿困擾", 3: "非常嚴重"}
    udi_scores = []

    if not no_udi:
        for i, item in enumerate(udi_items):
            with st.container():
                st.markdown(f"""
                <div class="udi-card">
                    <div class="udi-title">{item['icon']} {item['title']}</div>
                    <div class="udi-desc">{item['desc']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                val = st.radio(
                    f"udi_q_{i}", 
                    options=[0, 1, 2, 3],
                    format_func=lambda x: f"{option_map[x]} ({x})",
                    index=st.session_state.patient_data.get(f"udi_{i}", 0),
                    key=f"radio_udi_{i}",
                    horizontal=True,
                    label_visibility="collapsed"
                )
                
                # --- [修正] 防止 NoneType 錯誤的關鍵 ---
                if val is None:
                    val = 0
                # -----------------------------------
                
                udi_scores.append(val)
                
        udi_total = sum(udi_scores)
        if udi_total > 0:
            st.warning(f"頻尿困擾總分：{udi_total} 分")
    else:
        udi_scores = [0]*6
        udi_total = 0
        st.success("已記錄：排尿正常。")

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
                    st.session_state['submit_success'] = True
                    st.rerun()
                else:
                    st.error("❌ 傳送失敗，請聯繫管理員。")

    # 如果成功送出，顯示成功訊息與「下一位」按鈕
    if st.session_state.get('submit_success', False):
        st.success("✅ 問卷已成功送出！")
        st.balloons()
        
        # 這裡的按鈕邏輯跟側邊欄一模一樣，確保清空資料並回到第一頁
        if st.button("🔄 填寫下一位 (清空資料)"):
            reset_app() # 呼叫清空函式
            st.rerun()  # 重跑網頁
