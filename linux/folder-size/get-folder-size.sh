#!/bin/bash

# CSV-Datei definieren
OUTPUT_FILE="download_sizes.csv"

# CSV-Header schreiben
echo "Benutzer,Download-Ordner-Größe (MB)" > "$OUTPUT_FILE"

# Initialisierung der Summe
total_size=0

# Durch alle Home-Verzeichnisse iterieren
for user_dir in /home/*; do
    # Benutzername extrahieren
    username=$(basename "$user_dir")

    # Download-Ordner Pfad
    download_dir="$user_dir/Files/Downloads"

    # Prüfen, ob der Ordner existiert
    if [[ -d "$download_dir" ]]; then
        # Größe des Download-Ordners in MB ermitteln
        size=$(du -sm "$download_dir" | awk '{print $1}')
        
        # Falls Ordner nicht leer, in CSV speichern
        if [[ $size -gt 0 ]]; then
            echo "$username,$size" >> "$OUTPUT_FILE"
            total_size=$((total_size + size))
        fi
    fi
done

# Gesamtgröße ans Ende der CSV anhängen
echo "Gesamt,$total_size" >> "$OUTPUT_FILE"

echo "Fertig! Die Datei $OUTPUT_FILE wurde erstellt."
