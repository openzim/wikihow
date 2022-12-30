# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
as of 1.2.0.

## [1.2.2] - 2022-12-30

### Added

- Global 15mn pause on 429 response (#142)

### Changed

- Making all requests through a single Session/connection pool
- External link icon now bundled in-repo (#138)
- More sophisticated requests-retry mechanism (#122)
- Increased tolerance to API's maxlag issue
- Updated zimscraperlib to 2.0.0

## [1.2.1] - 2022-08-03

## Changed

- Fixed adding homepage twice for langs using Main-Page (#132)
- Not failing on duplicate pages (#134)

## [1.2.0] - 2022-05-25

### Added

- `--missing-article-tolerance` option to define a percentage of allowed 404 articles (#125)

### Changed

- Increased (5 -> 10) number of retries on (non-api) request errors
- Prevented an infinite loop on multi-referenced subcat (#123)
- Decoding article names retrieved from the API (#124)
- Using scraperlib 1.6 (libzim 7.2)
- Default output dir (/output -> output)
- Adapted DOM Integrity Checker to EN's Top categories change (#129)
- In-review articles not considered missing (404) anymore (#130)

# [1.1.0]

- Revamped to work off an expected list of articles/categories fetched from API
- Fixed category page icon size (#106)
- Removed devel param --skip-relateds
- Added --api-delay option
- Using the previously unused --delay option
- Better exit upon errors (#105)

# [1.0.2]

- Allow creation of usable ZIM from single category using --category

# [1.0.1]

- Using pylibzim 1.0.0 and zimscraperlib 1.4.0
- Fixed crash on incorrect link during --exclude rewrite (#101)
- Removed a link to author on sidebar (#102)

# [1.0.0]

- initial version
