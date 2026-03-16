# MovieRadar - 영화 레이더

**🌐 Live Report**: https://ai-frendly-datahub.github.io/MovieRadar/

영화 정보를 수집·분석하는 레이더. 씨네21, KOFIC 박스오피스 데이터를 매일 수집하여 장르·감독·배우·수상·박스오피스별로 분류하고 GitHub Pages에 배포합니다.

## 개요

- **수집 소스**: 씨네21 뉴스, 씨네21 리뷰, KOFIC 박스오피스
- **분석 대상**: 장르(Genre), 감독(Director), 배우(Actor), 수상/영화제(Award), 박스오피스(BoxOffice)
- **출력**: GitHub Pages HTML 리포트 (Flatpickr 캘린더 + Chart.js 트렌드)

## 빠른 시작

```bash
pip install -e ".[dev]"
python main.py --once
```

## 구조

```
MovieRadar/
  movieradar/
    collector.py    # 씨네21·KOFIC RSS 수집
    analyzer.py     # 엔티티 분석 (radar-core 위임)
    storage.py      # DuckDB 저장 (radar-core 위임)
    reporter.py     # HTML 리포트 생성 (radar-core 위임)
  config/
    config.yaml             # database_path, report_dir
    categories/movie.yaml   # 수집 소스 + 엔티티 정의
  main.py           # CLI 진입점
  tests/            # 단위 테스트
```

## 설정

`config/config.yaml` 및 `config/categories/movie.yaml` 참조.

## 개발

```bash
pytest tests/ -v
```

## 스케줄

GitHub Actions로 매일 자동 수집 후 GitHub Pages 배포.
