import streamlit as st
import openpyxl
from openpyxl.styles import Font
from io import BytesIO
import datetime

# Impostazioni della pagina
st.set_page_config(page_title="Compilazione Note Spese", page_icon="💶")

# --- TRUCCHETTO CSS MIGLIORATO ---
st.markdown(
    """
    <style>
    div[data-testid="stTextInput"] div[data-baseweb="input"] > div,
    div[data-testid="stNumberInput"] div[data-baseweb="input"] > div {
        background-color: #e8f5e9 !important; 
    }
    
    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input {
        color: black !important;
        -webkit-text-fill-color: black !important;
        font-weight: bold;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("Gestione Nota Spese 📝")
st.write("Inserisci le spese man mano. Quando hai finito la settimana, scarica l'Excel completo.")

# --- LA MEMORIA DELL'APP ---
if "spese_settimana" not in st.session_state:
    st.session_state.spese_settimana = []

# Funzione per eliminare una singola spesa
def elimina_spesa(indice):
    st.session_state.spese_settimana.pop(indice)

# Creiamo un "Form" per inserire i dati
with st.form("form_spese"):
    data_input = st.date_input("Data della spesa", datetime.date.today())
    motivazione = st.text_input("Motivazione (es. Pranzo Cliente Rossi)")
    
    st.markdown("---")
    st.markdown("### Dettagli Importo")
    
    tipo_spesa = st.selectbox(
        "Seleziona la colonna di destinazione",
        options=[
            "Fatture - Carta di Credito Nominale (Colonna H)",
            "Scontrini - Carta di Credito Nominale (Colonna G)",
            "Scontrini - Contanti (Colonna C)",
            "Fatture - Contanti (Colonna D)",
            "Fatture - Bonifico (Colonna I)"
        ],
        index=0 
    )
    
    importo = st.number_input("Importo in Euro (€)", min_value=0.0, step=0.01, format="%.2f", value=None)
    submit = st.form_submit_button("➕ Aggiungi alla lista della settimana")

# Cosa succede quando premi il pulsante di aggiunta
if submit:
    if motivazione == "" or importo is None or importo <= 0.0:
        st.warning("⚠️ Per favore, inserisci una motivazione e un importo maggiore di zero.")
    else:
        nuova_spesa = {
            "data": data_input,
            "motivazione": motivazione,
            "tipo": tipo_spesa,
            "importo": importo
        }
        st.session_state.spese_settimana.append(nuova_spesa)
        st.success("✅ Spesa aggiunta alla lista!")
        st.rerun() # Ricarica per mostrare subito la nuova spesa

# --- MOSTRA LE SPESE E CREA L'EXCEL ---
if len(st.session_state.spese_settimana) > 0:
    st.markdown("---")
    st.markdown("### 🛒 Spese inserite finora:")
    
    # Mostra l'elenco delle spese con il pulsante di eliminazione
    for i, spesa in enumerate(st.session_state.spese_settimana):
        # Dividiamo lo spazio: il testo a sinistra, il bottone a destra
        col_testo, col_bottone = st.columns([5, 1])
        
        with col_testo:
            st.write(f"**{i+1}.** {spesa['data'].strftime('%d/%m/%Y')} - {spesa['motivazione']} | **{spesa['importo']}€** *(Destinazione: {spesa['tipo'].split(' (')[0]})*")
        
        with col_bottone:
            # Pulsante per eliminare questa specifica riga
            st.button("❌ Elimina", key=f"elimina_{i}", on_click=elimina_spesa, args=(i,))

    totale_settimana = sum(spesa["importo"] for spesa in st.session_state.spese_settimana)
    
    st.markdown("---")
    st.markdown(f"## 💶 Totale Settimana: **{totale_settimana:.2f} €**")
    st.markdown("---")
    
    try:
        workbook = openpyxl.load_workbook("modello_spese.xlsx")
        foglio = workbook.active
        
        # --- SPOSTA IN GIÙ TUTTO CIÒ CHE C'È DALLA RIGA 14 ---
        foglio.insert_rows(14, amount=3)
        
        # Gestione Intestazione
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

        # Inserimento spese dalla riga 4
        riga_corrente = 4
        font_normale = Font(bold=False)

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
                foglio[f"{col}{riga_corrente}"].font = font_normale
            
            riga_corrente += 1
        
        # --- SCRITTURA DEL TOTALE IN J17 ---
        foglio["J17"] = totale_settimana
        foglio["J17"].font = Font(bold=True)
            
        output = BytesIO()
        workbook.save(output)
        output.seek(0)
        
        st.download_button(
            label="⬇️ Scarica la Nota Spese Completa in Excel",
            data=output,
            file_name=f"nota_spese_settimana_{numero_settimana}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        if st.button("🗑️ Svuota la intera lista e inizia una nuova settimana"):
            st.session_state.spese_settimana = []
            st.rerun()
            
    except FileNotFoundError:
        st.error("❌ ERRORE: Non trovo il file 'modello_spese.xlsx'.")
