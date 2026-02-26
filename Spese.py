import streamlit as st
import openpyxl
from openpyxl.styles import Font, Border, Side
from io import BytesIO
import datetime
import requests
import json
from fpdf import FPDF  # La libreria magica per i PDF

# --- 1. CONFIGURAZIONE CLOUD E CHIAVI ---
try:
    BIN_ID = st.secrets["JSONBIN_ID"]
    API_KEY = st.secrets["JSONBIN_KEY"]
    IMGBB_KEY = st.secrets["IMGBB_KEY"] # 🟢 NUOVA CHIAVE PER LE FOTO
except KeyError:
    st.error("⚠️ Attenzione: Mancano alcune chiavi segrete in Streamlit Cloud (Settings > Secrets)!")
    st.stop()

URL_JSONBIN = f"https://api.jsonbin.io/v3/b/{BIN_ID}"
HEADERS = {
    "X-Master-Key": API_KEY,
    "Content-Type": "application/json"
}

# --- 2. FUNZIONI DI MEMORIA E FOTO ---
def salva_spese(lista_spese):
    dati_da_salvare = []
    for spesa in lista_spese:
        spesa_copia = spesa.copy()
        spesa_copia["data"] = spesa_copia["data"].strftime("%Y-%m-%d")
        dati_da_salvare.append(spesa_copia)
    try:
        requests.put(URL_JSONBIN, json=dati_da_salvare, headers=HEADERS)
    except Exception:
        pass

def carica_spese():
    try:
        risposta = requests.get(URL_JSONBIN, headers=HEADERS)
        if risposta.status_code == 200:
            dati_caricati = risposta.json().get("record", [])
            for spesa in dati_caricati:
                spesa["data"] = datetime.datetime.strptime(spesa["data"], "%Y-%m-%d").date()
            return dati_caricati
    except Exception:
        pass
    return []

# 🟢 NUOVO: Funzione per caricare la foto di nascosto su ImgBB
def carica_foto_imgbb(foto_bytes):
    url = "https://api.imgbb.com/1/upload"
    payload = {"key": IMGBB_KEY}
    files = {"image": foto_bytes}
    res = requests.post(url, data=payload, files=files)
    if res.status_code == 200:
        return res.json()["data"]["url"]
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

def elimina_spesa(indice):
    st.session_state.spese_settimana.pop(indice)
    salva_spese(st.session_state.spese_settimana)

# --- 4. INSERIMENTO DATI (CON FOTOCAMERA) ---
# Il parametro clear_on_submit=True svuota i campi dopo aver premuto il bottone
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
    # 🟢 NUOVO: La fotocamera per il telefono!
    foto_scontrino = st.camera_input("📸 Scatta foto allo scontrino (Opzionale)")
    
    submit = st.form_submit_button("➕ Aggiungi alla lista della settimana")

if submit:
    if motivazione == "" or importo is None or importo <= 0.0:
        st.warning("⚠️ Per favore, inserisci una motivazione e un importo maggiore di zero.")
    else:
        foto_url = None
        if foto_scontrino is not None:
            with st.spinner("⏳ Sto caricando la foto dello scontrino..."):
                foto_url = carica_foto_imgbb(foto_scontrino.getvalue())
        
        nuova_spesa = {
            "data": data_input,
            "motivazione": motivazione,
            "tipo": tipo_spesa,
            "importo": importo,
            "foto_url": foto_url # Salviamo il link della foto
        }
        st.session_state.spese_settimana.append(nuova_spesa)
        salva_spese(st.session_state.spese_settimana)
        st.success("✅ Spesa aggiunta alla lista!")
        st.rerun()

