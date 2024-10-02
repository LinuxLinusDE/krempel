# Name der Regeln
$ruleNameICMPv4 = "Erlaube ICMPv4 (Ping) für öffentliche Netzwerke"
$ruleNameICMPv6 = "Erlaube ICMPv6 (Ping) für öffentliche Netzwerke"

# ICMPv4 für eingehenden Verkehr auf öffentlichen Netzwerken erlauben
New-NetFirewallRule -DisplayName $ruleNameICMPv4 `
                    -Direction Inbound `
                    -Protocol ICMPv4 `
                    -Action Allow `
                    -Profile Public `
                    -Description "Erlaubt eingehenden ICMPv4-Verkehr (Ping) für öffentliche Netzwerke"

# ICMPv6 für eingehenden Verkehr auf öffentlichen Netzwerken erlauben
New-NetFirewallRule -DisplayName $ruleNameICMPv6 `
                    -Direction Inbound `
                    -Protocol ICMPv6 `
                    -Action Allow `
                    -Profile Public `
                    -Description "Erlaubt eingehenden ICMPv6-Verkehr (Ping) für öffentliche Netzwerke"
