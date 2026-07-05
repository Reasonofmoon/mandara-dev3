---
id: PB-VF-05
purpose: API 멱등성 구현이 중복 요청을 안전하게 처리하는지 검증
applies_when: 멱등성 문제(F-05) 수정을 적용한 뒤 재시도·동시성·중복 방지를 확인할 때
version: "1.1"
---

# API 멱등성 구현 검증

Idempotency-Key, DB 유니크 제약, 재시도 로직을 구현한 뒤, 동일 키의 반복 요청이 단 하나의 리소스만 생성하고 재시도·동시 요청 상황에서도 부작용(중복 결제·중복 주문)이 없는지 확인하는 검증 프롬프트입니다.

## 용도

F-05 플로우의 6단계(수정) 이후, 순차 반복·동시 병렬·네트워크 실패 재시도 시나리오에서 멱등성이 보장되는지 부하 관점으로 검증합니다.

## 적용 시점

- Idempotency-Key 미들웨어를 추가한 직후
- 주문/결제 등 부작용 있는 엔드포인트를 수정한 직후
- 클라이언트 재시도(지수 백오프) 로직을 도입한 뒤

## 필수 입력

- 대상 엔드포인트와 멱등성 키 전달 방식
- 부작용 리소스(주문/결제 등)와 유니크 제약 컬럼
- 재시도 정책 (최대 횟수, 백오프)

## 프롬프트 템플릿

아래 멱등성 구현에 대해 중복 방지와 재시도 안전성을 검증하고 회귀가 없는지 확인해줘.

**엔드포인트:** [POST /api/orders]
**멱등성 키:** [Idempotency-Key 헤더]

1. **성공 기준 정의**
   - 동일 키 N회 요청 → 리소스 1개만 생성
   - 재요청 응답에 `Idempotency-Replay: true`
   - 서로 다른 키 → 각각 별도 리소스
   - DB에 idempotency_key 유니크 제약 존재

2. **재시도/동시성 테스트 매트릭스**
   | 시나리오 | 요청 방식 | 기대 생성 수 | 결과 |
   |---------|----------|-------------|------|
   | 순차 반복(동일 키 3회) | 직렬 | 1 | |
   | 동시 병렬(동일 키 5개) | 병렬 | 1 (경쟁 조건 방어) | |
   | 네트워크 실패 후 재시도 | 지수 백오프 | 1 | |
   | 다른 키 3개 | 직렬 | 3 | |

3. **동시성(경쟁 조건) 검증**
   ```bash
   # 동일 키로 5개 병렬 발사 → 주문 1개만 생성되어야 함
   for i in {1..5}; do
     curl -s -X POST http://localhost:3001/api/orders \
       -H "Idempotency-Key: race-key-1" \
       -H "Content-Type: application/json" \
       -d '{"items":[1,2,3],"amount":100}' &
   done; wait
   ```
   - DB에서 `SELECT count(*) WHERE idempotency_key='race-key-1'` = 1 확인

4. **자동화 테스트**
   ```javascript
   it('동일 키 반복 요청은 같은 리소스를 반환한다', async () => {
     const h = { 'Idempotency-Key': 'test-1', 'Content-Type': 'application/json' };
     const body = JSON.stringify({ amount: 100 });
     const a = await (await fetch(URL, { method: 'POST', headers: h, body })).json();
     const r = await fetch(URL, { method: 'POST', headers: h, body });
     const b = await r.json();
     expect(a.id).toBe(b.id);
     expect(r.headers.get('Idempotency-Replay')).toBe('true');
   });
   ```

5. **모니터링 지표**
   - 멱등 replay 발생 건수 로깅
   - 유니크 제약 위반 에러가 500이 아닌 정상 재사용으로 처리되는지
   - 키 저장소(Redis) TTL 만료 이후 동작 확인

## 출력 계약

```
검증 결과: [통과 / 실패]
- 순차 반복: [1개 생성]
- 동시 병렬: [1개 생성 / 경쟁조건 실패]
- 재시도: [중복 없음]
- Replay 헤더: [정상]
- DB 유니크 제약: [존재 / 없음]
```

## 셀프 체크리스트

- [ ] 순차뿐 아니라 동시 병렬 요청도 테스트했는가?
- [ ] DB 레벨 유니크 제약으로 최종 방어선을 두었는가?
- [ ] 재시도 시 동일 키를 재사용하는지 확인했는가?
- [ ] replay 응답과 헤더가 올바른가?
- [ ] 키 저장소 TTL 만료 후 동작을 고려했는가?
