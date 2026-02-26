import streamlit as st
import openpyxl
from io import BytesIO
import datetime

# Impostazioni della pagina
st.set_page_config(page_title="Compilazione Note Spese", page_icon="💶")

st.title("Gestione Nota Spese 📝")
st.write("Inserisci i dati qui sotto per aggiornare il tuo file Excel.")

# Creiamo un "Form" per inserire tutti i dati insieme
with st.form("form_spese"):
    data_input = st.date_input("Data della spesa", datetime.date.today())
    motivazione = st.text_input("Motivazione (es. Pranzo Cliente Rossi)")
    
    st.markdown("---")
    st.markdown("### Dettagli Importo")
    
    # Questo banner evidenzia l'opzione usata il 95% delle volte
    st.info("💡 **Fatture - Carta di Credito Nominale** è selezionata di default!")
    
    tipo_spesa = st.selectbox(
        "Seleziona la colonna di destinazione",
        options=[
            "Fatture - Carta di Credito Nominale (Colonna H)", # Indice 0 = Default
            "Scontrini - Carta di Credito Nominale (Colonna G)",
            "Scontrini - Contanti (Colonna C)",
            "Fatture - Contanti (Colonna D)",
            "Fatture - Bonifico (Colonna I)"
        ],
        index=0 
    )
    
    importo = st.number_input("Importo in Euro (€)", min_value=0.0, step=0.01, format="%.2f")
    
    # Pulsante per inviare i dati
    submit = st.form_submit_button("Elabora e Crea Excel")

# Cosa succede quando premi il pulsante
if submit:
    if motivazione == "" or importo == 0.0:
        st.warning("⚠️ Per favore, inserisci una motivazione e un importo maggiore di zero.")
    else:
        try:
            # 1. Carica il file Excel
            workbook = openpyxl.load_workbook("modello_spese.xlsx")
            foglio = workbook.active
            
            # 2. Trova la prima riga vuota a partire dalla riga 3
            riga_vuota = 3
            while foglio[f"A{riga_vuota}"].value is not None:
                riga_vuota += 1
            
            # 3. Inserimento di Data (Col A) e Motivazione (Col B)
            foglio[f"A{riga_vuota}"] = data_input.strftime("%d/%m/%Y")
            foglio[f"B{riga_vuota}"] = motivazione
            
            # 4. Inserimento dell'importo SOLO nella colonna scelta (le altre restano vuote)
            if "Colonna H" in tipo_spesa:
                foglio[f"H{riga_vuota}"] = importo
            elif "Colonna G" in tipo_spesa:
                foglio[f"G{riga_vuota}"] = importo
            elif "Colonna C" in tipo_spesa:
                foglio[f"C{riga_vuota}"] = importo
            elif "Colonna D" in tipo_spesa:
                foglio[f"D{riga_vuota}"] = importo
            elif "Colonna I" in tipo_spesa:
                foglio[f"I{riga_vuota}"] = importo
            
            # 5. Inserimento dello STESSO importo nella colonna J (Totale di riga)
            foglio[f"J{riga_vuota}"] = importo
            
            # 6. Salva il file nella memoria temporanea per il download
            output = BytesIO()
            workbook.save(output)
            output.seek(0)
            
            st.success(f"✅ Fatto! Spesa di {importo}€ inserita correttamente alla riga {riga_vuota}.")
            
            # 7. Crea il pulsante per scaricare il file aggiornato
            st.download_button(
                label="⬇️ Clicca qui per scaricare l'Excel aggiornato",
                data=output,
                file_name="modello_spese_aggiornato.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
        except FileNotFoundError:
            st.error("❌ ERRORE: Non trovo il file 'modello_spese.xlsx'. Assicurati che sia presente e si chiami esattamente così.")
