# MOVIERADAR

영화 정보를 수집하고 장르, 감독, 배우, 수상, 박스오피스별 트렌드를 분석합니다.

## STRUCTURE

```
MovieRadar/
├── movieradar/
│   ├── collector.py              # collect_sources() — 씨네21, KOFIC RSS 수집
│   ├── analyzer.py               # apply_entity_rules() — 장르, 감독, 배우 키워드 매칭
│   ├── reporter.py               # generate_report() — Jinja2 HTML (radar-core 위임)
│   ├── storage.py                # RadarStorage — DuckDB upsert/query/retention (radar-core 위임)
│   ├── models.py                 # Source, Article, EntityDefinition, CategoryConfig (radar-core 재사용)
│   ├── config_loader.py          # YAML 로딩
│   ├── logger.py                 # structlog 구조화 로깅
│   ├── resilience.py             # 서킷 브레이커 패턴
│   └── exceptions.py             # 커스텀 예외 클래스
├── config/
│   ├── config.yaml               # database_path, report_dir
│   └── categories/movie.yaml     # 소스 + 엔티티 정의
├── data/                         # DuckDB, crawl health 데이터
├── reports/                      # 생성된 HTML 리포트
├── tests/                        # pytest 단위 테스트
├── main.py                       # CLI 엔트리포인트
└── .github/workflows/radar-crawler.yml
```

## ENTITIES

| Entity | Examples |
|--------|----------|
| 장르 | 액션, 드라마, 코미디, 스릴러, SF, 공포, 로맨스, 판타지, 애니메이션 |
| 감독 | 봉준호, 박찬욱, 이창동, 최동훈, Spielberg, Nolan, Tarantino |
| 배우 | 송강호, 전도연, 이병헌, 하정우, 마동석, 공유, 김태리 |
| 수상/영화제 | 칸, 베니스, 아카데미, 오스카, 부산국제영화제, 청룡영화상 |
| 박스오피스 | 관객수, 흥행, 개봉, 천만, 스크린수, 예매율, CGV, 롯데시네마 |
| 제작사/배급사 | CJ ENM, 쇼박스, Disney, Warner Bros, Universal, A24 |
| OTT/플랫폼 | 넷플릭스, 웨이브, 왓챠, 쿠팡플레이, 티빙, 디즈니플러스 |

## DEVIATIONS FROM TEMPLATE

- **radar-core 의존성**: 모델, 스토리지, 분석, 리포트 생성 로직을 radar-core 공유 라이브러리에서 가져옴
- **적응형 스로틀링**: AdaptiveThrottler로 소스별 요청 간격을 동적 조정
- **서킷 브레이커**: 장애 소스를 자동으로 격리하여 전체 파이프라인 안정성 확보
- **크롤 헬스 추적**: CrawlHealthStore로 소스별 성공/실패율 모니터링 및 자동 비활성화
- **글로벌 영화 매체**: Variety, Hollywood Reporter, Deadline, IndieWire 등 할리우드 뉴스 수집
- **박스오피스 데이터**: KOFIC, Box Office Mojo JavaScript 크롤링 지원
- **MCP 서버 통합**: 한국 관광 문화행사 MCP, 서울 문화행사 MCP를 통한 문화 이벤트 수집
- **OTT 뉴스**: What's on Netflix, Decider 등 스트리밍 플랫폼 뉴스 모니터링

## COMMANDS

```bash
python main.py --category movie --recent-days 7
python main.py --category movie --per-source-limit 50 --keep-days 90
```

## 주의사항

- **DuckDB 스키마 변경 금지**: radar-core와 호환성 유지 필요
- **`generate_report()` 함수 시그니처 변경 금지**: 다른 Radar 프로젝트와 공유
- **config/categories/movie.yaml 수정 시**: 엔티티 키워드 추가는 가능하나 구조 변경은 신중히
- **collector.py 수집 로직**: RSS 피드 파싱 로직은 feedparser 라이브러리에 의존
- **JavaScript 크롤링**: Playwright 기반으로 KOFIC, Box Office Mojo 등 동적 페이지 수집
