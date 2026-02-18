import streamlit as st
import pandas as pd
from datetime import datetime
import io
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os

# --- 1. 頁面設定 ---
st.set_page_config(
    page_title="長庚海扶治療中心 - 患者追蹤問卷",
    page_icon="🏥",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- 2. CSS 樣式優化 ---
st.markdown("""
    <style>
    .main-header {
        font-size: 26px;
        font-weight: bold;
        color: #2E86C1;
        text-align: center;
        padding-bottom: 20px;
        border-bottom: 2px solid #eee;
        margin-bottom: 20px;
    }
    .step-header {
        font-size: 20px;
        font-weight: bold;
        color: #333;
        margin-top: 10px;
        margin-bottom: 20px;
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 8px;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
        font-weight: bold;
    }
    /* 強調主要按鈕 */
    div[data-testid="stHorizontalBlock"] > div:nth-child(2) button {
        background-color: #FF4B4B;
        color: white;
        border: none;
    }
    /* 次要按鈕 (上一步) */
    div[data-testid="stHorizontalBlock"] > div:nth-child(1) button {
        background-color: #ffffff;
        color: #333;
        border: 1px solid #ddd;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 核心邏輯函數 ---

def calculate_blood_score(pad_light, pad_medium, pad_heavy,
                          tampon_light, tampon_medium, tampon_heavy,
                          small_clot, large_clot, accident):
    """計算 PBAC 分數"""
    return (pad_light*1 + pad_medium*5 + pad_heavy*20 +
            tampon_light*1 + tampon_medium*5 + tampon_heavy*10 +
            small_clot*1 + large_clot*5 + accident*5)

def send_email_via_gmail(subject, content, df, filename):
    """
    使用 Gmail SMTP 發送郵件 (含 Excel 附件)
    """
    # 嘗試從 secrets 讀取帳密
    try:
        smtp_user = st.secrets["EMAIL_USER"]
        smtp_password = st.secrets["EMAIL_PASSWORD"]
        smtp_receiver = st.secrets["EMAIL_RECEIVER"]
    except Exception:
        st.error("❌ 系統設定錯誤：找不到 Email 帳號密碼，請檢查 secrets.toml")
        return False

    # 建立郵件物件
    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = smtp_receiver
    msg['Subject'] = subject

    # 加入內文
    msg.attach(MIMEText(content, 'html'))

    # 處理 Excel 附件 (不存檔，直接在記憶體轉換)
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

    # 連線 SMTP Server 發送
    try:
        # Gmail SMTP 設定: smtp.gmail.com, Port 465 (SSL)
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"❌ 郵件發送失敗 (SMTP Error): {e}")
        return False

# --- 4. Session State 初始化 (狀態管理) ---
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'patient_data' not in st.session_state:
    st.session_state.patient_data = {}

# 導航函數
def next_step():
    st.session_state.step += 1
def prev_step():
    st.session_state.step -= 1
def reset_app():
    st.session_state.step = 1
    st.session_state.patient_data = {}

# --- 5. 主程式介面 ---

st.markdown("<div class='main-header'>🏥 長庚海扶治療中心 - 患者追蹤問卷</div>", unsafe_allow_html=True)

# 進度條顯示
progress_val = {1: 10, 2: 40, 3: 70, 4: 100}
st.progress(progress_val[st.session_state.step])

# ================= STEP 1: 基本資料 =================
if st.session_state.step == 1:
    st.markdown("<div class='step-header'>Step 1: 基本資料填寫</div>", unsafe_allow_html=True)
    
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            # 嘗試讀取舊值，若無則為空
            p_id = st.text_input("病歷號碼", value=st.session_state.patient_data.get("id", ""))
            p_name = st.text_input("姓名", value=st.session_state.patient_data.get("name", ""))
        with col2:
            p_birth = st.text_input("出生西元年月日 (例: 1980-01-01)", 
                                    value=st.session_state.patient_data.get("birth", ""))
            
            # 定義選項
            options = ["海扶術前", "海扶術後", "術後3個月", "6個月", "1年", "2年", "3年", "4年以上"]
            # 嘗試抓取上次選的 index
            saved_idx = 0
            if "followup" in st.session_state.patient_data:
                try:
                    saved_idx = options.index(st.session_state.patient_data["followup"])
                except:
                    saved_idx = 0
            
            p_followup = st.selectbox("追蹤期間", options, index=saved_idx)

    st.markdown("---")
    # 下一步按鈕
    _, col_next = st.columns([3, 1])
    with col_next:
        if st.button("下一步 ➡️"):
            if not p_id or not p_name or not p_birth:
                st.warning("⚠️ 請填寫完整的 病歷號、姓名 與 出生日期")
            else:
                st.session_state.patient_data.update({
                    "id": p_id, "name": p_name, "birth": p_birth, "followup": p_followup
                })
                next_step()
                st.rerun()

# ================= STEP 2: 經血量評估 (PBAC) =================
elif st.session_state.step == 2:
    st.markdown("<div class='step-header'>Step 2: 經血量評估 (PBAC Score)</div>", unsafe_allow_html=True)
    st.info("💡 請參考左側圖示，填寫您在一個經期內的「總使用量」。")

    c_img, c_input = st.columns([1, 1.5])
    
    with c_img:
        # 顯示圖片 (請確保圖片在同目錄)
        if os.path.exists("blood_chart.png"):
            st.image("blood_chart.png", caption="經血量參考圖", use_column_width=True)
        else:
            st.warning("⚠️ 找不到圖片 blood_chart.png，請確認檔案已上傳。")

    with c_input:
        no_blood = st.checkbox("我目前無月經/無經血困擾", value=st.session_state.patient_data.get("no_blood", False))
        
        if not no_blood:
            with st.expander("📝 點擊展開填寫細項", expanded=True):
                st.markdown("**衛生棉 (片/週期)**")
                c1, c2, c3 = st.columns(3)
                pl = c1.number_input("輕微 (1分)", 0, 100, value=st.session_state.patient_data.get("pl", 0))
                pm = c2.number_input("中等 (5分)", 0, 100, value=st.session_state.patient_data.get("pm", 0))
                ph = c3.number_input("大量 (20分)", 0, 100, value=st.session_state.patient_data.get("ph", 0))
                
                st.markdown("**棉條 (支/週期)**")
                c4, c5, c6 = st.columns(3)
                tl = c4.number_input("棉-輕 (1分)", 0, 100, value=st.session_state.patient_data.get("tl", 0))
                tm = c5.number_input("棉-中 (5分)", 0, 100, value=st.session_state.patient_data.get("tm", 0))
                th = c6.number_input("棉-大 (10分)", 0, 100, value=st.session_state.patient_data.get("th", 0))
                
                st.markdown("**血塊與意外**")
                c7, c8, c9 = st.columns(3)
                cs = c7.number_input("小血塊 (1分)", 0, 100, value=st.session_state.patient_data.get("cs", 0))
                cl = c8.number_input("大血塊 (5分)", 0, 100, value=st.session_state.patient_data.get("cl", 0))
                ac = c9.number_input("滲漏 (5分)", 0, 100, value=st.session_state.patient_data.get("ac", 0))

            # 即時計算
            score = calculate_blood_score(pl, pm, ph, tl, tm, th, cs, cl, ac)
            st.metric("目前經血量分數", f"{score} 分")
            
            # 判斷結果提示
            if score > 100:
                st.error("您的經血量分數偏高 (>100)，建議諮詢醫師。")
            elif score > 0:
                st.success("分數計算完成。")
        else:
            # 歸零邏輯
            pl=pm=ph=tl=tm=th=cs=cl=ac=0
            score = 0
            st.info("已選擇無經血困擾，分數為 0 分。")

    st.markdown("---")
    col_back, col_next = st.columns([1, 1])
    with col_back:
        if st.button("⬅️ 上一步"):
            prev_step()
            st.rerun()
    with col_next:
        if st.button("下一步 ➡️"):
            # 儲存數據
            st.session_state.patient_data.update({
                "no_blood": no_blood, "blood_score": score,
                "pl": pl, "pm": pm, "ph": ph,
                "tl": tl, "tm": tm, "th": th,
                "cs": cs, "cl": cl, "ac": ac
            })
            next_step()
            st.rerun()

# ================= STEP 3: 疼痛與頻尿評估 =================
elif st.session_state.step == 3:
    st.markdown("<div class='step-header'>Step 3: 症狀評估</div>", unsafe_allow_html=True)

    # --- 經痛區塊 ---
    st.subheader("1. 經痛程度 (VAS Score)")
    no_pain = st.checkbox("無經痛困擾", value=st.session_state.patient_data.get("no_pain", False))
    
    if not no_pain:
        pain_val = st.slider("請滑動選擇痛感 (0-10分)", 0, 10, value=st.session_state.patient_data.get("pain_val", 0))
        st.caption("說明：0=無痛, 5=中等, 10=無法忍受")
    else:
        pain_val = 0
        st.caption("已選擇無經痛。")

    st.markdown("---")

    # --- 頻尿區塊 (UDI-6) ---
    st.subheader("2. 頻尿/漏尿評估 (UDI-6)")
    st.caption("請回答下列症狀對您的**困擾程度**：0=無, 1=稍微, 2=中度, 3=極度")
    
    no_udi = st.checkbox("無頻尿/排尿相關困擾", value=st.session_state.patient_data.get("no_udi", False))
    
    udi_labels = ["頻尿 (小便次數多)", "尿急導致漏尿", "咳嗽/打噴嚏/運動時漏尿", "滴尿 (解完還有)", "排尿困難 (需用力)", "下腹/骨盆疼痛"]
    udi_scores = []

    if not no_udi:
        # 使用 Grid 排版讓選項整齊
        for i, label in enumerate(udi_labels):
            st.markdown(f"**{label}**")
            # 使用 unique key 避免衝突
            val = st.radio(f"label_{i}", [0, 1, 2, 3], index=st.session_state.patient_data.get(f"udi_{i}", 0), 
                           key=f"radio_udi_{i}", horizontal=True)
            udi_scores.append(val)
        udi_total = sum(udi_scores)
        st.metric("頻尿困擾總分", f"{udi_total} 分")
    else:
        udi_scores = [0]*6
        udi_total = 0

    st.markdown("---")
    col_back, col_next = st.columns([1, 1])
    with col_back:
        if st.button("⬅️ 上一步"):
            prev_step()
            st.rerun()
    with col_next:
        if st.button("完成並預覽 ➡️"):
            # 儲存
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
    
    # 顯示摘要卡片
    with st.container():
        st.info("請確認以下資料無誤，按下送出後將自動寄發通知信。")
        st.markdown(f"""
        | 項目 | 內容 |
        |---|---|
        | **姓名** | {d.get('name')} |
        | **病歷號** | {d.get('id')} |
        | **追蹤期** | {d.get('followup')} |
        | **經血分數** | **{d.get('blood_score')}** 分 |
        | **經痛分數** | **{d.get('pain_val')}** 分 |
        | **頻尿分數** | **{d.get('udi_total')}** 分 |
        """)

    st.markdown("---")
    col_back, col_submit = st.columns([1, 1])
    
    with col_back:
        if st.button("⬅️ 返回修改"):
            prev_step()
            st.rerun()
    
    with col_submit:
        if st.button("✅ 確認送出 (Submit)"):
            with st.spinner("📩 正在處理資料並發送郵件..."):
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # 準備 Excel 資料 (DataFrame)
                raw_data = {
                    "病歷號碼": [d['id']],
                    "姓名": [d['name']],
                    "出生年月日": [d['birth']],
                    "追蹤期間": [d['followup']],
                    "填寫時間": [now_str],
                    "經血分數(PBAC)": [d['blood_score']],
                    "經痛分數(VAS)": [d['pain_val']],
                    "頻尿分數(UDI)": [d['udi_total']],
                    # 將詳細資料組合成字串方便檢視
                    "經血明細": [f"Pad:{d['pl']}/{d['pm']}/{d['ph']}, Tam:{d['tl']}/{d['tm']}/{d['th']}, Clot:{d['cs']}/{d['cl']}"],
                    "頻尿明細": [str([d[f'udi_{i}'] for i in range(6)])]
                }
                df = pd.DataFrame(raw_data)
                
                # 寄信
                filename = f"{d['name']}_{d['followup']}_Report.xlsx"
                email_content = f"""
                <h3>長庚海扶中心 - 問卷回覆通知</h3>
                <p><b>姓名：</b>{d['name']}</p>
                <p><b>病歷號：</b>{d['id']}</p>
                <p><b>追蹤期間：</b>{d['followup']}</p>
                <p><b>總結分數：</b>經血 {d['blood_score']} / 經痛 {d['pain_val']} / 頻尿 {d['udi_total']}</p>
                <p>詳細數據請查閱附件 Excel。</p>
                <br>
                <p><i>此信件由系統自動發送</i></p>
                """
                
                success = send_email_via_gmail(
                    subject=f"【問卷】{d['name']} - {d['followup']}",
                    content=email_content,
                    df=df,
                    filename=filename
                )
                
                if success:
                    st.success("✅ 問卷已成功送出！郵件已發送至中心信箱。")
                    st.balloons()
                    if st.button("填寫下一位患者"):
                        reset_app()
                        st.rerun()
                else:
                    st.error("❌ 傳送失敗，請確認網路連線或聯繫管理員。")
