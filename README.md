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

운영 점검: `python -X utf8 monitor_archive.py`

- 스티비 공개 발행 목록과 공통 JSON·공개 HTML·사이트맵을 비교하며 최신 대표이미지, 수집 실패 및 6시간 이상 실행 중단도 확인합니다.
- 발행호·제목·검색용 HTML의 미반영은 첫 발견 후 90분의 유예를 둡니다. 일시적인 접근 오류는 30분 유예 후 경고합니다.
- 결과와 중복 알림 상태는 로컬 `.monitor/state.json`에 보관하며 Git에 올리지 않습니다. 파일을 지우면 누락 유예와 중복 방지 기록이 초기화됩니다.
- 실제 이메일 전송 완료 후에만 `python monitor_archive.py --ack-notification <fingerprint>`를 실행합니다. 전송 전에는 확인 처리하지 않습니다.
- 점검 스크립트 자체는 메일을 전송하지 않습니다. 연결된 Gmail과 Codex 정기 점검으로 발송하며, 로컬 점검은 컴퓨터와 앱이 실행 중이어야 합니다.
