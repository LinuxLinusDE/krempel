#!/bin/bash

# Logfile Pfad
LOGFILE="/var/log/checknetwork.log"

# Gateway IP-Adresse
GATEWAY="10.0.40.1"

# Ping Test
#ping -c 1 $GATEWAY > /dev/null 2>&1
ping -c 1 -w 10 $GATEWAY > /dev/null 2>&1

if [ $? -ne 0 ]; then
  # Falls das Gateway nicht erreichbar ist, Netzwerkkonfiguration neu starten
  echo "$(date): Gateway $GATEWAY nicht erreichbar. Netzwerkkonfiguration wird neu gestartet." >> $LOGFILE
  service networking restart
else
  echo "$(date): Gateway $GATEWAY ist erreichbar." >> $LOGFILE
