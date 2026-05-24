#!/usr/bin/env python3
"""
EBS 라디오 자동 녹음 및 텔레그램 전송
- config.ini 하나로 모든 설정 관리
"""
import os, sys, subprocess, asyncio, logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pytz
import requests
from telegram import Bot

KST = pytz.timezone('Asia/Seoul')

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
log = logging.getLogger(__name__)

# ─── config.ini 파싱 ───────────────────────────────────────────

def load_config(path: str = None) -> dict:
    """config.ini를 읽어서 설정 반환"""
    if path is None:
        path = Path(__file__).parent / 'config.ini'
    else:
        path = Path(path)

    cfg = {'bot_token': '', 'chat_id': '', 'recordings_dir': Path('./recordings'),
           'streams': {'EBS': '', 'BANDI': ''}, 'programs': []}

    in_schedule = False
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()

        # 프로그램 스케줄 섹션
        if line.startswith('# --- 프로그램 스케줄'):
            in_schedule = True
            continue
        if in_schedule and line.startswith('# ---') and '프로그램' not in line:
            in_schedule = False
            continue

        if in_schedule:
            if not line or line.startswith('#'):
                continue
            # 헤더 줄 무시 (형식: 이 포함된 줄)
            if '형식:' in line:
                continue
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 6:
                cfg['programs'].append({
                    'name': parts[0],
                    'start': parts[1],
                    'end': parts[2],
                    'days': parts[3],
                    'type': parts[4],     # 정규 / 재방송
                    'source': parts[5],   # EBS / BANDI
                })
            continue

        # 키 = 값 파싱
        if '=' not in line or line.startswith('#'):
            continue
        key, val = line.split('=', 1)
        key = key.strip().lower()
        val = val.strip()

        if key == 'bot_token':
            cfg['bot_token'] = val
        elif key == 'chat_id':
            cfg['chat_id'] = val
        elif key == 'recordings_dir':
            cfg['recordings_dir'] = Path(val)
        elif key == 'ebs_fm':
            cfg['streams']['EBS'] = val
        elif key == 'bandi':
            cfg['streams']['BANDI'] = val

    return cfg

# ─── 요일 체크 ─────────────────────────────────────────────────

WEEKDAYS = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']

def day_matches(days_str: str, now_day: str) -> bool:
    days_str = days_str.upper().strip()
    if days_str == 'ALL':
        return True
    if '-' in days_str:
        s, e = days_str.split('-')
        return WEEKDAYS.index(s) <= WEEKDAYS.index(now_day) <= WEEKDAYS.index(e)
    return now_day in [d.strip() for d in days_str.split(',')]

# ─── 녹음 ───────────────────────────────────────────────────────

def should_record(prog: dict) -> tuple:
    """지금 녹음해야 하는지? → (bool, duration_sec)"""
    now = datetime.now(KST)
    if not day_matches(prog['days'], now.strftime('%a').upper()[:3]):
        return False, 0

    sh, sm = map(int, prog['start'].split(':'))
    eh, em = map(int, prog['end'].split(':'))
    start = KST.localize(now.replace(hour=sh, minute=sm, second=0, microsecond=0))
    end   = KST.localize(now.replace(hour=eh, minute=em, second=0, microsecond=0))
    if end <= start:
        end += timedelta(days=1)

    diff = (now - start).total_seconds()
    if -120 <= diff <= 120:
        return True, int((end - start).total_seconds())
    return False, 0


def existing_today(alias: str, rec_dir: Path) -> Optional[Path]:
    """오늘 이미 녹음된 파일 있는지"""
    date_str = datetime.now(KST).strftime('%y%m%d')
    safe_alias = alias.replace(' ', '_')
    fp = rec_dir / f"{date_str}-{safe_alias}.mp3"
    return fp if fp.exists() and fp.stat().st_size > 100000 else None


def record(stream_url: str, alias: str, duration: int, rec_dir: Path) -> Optional[Path]:
    date_str = datetime.now(KST).strftime('%y%m%d')
    safe_alias = alias.replace(' ', '_')
    fp = rec_dir / f"{date_str}-{safe_alias}.mp3"
    rec_dir.mkdir(parents=True, exist_ok=True)

    log.info(f"🎙 녹음 시작: {alias} ({duration}초)")
    try:
        r = subprocess.run([
            'ffmpeg', '-i', stream_url,
            '-t', str(duration),
            '-acodec', 'libmp3lame', '-ab', '64k', '-ar', '22050',
            '-y', str(fp)
        ], capture_output=True, text=True, timeout=duration + 60)

        if r.returncode != 0:
            log.error(f"ffmpeg 오류: {r.stderr[:300]}")
            return None
        log.info(f"✅ 녹음 완료: {fp.name} ({fp.stat().st_size//1024}KB)")
        return fp
    except Exception as e:
        log.error(f"녹음 오류: {e}")
        return None

# ─── 텔레그램 전송 ─────────────────────────────────────────────

async def send_telegram(fp: Path, prog: dict, token: str, chat_id: str):
    if not token or not chat_id:
        log.warning("텔레그램 설정 없음")
        return
    bot = Bot(token=token)
    now = datetime.now(KST)
    tag = " 🔄재방송" if prog['type'] == '재방송' else ""
    caption = f"📻 {prog['name']}\n📅 {now.strftime('%Y-%m-%d %H:%M')}{tag}"
    try:
        with open(fp, 'rb') as f:
            await bot.send_audio(chat_id=chat_id, audio=f,
                                 title=f"{prog['name']} - {now.strftime('%Y-%m-%d')}",
                                 caption=caption)
        log.info(f"📤 전송 완료: {fp.name}")
    except Exception as e:
        log.error(f"전송 오류: {e}")

# ─── 메인 ───────────────────────────────────────────────────────

def main():
    cfg = load_config()
    rec_dir = cfg['recordings_dir']

    if not cfg['programs']:
        log.info("등록된 프로그램이 없습니다 — config.ini를 확인하세요")
        return

    for prog in cfg['programs']:
        ok, dur = should_record(prog)
        if not ok:
            now = datetime.now(KST)
            log.info(f"⏭ {prog['name']} (지금 {now.strftime('%H:%M')} KST, 예정 {prog['start']})")
            continue

        alias = prog['name'].replace(' 재방송', '')
        stream_url = cfg['streams'].get(prog['source'], '')

        # 재방송이면 이미 파일 있는지 확인
        if prog['type'] == '재방송':
            exist = existing_today(alias, rec_dir)
            if exist:
                log.info(f"⏭ 재방송 스킵: {exist.name}")
                continue
            log.info(f"🔄 본방송 녹음 실패 → 재방송 녹음: {prog['name']}")

        fp = record(stream_url, alias, dur, rec_dir)
        if fp and fp.exists():
            asyncio.run(send_telegram(fp, prog, cfg['bot_token'], cfg['chat_id']))


if __name__ == '__main__':
    main()
