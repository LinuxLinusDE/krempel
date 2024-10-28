#!/bin/bash

# Teams Webhook-URL hier einfügen
WEBHOOK_URL="XXXXXXX"

# Nachricht, die an Teams gesendet werden soll
MESSAGE="Hallo, dies ist eine Testnachricht von meinem Bash-Skript!"

# JSON-Daten erstellen
JSON_PAYLOAD=$(cat <<EOF
{
       "type":"message",
       "attachments":[
          {
             "contentType":"application/vnd.microsoft.card.adaptive",
             "contentUrl":null,
             "content":{
                "$schema":"http://adaptivecards.io/schemas/adaptive-card.json",
                "type":"AdaptiveCard",
                "version":"1.2",
                "body":[
                    {
                    "type": "TextBlock",
                    "text": "Text 123"
                    }
                ]
             }
          }
       ]
    }
EOF
)

# Nachricht an MS Teams senden
curl -H "Content-Type: application/json" -d "$JSON_PAYLOAD" "$WEBHOOK_URL"
