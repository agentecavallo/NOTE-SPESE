import streamlit as st
import openpyxl
from openpyxl.styles import Font, Border, Side
from io import BytesIO
import datetime
import requests
import json
from fpdf import FPDF

# --- 1. CONFIGURAZIONE CLOUD E CHIAVI ---
try:
    BIN_ID = st.secrets["JSONBIN_ID"]
    API_KEY = st.secrets["JSONBIN_KEY"]
    IMGBB_KEY = st.secrets["IMGBB_KEY"]
except KeyError:
    st.error("⚠️ Attenzione: Mancano alcune chiavi segrete in Streamlit Cloud (Settings > Secrets)!")
    st.stop()

URL_JSONBIN = f"https://api.jsonbin.io/v3/b/{BIN_ID}"
HEADERS = {
    "X-Master-Key": API_KEY,
    "Content-Type": "application/json"
}

# --- 2. FUNZIONI DI MEMORIA (AGGIORNATE CON IL TRUCCHETTO DELLA SCATOLA) ---
def salva_spese(lista_spese):
    dati_da_salvare = []
    for spesa in lista_spese:
        spesa_copia = spesa.copy()
        spesa_copia["data"] = spesa_copia["data"].strftime("%Y-%m-%d")
        dati_da_salvare.append(spesa_copia)
        
    # 🟢 IL TRUCCO: Invece di mandare [], mandiamo {"spese": []}
    payload = {"spese": dati_da_salvare}
    
    try:
        res = requests.put(URL_JSONBIN, json=payload, headers=HEADERS, timeout=5)
        if res.status_code == 200:
            return True
        else:
            st.error(f"⚠️ Errore dal server JSONBin: {res.text}")
            return False
    except Exception as e:
        st.error(f"⚠️ Errore di connessione: {e}")
        return False

def carica_spese():
    try:
        risposta = requests.get(URL_JSONBIN, headers=HEADERS, timeout=5)
        if risposta.status_code == 200:
            record = risposta.json().get("record", {})
            
            # 🟢 Capisce sia il vecchio formato che la nuova "scatola"
            if isinstance(record, list):
                dati_caricati = record
            else:
                dati_caricati = record.get("spese", [])
                
            for spesa in dati_caricati:
                spesa["data"] = datetime.datetime.strptime(spesa["data"], "%Y-%m-%d").date()
            return dati_caricati
    except Exception:
        pass
    return []

def carica_foto_imgbb(foto_bytes):
    url = "https://api.imgbb.com/1/upload"
    payload = {"key": IMGBB_KEY}
    files = {"image": foto_bytes}
    try:
        res = requests.post(url, data=payload, files=files, timeout=10)
        if res.status_code == 200:
            return res.json()["data"]["url"]
    except Exception:
        pass
    return None

# --- 3. IMPOSTAZIONI PAGINA E GRAFICA ---
st.set_page_config(page_title="Compilazione Note Spese", page_icon="💶")

