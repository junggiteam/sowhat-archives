# 쏘왓레터 모아보기

`sowhat.bestexit.co.kr` 전용 공개 아카이브입니다. 대표이미지·제목·호수·발행일 카드와 기존 구독폼을 제공합니다.

- 스티비 공개 아카이브: https://page.stibee.com/archives/479387
- 공통 메타데이터: `junggiteam/naver-news`의 `data/sowhat_archive.json`
- 새 발행호는 브라우저의 공통 데이터 갱신으로 추가됩니다.
- 보조 워크플로가 30분 간격으로 초기 HTML도 갱신해 검색엔진이 새 카드 링크를 직접 읽을 수 있게 합니다. GitHub 일정 실행에는 지연이 있을 수 있습니다.
- 공개 저장소, 표준 Linux 실행기, GitHub Pages만 사용하며 유료 API·유료 플랜·구독자 DB를 사용하지 않습니다.
- 구독은 기존 스티비 구독폼에서 처리합니다. 이 저장소에는 신청자의 개인정보를 저장하지 않습니다.

로컬 빌드: `python build_site.py`

공개 데이터 갱신 후 빌드: `python build_site.py --refresh`
