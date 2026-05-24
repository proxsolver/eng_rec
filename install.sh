#!/usr/bin/env bash
# 📻 영어 학습 녹음기 — 원클릭 설치
# 사용법: git clone <repo> && cd eng_rec && bash install.sh
set -e

echo "📻 영어 학습 자동 녹음기 설치"
echo "================================"

# 필수 확인
for cmd in python3 ffmpeg; do
    if ! command -v $cmd &> /dev/null; then
        echo "❌ $cmd 없음 → sudo apt install $cmd"
        exit 1
    fi
done
echo "✅ python3, ffmpeg 확인"

# config.ini 준비
if [ ! -f config.ini ]; then
    if [ -f config.ini.example ]; then
        cp config.ini.example config.ini
        echo ""
        echo "📝 config.ini 를 생성했습니다. BOT_TOKEN과 CHAT_ID를 입력하세요!"
        echo ""
        echo "    nano config.ini"
        echo ""
        echo "    BOT_TOKEN = 여기에_봇토큰_입력  ← 수정"
        echo "    CHAT_ID   = 여기에_챗아이디_입력  ← 수정"
        echo ""
        echo "수정 후 다시 bash install.sh 를 실행하세요."
        exit 0
    else
        echo "❌ config.ini.example 이 없습니다."
        exit 1
    fi
fi

# 토큰 확인
if grep -q '여기에_' config.ini; then
    echo "❌ config.ini에서 BOT_TOKEN / CHAT_ID를 먼저 수정하세요!"
    echo "   nano config.ini"
    exit 1
fi
echo "✅ config.ini 설정 확인"

# venv
python3 -m venv .venv
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet python-telegram-bot python-dotenv pytz requests httpx
echo "✅ Python 패키지 설치 완료"

mkdir -p recordings

# systemd 타이머
echo ""
echo "⏰ systemd 타이머 설치? [y/N]"
read -r ans
if [ "$ans" = "y" ] || [ "$ans" = "Y" ]; then
    DIR="$(cd "$(dirname "$0")" && pwd)"
    sed "s|__DIR__|$DIR|g" deploy/eng_rec.service > /tmp/eng_rec.service
    sudo cp /tmp/eng_rec.service /etc/systemd/system/
    sudo cp deploy/eng_rec.timer /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable --now eng_rec.timer
    echo "✅ 타이머 활성화 완료!"
fi

# 테스트
echo ""
echo "🧪 30초 테스트 녹음? [y/N]"
read -r ans
if [ "$ans" = "y" ] || [ "$ans" = "Y" ]; then
    source .venv/bin/activate
    ffmpeg -i "https://ebsonair.ebs.co.kr/fmradiofamilypc/familypc1m/playlist.m3u8" \
        -t 30 -acodec libmp3lame -ab 64k -ar 22050 -y recordings/test.mp3 2>/dev/null
    [ -f recordings/test.mp3 ] && echo "✅ 테스트 성공! $(du -h recordings/test.mp3 | cut -f1)" || echo "❌ 실패"
fi

echo ""
echo "🎉 완료!"
echo "   수동 실행: .venv/bin/python record.py"
echo "   스케줄 수정: nano config.ini"
