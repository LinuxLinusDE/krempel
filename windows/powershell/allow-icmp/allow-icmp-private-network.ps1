# Name der Regeln
$ruleNameICMPv4 = "Erlaube ICMPv4 (Ping) für private Netzwerke"
$ruleNameICMPv6 = "Erlaube ICMPv6 (Ping) für private Netzwerke"

# ICMPv4 für eingehenden Verkehr auf privaten Netzwerken erlauben
New-NetFirewallRule -DisplayName $ruleNameICMPv4 `
                    -Direction Inbound `
                    -Protocol ICMPv4 `
                    -Action Allow `
                    -Profile Private `
                    -Description "Erlaubt eingehenden ICMPv4-Verkehr (Ping) für private Netzwerke"

# ICMPv6 für eingehenden Verkehr auf privaten Netzwerken erlauben
New-NetFirewallRule -DisplayName $ruleNameICMPv6 `
                    -Direction Inbound `
                    -Protocol ICMPv6 `
                    -Action Allow `
                    -Profile Private `
                    -Description "Erlaubt eingehenden ICMPv6-Verkehr (Ping) für private Netzwerke"
