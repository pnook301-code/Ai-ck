#!/bin/bash
# CK-NEXUS Free Helper - ระบบผู้ช่วยฟรี
# ไม่ต้องใช้ API Key ใดๆ

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

case "${1:-help}" in
    weather)
        city="${2:-Bangkok}"
        curl -s "wttr.in/${city}?format=%l:+%c+%t+%h+%w" 2>/dev/null
        ;;
    ip)
        curl -s ifconfig.me 2>/dev/null
        ;;
    ping)
        host="${2:-google.com}"
        ping -c 4 "$host" 2>/dev/null | tail -1
        ;;
    disk)
        df -h / | awk 'NR==2{print "Used:", $3, "/ Free:", $4, "/ Total:", $2}'
        ;;
    mem)
        free -h | awk 'NR==2{print "Used:", $3, "/ Free:", $4, "/ Total:", $2}'
        ;;
    cpu)
        top -bn1 | grep "Cpu(s)" | awk '{print $2"% used"}'
        ;;
    ports)
        ss -tlnp 2>/dev/null | grep LISTEN | awk '{print $4}' | sort -u
        ;;
    processes)
        ps aux --sort=-%mem | head -10
        ;;
    network)
        echo -e "${CYAN}Network Info:${NC}"
        echo "IP: $(curl -s ifconfig.me)"
        echo "Gateway: $(ip route | grep default | awk '{print $3}')"
        echo "DNS: $(cat /etc/resolv.conf | grep nameserver | head -1)"
        ;;
    crypto)
        curl -s "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd" 2>/dev/null | jq . 2>/dev/null
        ;;
    news)
        curl -s "https://newsapi.org/v2/top-headlines?country=th&pageSize=5&apiKey=demo" 2>/dev/null | jq -r '.articles[].title' 2>/dev/null
        ;;
    quote)
        curl -s "https://api.quotable.io/random" 2>/dev/null | jq -r '"\(.content) - \(.author)"' 2>/dev/null
        ;;
    translate)
        text="${2:-hello}"
        from="${3:-en}"
        to="${4:-th}"
        curl -s "https://translate.googleapis.com/translate_a/single?client=gtx&sl=${from}&tl=${to}&dt=t&q=${text}" 2>/dev/null | jq -r '.[0][0][0]' 2>/dev/null
        ;;
    color)
        for i in {0..255}; do printf "\x1b[38;5;${i}m%-3s " "$i"; ((i%8==7)) && echo; done
        ;;
    ascii)
        echo "  /\\_/\\  "
        echo " ( o.o ) "
        echo "  > ^ <  "
        echo " /|   |\\"
        echo "(_|   |_)"
        ;;
    timer)
        secs="${2:-60}"
        while [ $secs -gt 0 ]; do
            echo -ne "\rTime: $(($secs/60)):$(printf '%02d' $(($secs%60)))"
            sleep 1
            ((secs--))
        done
        echo -e "\n⏰ Done!"
        ;;
    help|*)
        echo -e "${GREEN}CK-NEXUS Free Helper${NC}"
        echo ""
        echo "Free tools (no API key needed):"
        echo "  weather [city]     - Weather forecast"
        echo "  ip                 - Your public IP"
        echo "  ping [host]        - Ping test"
        echo "  disk               - Disk usage"
        echo "  mem                - Memory usage"
        echo "  cpu                - CPU usage"
        echo "  ports              - Open ports"
        echo "  processes          - Top processes"
        echo "  network            - Network info"
        echo "  crypto             - Crypto prices"
        echo "  news               - Thai news"
        echo "  quote              - Random quote"
        echo "  translate [text]   - Translate (en->th)"
        echo "  color              - Color palette"
        echo "  ascii              - ASCII art"
        echo "  timer [seconds]    - Countdown timer"
        ;;
esac