st.markdown(
    """
    <style>
    div[data-testid="stTextInput"] div[data-baseweb="input"] > div,
    div[data-testid="stNumberInput"] div[data-baseweb="input"] > div {
        background-color: #e8f5e9 !important; 
    }
    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input {
        color: black !important; -webkit-text-fill-color: black !important; font-weight: bold;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("Gestione Nota Spese 📝")

if "spese_settimana" not in st.session_state:
    st.session_state.spese_settimana = carica_spese()

# --- 4. INSERIMENTO DATI ---
with st.form("form_spese", clear_on_submit=True):
    data_input = st.date_input("Data della spesa", datetime.date.today())
    motivazione = st.text_input("Motivazione (es. Pranzo Cliente Rossi)")
    
    tipo_spesa = st.selectbox(
        "Seleziona la colonna di destinazione",
        ["Fatture - Carta di Credito Nominale (Colonna H)", "Scontrini - Carta di Credito Nominale (Colonna G)", 
         "Scontrini - Contanti (Colonna C)", "Fatture - Contanti (Colonna D)", "Fatture - Bonifico (Colonna I)"]
    )
    
    importo = st.number_input("Importo in Euro (€)", min_value=0.0, step=0.01, format="%.2f", value=None)
    
    st.markdown("---")
    foto_scontrino = st.camera_input("📸 Scatta foto allo scontrino (Opzionale)")
    
    submit = st.form_submit_button("➕ Aggiungi alla lista della settimana")

if submit:
    if motivazione == "" or importo is None or importo <= 0.0:
        st.warning("⚠️ Per favore, inserisci una motivazione e un importo maggiore di zero.")
    else:
        foto_url = None
        if foto_scontrino is not None:
            with st.spinner("⏳ Caricamento foto in corso..."):
                foto_url = carica_foto_imgbb(foto_scontrino.getvalue())
        
        nuova_spesa = {
            "data": data_input,
            "motivazione": motivazione,
            "tipo": tipo_spesa,
            "importo": importo,
            "foto_url": foto_url 
        }
        st.session_state.spese_settimana.append(nuova_spesa)
        
        with st.spinner("💾 Salvataggio nel cloud..."):
            successo = salva_spese(st.session_state.spese_settimana)
            
        if successo:
            st.rerun()

# --- 5. MOSTRA SPESE E PULSANTI ---
if len(st.session_state.spese_settimana) > 0:
    st.markdown("---")
    st.markdown("### 🛒 Spese inserite finora:")
    
    for i, spesa in enumerate(st.session_state.spese_settimana):
        col_testo, col_bottone = st.columns([5, 1])
        with col_testo:
            icona = " 📷" if spesa.get("foto_url") else ""
            st.write(f"**{i+1}.** {spesa['data'].strftime('%d/%m/%Y')} - {spesa['motivazione']} | **{spesa['importo']:.2f}€**{icona}")
        with col_bottone:
            if st.button("❌", key=f"del_btn_{i}"):
                # 🟢 Eliminiamo la riga solo se JSONBin ci dà l'ok!
                vecchia_lista = st.session_state.spese_settimana.copy()
                st.session_state.spese_settimana.pop(i)
                successo = salva_spese(st.session_state.spese_settimana)
                if successo:
                    st.rerun()
                else:
                    st.session_state.spese_settimana = vecchia_lista # Rimette la riga se c'è errore

    totale_settimana = sum(spesa["importo"] for spesa in st.session_state.spese_settimana)
    st.markdown(f"## 💶 Totale Settimana: **{totale_settimana:.2f} €**")
    st.markdown("---")
    
    # ---------------- GENERAZIONE PDF ----------------
    spese_con_foto = [s for s in st.session_state.spese_settimana if s.get("foto_url") is not None]
    
    if len(spese_con_foto) > 0:
        if st.button("📄 Crea PDF degli Scontrini"):
            with st.spinner("⏳ Preparazione del PDF in corso..."):
                pdf = FPDF(orientation="L", unit="mm", format="A4") 
                for i in range(0, len(spese_con_foto), 3):
                    pdf.add_page()
                    pdf.set_font("Helvetica", size=10)
                    gruppo_spese = spese_con_foto[i:i+3]
                    x_start, larghezza_foto, spazio = 10, 85, 10   
                    
                    for indice_foto, spesa_corrente in enumerate(gruppo_spese):
                        x_posizione = x_start + indice_foto * (larghezza_foto + spazio)
                        pdf.set_xy(x_posizione, 10)
                        testo_etichetta = f"{spesa_corrente['data'].strftime('%d/%m/%Y')} - {spesa_corrente['importo']} EUR"
                        pdf.cell(w=larghezza_foto, h=10, text=testo_etichetta, align="C")
                        pdf.set_xy(x_posizione, 15)
                        pdf.cell(w=larghezza_foto, h=10, text=spesa_corrente['motivazione'][:30], align="C")
                        
                        try:
                            req = requests.get(spesa_corrente["foto_url"], timeout=10)
                            img_bytes = BytesIO(req.content)
                            pdf.image(img_bytes, x=x_posizione, y=25, w=larghezza_foto)
                        except Exception:
                            pdf.set_xy(x_posizione, 50)
                            pdf.cell(w=larghezza_foto, h=10, text="Errore caricamento foto", align="C")

                pdf_bytes = pdf.output()
                st.download_button(label="⬇️ Scarica il file PDF", data=bytes(pdf_bytes), file_name="scontrini_settimana.pdf", mime="application/pdf")
        st.markdown("---")

    # ---------------- GENERAZIONE EXCEL ----------------
    try:
        workbook = openpyxl.load_workbook("modello_spese.xlsx")
        foglio = workbook.active
        foglio.insert_rows(14, amount=3)
        bordo_sottile = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        for riga in range(4, 17):
            for col in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]:
                foglio[f"{col}{riga}"].border = bordo_sottile
        
        prima_data = st.session_state.spese_settimana[0]["data"]
        numero_settimana = prima_data.isocalendar()[1]
        testo_intestazione = f"COME DA ESTRATTI CONTO: settimana n. {numero_settimana} anno {prima_data.year}"
        
        for col in range(3, 11): 
            cella = foglio.cell(row=1, column=col)
            if cella.value is not None and "COME DA ESTRATTI CONTO" in str(cella.value):
                cella.value = testo_intestazione
                cella.font = Font(bold=True)
                break
        else:
            foglio["E1"] = testo_intestazione
            foglio["E1"].font = Font(bold=True)

        riga_corrente = 4
        for spesa in st.session_state.spese_settimana:
            foglio[f"A{riga_corrente}"] = spesa["data"].strftime("%d/%m/%Y")
            foglio[f"B{riga_corrente}"] = spesa["motivazione"]
            if "Colonna H" in spesa["tipo"]: foglio[f"H{riga_corrente}"] = spesa["importo"]
            elif "Colonna G" in spesa["tipo"]: foglio[f"G{riga_corrente}"] = spesa["importo"]
            elif "Colonna C" in spesa["tipo"]: foglio[f"C{riga_corrente}"] = spesa["importo"]
            elif "Colonna D" in spesa["tipo"]: foglio[f"D{riga_corrente}"] = spesa["importo"]
            elif "Colonna I" in spesa["tipo"]: foglio[f"I{riga_corrente}"] = spesa["importo"]
            foglio[f"J{riga_corrente}"] = spesa["importo"]
            for col in ["A", "B", "C", "D", "G", "H", "I", "J"]:
                foglio[f"{col}{riga_corrente}"].font = Font(bold=False)
            riga_corrente += 1
        
        foglio["J17"] = totale_settimana
        foglio["J17"].font = Font(bold=True)
            
        output_excel = BytesIO()
        workbook.save(output_excel)
        output_excel.seek(0)
        
        st.download_button(label="⬇️ Scarica la Nota Spese in Excel", data=output_excel, file_name=f"nota_spese_settimana_{numero_settimana}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.markdown("---")
        
        st.warning("Vuoi azzerare la settimana?")
        if st.button("🗑️ Svuota la intera lista e inizia una nuova settimana", type="primary"):
            with st.spinner("⏳ Svuotamento del database in corso..."):
                # Mandiamo una lista vuota che il codice trasformerà in {"spese": []}
                successo = salva_spese([]) 
                if successo:
                    st.session_state.spese_settimana = []
                    st.rerun()
            
    except FileNotFoundError:
        st.error("❌ ERRORE: Non trovo il file 'modello_spese.xlsx' su GitHub.")
