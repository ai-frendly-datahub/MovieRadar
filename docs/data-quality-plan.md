# Data Quality Plan

- 생성 시각: `2026-04-11T16:05:37.910248+00:00`
- 우선순위: `P2`
- 데이터 품질 점수: `77`
- 가장 약한 축: `권위성`
- Governance: `low`
- Primary Motion: `intelligence`

## 현재 이슈

- 가장 약한 품질 축은 권위성(62)

## 필수 신호

- 국내 예매 순위와 박스오피스
- OTT Top 10과 공개 일정
- 관객 평점·리뷰·배급사/스튜디오 정보

## 품질 게이트

- 작품명·개봉연도·국가를 canonical movie key로 유지
- 극장 흥행과 OTT 순위를 별도 레이어로 분리
- 예매일·개봉일·수집일을 별도 필드로 유지

## 다음 구현 순서

- 예매 순위, OTT Top 10, release calendar source를 추가
- movie title/year canonicalization rule을 추가
- 배급/편성 판단용 audience rating과 box office trend를 분리 출력

## 운영 규칙

- 원문 URL, 수집일, 이벤트 발생일은 별도 필드로 유지한다.
- 공식 source와 커뮤니티/시장 source를 같은 신뢰 등급으로 병합하지 않는다.
- collector가 인증키나 네트워크 제한으로 skip되면 실패를 숨기지 말고 skip 사유를 기록한다.
- 이 문서는 `scripts/build_data_quality_review.py --write-repo-plans`로 재생성한다.
