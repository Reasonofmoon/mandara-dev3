---
title: HTTP 상태 코드 전체 가이드
version: 1.0
---

# HTTP 상태 코드 전체 가이드

## 2xx - 성공

| 코드 | 의미 | 용도 |
|------|------|------|
| 200 | OK | 요청 성공 |
| 201 | Created | 리소스 생성 성공 |
| 202 | Accepted | 요청 수락됨 (처리 중) |
| 204 | No Content | 응답 본문 없음 |

## 3xx - 리다이렉트

| 코드 | 의미 | 용도 |
|------|------|------|
| 301 | Moved Permanently | 영구 이동 |
| 302 | Found | 임시 이동 |
| 304 | Not Modified | 캐시된 버전 사용 |
| 307 | Temporary Redirect | 메서드 유지 리다이렉트 |

## 4xx - 클라이언트 오류

| 코드 | 의미 | 용도 |
|------|------|------|
| 400 | Bad Request | 잘못된 요청 |
| 401 | Unauthorized | 인증 필요 |
| 403 | Forbidden | 접근 권한 없음 |
| 404 | Not Found | 리소스 없음 |
| 409 | Conflict | 충돌 (예: 중복) |
| 422 | Unprocessable Entity | 유효성 검사 실패 |
| 429 | Too Many Requests | 요청 한도 초과 |

## 5xx - 서버 오류

| 코드 | 의미 | 용도 |
|------|------|------|
| 500 | Internal Server Error | 서버 오류 |
| 501 | Not Implemented | 미구현 |
| 502 | Bad Gateway | 게이트웨이 오류 |
| 503 | Service Unavailable | 서비스 불가능 |
| 504 | Gateway Timeout | 타임아웃 |

