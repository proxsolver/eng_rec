# 📻 EBS 라디오 자동 녹음기

`config.ini` 하나만 수정하면 바로 사용 가능합니다.

## 빠른 시작

```bash
git clone https://github.com/YOUR_USERNAME/ebs-recorder.git
cd ebs-recorder
bash install.sh
# → config.ini에서 BOT_TOKEN, CHAT_ID 수정하라고 나오면
nano config.ini
bash install.sh   # 다시 실행
```

## 설정 — config.ini 만 수정하세요

```ini
# 텔레그램 — 이 두 줄만 수정!
BOT_TOKEN = 여기에_봇토큰_입력
CHAT_ID   = 여기에_챗아이디_입력

# 프로그램 스케줄 — 줄 추가/삭제로 자유롭게
# 형식: 이름 | 시작(KST) | 종료(KST) | 요일 | 정규/재방송 | 소스
Easy Writing         | 05:59 | 06:22 | MON-SAT | 정규   | EBS
Easy Writing 재방송  | 09:00 | 09:23 | MON-SAT | 재방송  | BANDI
입이 트이는 영어      | 06:20 | 06:40 | MON-SAT | 정규   | EBS
최수진의 모닝스페셜  | 08:00 | 08:20 | ALL     | 정규   | EBS

# 새 프로그램 추가 (앞에 # 지우면 활성화)
#새 프로그램 | 10:00 | 10:30 | MON-FRI | 정규 | EBS
```

### 프로그램 추가

한 줄만 추가하면 됩니다:

```
내 프로그램 | 14:00 | 14:30 | MON-FRI | 정규 | EBS
```

| 항목 | 설명 |
|------|------|
| 이름 | 아무 이름 |
| 시작/종료 | KST 기준 HH:MM |
| 요일 | `MON-FRI`, `MON-SAT`, `ALL`, `MON,WED,FRI` |
| 정규/재방송 | 재방송은 본방송 실패 시에만 녹음 |
| 소스 | `EBS` (FM) 또는 `BANDI` (반디 AOD) |

### 텔레그램 설정

1. @BotFather → `/newbot` → 토큰 발급
2. 봇에게 메시지 보내기
3. `https://api.telegram.org/bot<토큰>/getUpdates` → chat_id 확인
4. `config.ini`에 입력

## 파일 구조

```
ebs-recorder/
├── config.ini          ← 이것만 수정!
├── config.ini.example  ← 템플릿 (GitHub에 올라감)
├── record.py           ← 메인 로직
├── install.sh          ← 설치 스크립트
├── deploy/             ← systemd 파일
└── recordings/         ← 녹음 파일
```

## 수동 실행 / 로그

```bash
.venv/bin/python record.py                  # 수동 실행
sudo journalctl -u ebs-record.service -f    # 로그
```

## 요구사항

- Linux (Ubuntu 20.04+, Amazon Linux 2023)
- Python 3.9+
- ffmpeg
