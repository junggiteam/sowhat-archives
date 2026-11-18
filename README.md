# 쏘왓레터 모아보기

`sowhat.bestexit.co.kr` 전용 공개 아카이브입니다. 대표이미지·제목·호수·발행일 카드와 기존 구독폼을 제공합니다.

- 스티비 공개 아카이브: https://page.stibee.com/archives/479387
- 공통 메타데이터: `junggiteam/naver-news`의 `data/sowhat_archive.json`
- 새 발행호는 브라우저의 공통 데이터 갱신으로 추가됩니다.
- 보조 워크플로가 30분 간격으로 초기 HTML도 갱신해 검색엔진이 새 카드 링크를 직접 읽을 수 있게 합니다. GitHub 일정 실행에는 지연이 있을 수 있습니다.
- 공개 저장소, 표준 Linux 실행기, GitHub Pages만 사용하며 유료 API·유료 플랜·구독자 DB를 사용하지 않습니다.
- 구독은 기존 스티비 구독폼에서 처리합니다. 이 저장소에는 신청자의 개인정보를 저장하지 않습니다.
- SEO: 월별 정적 페이지(`/2026/11/` 등), 월별 고유 제목·설명·canonical, 발행호 ItemList와 WebSite/Breadcrumb 구조화 데이터, 전체 월별 링크 및 자동 사이트맵을 생성합니다.
- 새 달의 발행호가 추가되면 월별 페이지와 사이트맵도 같은 자동 갱신 작업에서 생성됩니다. 검색엔진의 수집·색인 시점은 검색엔진이 결정합니다.
- 공유 이미지: `assets/sowhat-share.png` (1200×630). 원본 생성 코드는 `make_share_image.py`이며 로컬 Windows/Pillow로 렌더링합니다. 자동 갱신에는 Pillow가 필요 없습니다.
- 네이버 소유 확인용 공개 메타 태그는 `site-verification.json`에서 읽어 매번 생성합니다. 이 값은 공개 HTML에 게시하는 소유 확인 값이며 로그인 비밀키가 아닙니다.

로컬 빌드: `python build_site.py`

공개 데이터 갱신 후 빌드: `python build_site.py --refresh`

운영 점검과 이메일 알림은 GitHub Actions의 `Monitor So What archive`가 매시간 10분에 실행합니다. 컴퓨터와 Codex 앱은 꺼도 됩니다. GitHub 예약 실행은 혼잡 시 지연될 수 있습니다.

- 스티비 공개 발행 목록과 공통 JSON·공개 HTML·사이트맵을 비교하며 최신 대표이미지, 수집 실패 및 6시간 이상 실행 중단도 확인합니다.
- 발행호·제목·검색용 HTML의 미반영은 첫 발견 후 90분의 유예를 둡니다. 일시적인 접근 오류는 30분 유예 후 경고합니다.
- 실행 코드: `cloud_monitor.py`. Python 표준 라이브러리만 사용하며 AI 모델·OpenAI API·Codex 예약 작업을 호출하지 않습니다.
- GitHub의 공개 저장소와 표준 Linux 실행기만 사용합니다. 아티팩트 업로드·캐시·외부 DB·유료 메일 서비스를 사용하지 않습니다. GitHub의 공개 저장소 표준 실행기는 무료입니다: https://docs.github.com/en/billing/concepts/product-billing/github-actions
- 발송은 Gmail SMTP(인증서 검증을 사용하는 TLS)로 처리합니다. 주소와 앱 비밀번호는 Actions repository secrets의 `SOWHAT_SMTP_USERNAME`, `SOWHAT_SMTP_PASSWORD`, `SOWHAT_ALERT_TO`에서만 읽으며 공개 코드·상태 파일·실행 요약에 기록하지 않습니다.
- 결과·유예시간·중복 알림 기록은 사이트와 별개의 `monitor-state` 브랜치 `state.json`에 보관합니다. 공개 발행호와 실행 상태만 기록하며 구독자 데이터나 메일 인증정보는 넣지 않습니다. 상태 읽기에 실패하면 기존 기록을 초기화하지 않고 실행을 실패 처리합니다.
- SMTP가 수신자를 수락한 뒤에만 발송 완료를 기록합니다. 발송 실패 시 완료로 기록하지 않고 다음 실행에서 재시도합니다. SMTP 수락 직후 상태 저장까지 실패한 경우에는 재시도 시 같은 알림이 중복될 수 있습니다.
- 수동 발송 테스트: 저장소 Actions → Monitor So What archive → Run workflow → `send_test_email` 선택. 테스트도 GitHub 실행기에서 직접 발송하며, 같은 실행을 재실행할 때 이미 성공한 연결 테스트는 반복하지 않습니다.
- 기존 Codex 정기 점검은 중지했습니다. 로컬에서 메일 없이 상태만 확인하려면 `python -X utf8 monitor_archive.py`를 사용할 수 있습니다. 로컬 `.monitor/state.json`은 Git에 올리지 않습니다.
- 발행 일정: 한국시간 월~금 15:30~16:30, 토·일·공휴일 미발행. 점검은 스티비 공개 아카이브에 실제 추가된 발행호를 기준으로 비교하며, 오늘 새 호가 없다는 이유만으로 누락 경고를 만들지 않습니다.
