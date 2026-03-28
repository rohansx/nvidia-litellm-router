#!/usr/bin/env bash
# Demo script for asciinema recording
# Usage: asciinema rec demo.cast -c ./demo.sh

set -e

PROXY="http://localhost:4000"
KEY="sk-litellm-master"

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

type_slow() {
    local text="$1"
    for ((i=0; i<${#text}; i++)); do
        printf '%s' "${text:$i:1}"
        sleep 0.03
    done
    echo
}

pause() { sleep "${1:-1.5}"; }

header() {
    echo
    echo -e "${BOLD}${CYAN}$1${NC}"
    echo -e "${DIM}$(printf '─%.0s' $(seq 1 ${#1}))${NC}"
    pause 0.5
}

query_model() {
    local model="$1"
    local prompt="$2"
    local start end elapsed response routed content

    start=$(date +%s%N)
    response=$(curl -s "$PROXY/v1/chat/completions" \
        -H "Authorization: Bearer $KEY" \
        -H "Content-Type: application/json" \
        -d "{\"model\": \"$model\", \"messages\": [{\"role\": \"user\", \"content\": \"$prompt\"}], \"max_tokens\": 60, \"temperature\": 0.1}")
    end=$(date +%s%N)
    elapsed=$(( (end - start) / 1000000 ))

    routed=$(echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('model','?'))" 2>/dev/null || echo "error")
    content=$(echo "$response" | python3 -c "
import sys,json
d=json.load(sys.stdin)
if 'choices' in d:
    text = d['choices'][0]['message']['content'].strip().replace('\n',' ')[:120]
    print(text)
else:
    print('ERROR: ' + d.get('error',{}).get('message','unknown')[:80])
" 2>/dev/null || echo "parse error")

    echo -e "  ${GREEN}Model:${NC}    $model"
    echo -e "  ${GREEN}Routed:${NC}   $routed"
    echo -e "  ${GREEN}Latency:${NC}  ${elapsed}ms"
    echo -e "  ${GREEN}Response:${NC} ${content}"
    echo
}

# ── Start ──

clear
echo
echo -e "${BOLD}${YELLOW}  nvidia-litellm-router${NC}"
echo -e "${DIM}  Auto-route across 31 free NVIDIA NIM models${NC}"
echo -e "${DIM}  github.com/rohansx/nvidia-litellm-router${NC}"
pause 2

# ── Step 1: Show setup ──

header "1. Generate config from NVIDIA API"
type_slow "$ python setup.py"
pause 0.5
set -a && source .env && set +a
python setup.py 2>&1 | grep -E '^\[' | head -6
pause 2

# ── Step 2: Show proxy is running ──

header "2. Proxy running on localhost:4000"
type_slow "$ curl localhost:4000/health/liveliness"
curl -s "$PROXY/health/liveliness"
echo
pause 1.5

# ── Step 3: Test all tiers ──

header "3. Testing all 5 model tiers"

echo -e "\n${YELLOW}nvidia-auto${NC} — routes to fastest across ALL models"
query_model "nvidia-auto" "What is 2+2? Answer in one word."
pause 1

echo -e "${YELLOW}nvidia-coding${NC} — coding specialists"
query_model "nvidia-coding" "Write a Python one-liner to reverse a string."
pause 1

echo -e "${YELLOW}nvidia-reasoning${NC} — reasoning models"
query_model "nvidia-reasoning" "What is 15% of 240? Show just the answer."
pause 1

echo -e "${YELLOW}nvidia-fast${NC} — small efficient models"
query_model "nvidia-fast" "Say hello in one word."
pause 1

echo -e "${YELLOW}nvidia-general${NC} — balanced all-rounders"
query_model "nvidia-general" "Name one planet in our solar system."
pause 1

# ── Step 4: Direct model access ──

header "4. Direct model access"
echo -e "${YELLOW}kimi-k2-instruct${NC} — Moonshot Kimi K2"
query_model "kimi-k2-instruct" "Write a bash one-liner to count files in current dir."
pause 2

# ── Done ──

header "Done!"
echo -e "  31 models | 5 tiers | latency-based routing | automatic failover"
echo -e "  ${DIM}All free. Zero cost.${NC}"
echo
pause 3
