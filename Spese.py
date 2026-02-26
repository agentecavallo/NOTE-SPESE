import streamlit as st
import openpyxl
from openpyxl.styles import Font
from io import BytesIO
import datetime

# Impostazioni della pagina
st.set_page_config(page_title="Compilazione Note Spese", page_icon="💶")

st.title("Gestione Nota Spese 📝")
st.write("Inserisci le spese man mano. Quando hai finito la settimana, scarica l'Excel completo.")

# --- LA MEMORIA DELL'APP ---
# Se è la prima volta che apriamo l'app, creiamo un "cassetto" vuoto per le spese
if "spese_settimana" not in st.session_state:
    st.session_state.spese_settimana = []

# Creiamo un "Form" per inserire i dati
with st.form("form_spese"):
    data_input = st.date_input("Data della spesa", datetime.date.today())
    motivazione = st.text_input("Motivazione (es. Pranzo Cliente Rossi)")
    
    st.markdown("---")
    st.markdown("### Dettagli Importo")
    
    st.info("💡 **Fatture - Carta di Credito Nominale** è selezionata di default!")
    
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
    
    importo = st.number_input("Importo in Euro (€)", min_value=0.0, step=0.01, format="%.2f")
    
    # Pulsante per salvare la spesa nella memoria
    submit = st.form_submit_button("➕ Aggiungi alla lista della settimana")

# Cosa succede quando premi il pulsante di aggiunta
if submit:
    if motivazione == "" or importo == 0.0:
        st.warning("⚠️ Per favore, inserisci una motivazione e un importo maggiore di zero.")
    else:
        # Creiamo un "pacchetto" con i dati della spesa e lo mettiamo nel cassetto
        nuova_spesa = {
            "data": data_input,
            "motivazione": motivazione,
            "tipo": tipo_spesa,
            "importo": importo
        }
        st.session_state.spese_settimana.append(nuova_spesa)
        st.success("✅ Spesa aggiunta alla lista!")

# --- MOSTRA LE SPESE E CREA L'EXCEL ---
# Se c'è almeno una spesa nel cassetto, facciamo vedere il riepilogo e il tasto di download
if len(st.session_state.spese_settimana) > 0:
    st.markdown("---")
    st.markdown("### 🛒 Spese inserite finora:")
    
    # Mostriamo un elenco puntato delle spese inserite
    for i, spesa in enumerate(st.session_state.spese_settimana):
        st.write(f"**{i+1}.** {spesa['data'].strftime('%d/%m/%Y')} - {spesa['motivazione']} | **{spesa['importo']}€** *(Destinazione: {spesa['tipo'].split(' (')[0]})*")

    st.markdown("---")
    
    # Prepariamo il file Excel dietro le quinte
    try:
        workbook = openpyxl.load_workbook("modello_spese.xlsx")
        foglio = workbook.active
        
        # Gestione Intestazione (usa la data della PRIMA spesa inserita)
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

        # Inseriamo tutte le spese partendo dalla riga 4
        riga_corrente = 4
        font_normale = Font(bold=False)

        for spesa in st.session_state.spese_settimana:
            foglio[f"A{riga_corrente}"] = spesa["data"].strftime("%d/%m/%Y")
            foglio[f"B{riga_corrente}"] = spesa["motivazione"]
            
            # Inserimento importo
            if "Colonna H" in spesa["tipo"]: foglio[f"H{riga_corrente}"] = spesa["importo"]
            elif "Colonna G" in spesa["tipo"]: foglio[f"G{riga_corrente}"] = spesa["importo"]
            elif "Colonna C" in spesa["tipo"]: foglio[f"C{riga_corrente}"] = spesa["importo"]
            elif "Colonna D" in spesa["tipo"]: foglio[f"D{riga_corrente}"] = spesa["importo"]
            elif "Colonna I" in spesa["tipo"]: foglio[f"I{riga_corrente}"] = spesa["importo"]
            
            # Totale di riga
            foglio[f"J{riga_corrente}"] = spesa["importo"]
            
            # Tolgo il neretto
            for col in ["A", "B", "C", "D", "G", "H", "I", "J"]:
                foglio[f"{col}{riga_corrente}"].font = font_normale
            
            # Passo alla riga successiva per la prossima spesa
            riga_corrente += 1
            
        # Salva in memoria
        output = BytesIO()
        workbook.save(output)
        output.seek(0)
        
        # Pulsante per scaricare
        st.download_button(
            label="⬇️ Scarica la Nota Spese Completa in Excel",
            data=output,
            file_name=f"nota_spese_settimana_{numero_settimana}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        # Bottone per azzerare tutto a fine settimana
        if st.button("🗑️ Svuota la lista e inizia una nuova settimana"):
            st.session_state.spese_settimana = []
            st.rerun() # Riavvia l'app per pulire lo schermo
            
    except FileNotFoundError:
        st.error("❌ ERRORE: Non trovo il file 'modello_spese.xlsx'.")
