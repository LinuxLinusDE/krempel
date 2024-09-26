#!/bin/bash

# Pfad zur authorized_keys Datei des root-Benutzers
AUTHORIZED_KEYS="/root/.ssh/authorized_keys"

# Dein öffentlicher SSH-Schlüssel
SSH_KEY="DEIN_SSH_KEY"

# Prüfen, ob die authorized_keys Datei existiert, wenn nicht, erstelle sie
if [ ! -f "$AUTHORIZED_KEYS" ]; then
    echo "authorized_keys Datei nicht gefunden, erstelle sie..."
    mkdir -p /root/.ssh
    touch "$AUTHORIZED_KEYS"
    chmod 600 "$AUTHORIZED_KEYS"
fi

# Prüfen, ob der SSH-Schlüssel bereits in der authorized_keys Datei enthalten ist
if grep -Fxq "$SSH_KEY" "$AUTHORIZED_KEYS"; then
    echo "Der SSH-Schlüssel ist bereits in der authorized_keys Datei vorhanden."
else
    echo "SSH-Schlüssel nicht gefunden, füge ihn hinzu..."
    echo "$SSH_KEY" >> "$AUTHORIZED_KEYS"
    chmod 600 "$AUTHORIZED_KEYS"
    echo "SSH-Schlüssel erfolgreich hinzugefügt."
fi