# --- 5. MOSTRA SPESE, EXCEL E PDF ---
if len(st.session_state.spese_settimana) > 0:
    st.markdown("---")
    st.markdown("### 🛒 Spese inserite finora:")
    
    for i, spesa in enumerate(st.session_state.spese_settimana):
        col_testo, col_bottone = st.columns([5, 1])
        with col_testo:
            # 🟢 Mostriamo l'icona della macchina fotografica se c'è uno scontrino
            icona = " 📷" if spesa.get("foto_url") else ""
            st.write(f"**{i+1}.** {spesa['data'].strftime('%d/%m/%Y')} - {spesa['motivazione']} | **{spesa['importo']:.2f}€**{icona}")
        with col_bottone:
            st.button("❌", key=f"elimina_{i}", on_click=elimina_spesa, args=(i,))

    totale_settimana = sum(spesa["importo"] for spesa in st.session_state.spese_settimana)
    st.markdown(f"## 💶 Totale Settimana: **{totale_settimana:.2f} €**")
    st.markdown("---")
    
    # ---------------- GENERAZIONE PDF ----------------
    spese_con_foto = [s for s in st.session_state.spese_settimana if s.get("foto_url") is not None]
    
    if len(spese_con_foto) > 0:
        if st.button("📄 Crea PDF degli Scontrini"):
            with st.spinner("⏳ Preparazione del PDF in corso..."):
                pdf = FPDF(orientation="L", unit="mm", format="A4") # L = Landscape (Orizzontale)
                
                # Dividiamo le foto a gruppi di 3
                for i in range(0, len(spese_con_foto), 3):
                    pdf.add_page()
                    pdf.set_font("Helvetica", size=10)
                    
                    gruppo_spese = spese_con_foto[i:i+3]
                    
                    x_start = 10  # Margine sinistro
                    larghezza_foto = 85  # Ogni foto prende 85mm
                    spazio = 10   # Spazio bianco tra una foto e l'altra
                    
                    for indice_foto, spesa_corrente in enumerate(gruppo_spese):
                        # Calcoliamo dove posizionare questa foto (asse X)
                        x_posizione = x_start + indice_foto * (larghezza_foto + spazio)
                        
                        # Scriviamo il testo sopra la foto
                        pdf.set_xy(x_posizione, 10)
                        testo_etichetta = f"{spesa_corrente['data'].strftime('%d/%m/%Y')} - {spesa_corrente['importo']} EUR"
                        pdf.cell(w=larghezza_foto, h=10, text=testo_etichetta, align="C")
                        pdf.set_xy(x_posizione, 15)
                        # Tagliamo la motivazione se è troppo lunga
                        mot_breve = spesa_corrente['motivazione'][:30]
                        pdf.cell(w=larghezza_foto, h=10, text=mot_breve, align="C")
                        
                        # Scarichiamo la foto da internet e la incolliamo
                        try:
                            req = requests.get(spesa_corrente["foto_url"])
                            img_bytes = BytesIO(req.content)
                            pdf.image(img_bytes, x=x_posizione, y=25, w=larghezza_foto)
                        except Exception:
                            pdf.set_xy(x_posizione, 50)
                            pdf.cell(w=larghezza_foto, h=10, text="Errore caricamento foto", align="C")

                # Generiamo il file PDF finito
                pdf_bytes = pdf.output()
                st.download_button(
                    label="⬇️ Scarica il file PDF",
                    data=bytes(pdf_bytes),
                    file_name="scontrini_settimana.pdf",
                    mime="application/pdf"
                )
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
        anno = prima_data.year
        testo_intestazione = f"COME DA ESTRATTI CONTO: settimana n. {numero_settimana} anno {anno}"
        
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
        
        st.download_button(
            label="⬇️ Scarica la Nota Spese in Excel",
            data=output_excel,
            file_name=f"nota_spese_settimana_{numero_settimana}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.markdown("---")
        with st.popover("🗑️ Svuota la intera lista e inizia una nuova settimana"):
            st.warning("⚠️ Sei sicuro? Cancellerà le spese inserite finora (le foto su ImgBB rimarranno salvate nei loro server, ma spariranno da questa app).")
            if st.button("Sì, cancella tutto", type="primary"):
                st.session_state.spese_settimana = []
                salva_spese([])
                st.success("Lista svuotata!")
                st.rerun()
            
    except FileNotFoundError:
        st.error("❌ ERRORE: Non trovo il file 'modello_spese.xlsx' su GitHub.")
