import openpyxl
from datetime import datetime

print("=== INSERIMENTO NUOVA NOTA SPESE ===")

# 1. Chiediamo i dati in input
# Se premi solo 'Invio', prende in automatico la data di oggi
data_input = input("Data (premi Invio per usare la data di oggi, o scrivi GG/MM/AAAA): ")
if data_input == "":
    data = datetime.now().strftime("%d/%m/%Y")
else:
    data = data_input

motivazione = input("Motivazione della spesa (es. Pranzo cliente Rossi): ")

# Sostituiamo la virgola con il punto nel caso lo scrivessi "all'italiana" (es. 15,50 -> 15.50)
importo_input = input("Importo in Euro (es. 15.50): ")
importo_input = importo_input.replace(",", ".") 
importo = float(importo_input)

# 2. Impostiamo il nome del file Excel che l'azienda ti ha dato
# IMPORTANTE: Metti il tuo file Excel nella stessa cartella di questo script!
nome_file_excel = "modello_spese.xlsx"

try:
    # 3. Apriamo il file Excel
    workbook = openpyxl.load_workbook(nome_file_excel)
    foglio = workbook.active # Prende il primo foglio di lavoro
    
    # 4. Troviamo la prima riga vuota nel file per non sovrascrivere i dati vecchi
    riga_vuota = foglio.max_row + 1
    
    # 5. Inseriamo i dati nelle colonne corrispondenti
    # Facciamo finta che la colonna A sia la Data, la B la Motivazione, la C l'Importo
    foglio[f"A{riga_vuota}"] = data
    foglio[f"B{riga_vuota}"] = motivazione
    foglio[f"C{riga_vuota}"] = importo
    
    # 6. Salviamo il file
    workbook.save(nome_file_excel)
    
    print(f"\n✅ Fatto! Spesa di {importo}€ per '{motivazione}' aggiunta al file con successo.")
    
except FileNotFoundError:
    print(f"\n❌ ERRORE: Non trovo il file '{nome_file_excel}'. Assicurati che sia nella stessa cartella del file spese.py!")
except ValueError:
    print("\n❌ ERRORE: Hai inserito un importo non valido. Usa solo numeri.")