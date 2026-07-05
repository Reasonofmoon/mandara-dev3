---
id: E-RT-10
title: 메모리 누수
error_class: Runtime
symptoms:
  - 메모리 사용량 증가
  - 애플리케이션 느려짐
  - OOM 에러
exact_messages:
  - "FATAL ERROR: CALL_AND_RETRY_LAST Allocation failed"
  - "JavaScript heap out of memory"
  - "Cannot allocate memory"
tech_tags:
  - Memory Management
  - Garbage Collection
  - Profiling
  - Performance
linked_patterns: []
linked_flows: []
---

# 메모리 누수

## 증상
애플리케이션의 메모리 사용량이 지속적으로 증가하여 결국 OOM(Out of Memory)이 발생합니다. 이벤트 리스너, 타이머, 또는 큰 객체 참조가 정리되지 않을 때 발생합니다.

## 정확한 에러 메시지
```
FATAL ERROR: CALL_AND_RETRY_LAST Allocation failed
JavaScript heap out of memory
Cannot allocate memory
RangeError: Maximum call stack size exceeded
```

## 발생 맥락
```typescript
// 잘못된 예 1: 이벤트 리스너 미제거
element.addEventListener('click', handler);
// 요소 제거 후에도 listener 남음
element.remove();  // ❌ listener는 메모리에 남음

// 잘못된 예 2: 타이머 미해제
const timerId = setInterval(() => {
  console.log('tick');
}, 1000);
// ❌ clearInterval 호출 안 함

// 잘못된 예 3: 큰 객체 캐시
const cache = new Map();
function getData(key) {
  if (!cache.has(key)) {
    cache.set(key, largeObject);  // ❌ 계속 추가만 함
  }
  return cache.get(key);
}

// 잘못된 예 4: 순환 참조
class Node {
  next: Node | null = null;
  data: any;

  constructor(data: any) {
    this.data = data;
  }
}
const node1 = new Node({ size: 1000000 });
const node2 = new Node({ size: 1000000 });
node1.next = node2;
node2.next = node1;  // ❌ 순환 참조로 GC 미동작
```

## 필요한 증거
- 메모리 프로파일 데이터
- 힙 스냅샷
- 메모리 사용량 그래프
- 의심 코드

## 의심 원인
1. 이벤트 리스너가 제거되지 않음
2. setTimeout/setInterval이 정리되지 않음
3. 전역 변수에 계속 추가됨
4. 캐시 크기 제한 없음
5. 순환 참조
6. DOM 노드 참조 유지

## 빠른 해결법

### 1. 이벤트 리스너 정리
```typescript
// ❌ 잘못된 코드
element.addEventListener('click', handler);

// ✅ 올바른 코드
function attach() {
  element.addEventListener('click', handler);
}

function detach() {
  element.removeEventListener('click', handler);
}

// 또는 once 옵션
element.addEventListener('click', handler, { once: true });
```

### 2. React에서 cleanup
```typescript
useEffect(() => {
  const handler = () => console.log('click');
  window.addEventListener('click', handler);

  // cleanup 함수에서 제거
  return () => {
    window.removeEventListener('click', handler);
  };
}, []);

// 또는 타이머
useEffect(() => {
  const timerId = setInterval(() => {
    // 작업
  }, 1000);

  return () => clearInterval(timerId);
}, []);
```

### 3. 크기 제한이 있는 캐시
```typescript
class LimitedCache<K, V> {
  private cache = new Map<K, V>();
  private maxSize: number;

  constructor(maxSize: number = 100) {
    this.maxSize = maxSize;
  }

  set(key: K, value: V) {
    if (this.cache.size >= this.maxSize) {
      // 가장 오래된 항목 제거
      const firstKey = this.cache.keys().next().value;
      this.cache.delete(firstKey);
    }
    this.cache.set(key, value);
  }

  get(key: K): V | undefined {
    return this.cache.get(key);
  }
}

// 또는 LRU 캐시
class LRUCache<K, V> {
  private cache = new Map<K, V>();
  private accessOrder: K[] = [];
  private maxSize: number;

  constructor(maxSize: number = 100) {
    this.maxSize = maxSize;
  }

  set(key: K, value: V) {
    if (this.cache.has(key)) {
      this.accessOrder.splice(this.accessOrder.indexOf(key), 1);
    } else if (this.cache.size >= this.maxSize) {
      const lru = this.accessOrder.shift();
      if (lru) this.cache.delete(lru);
    }

    this.cache.set(key, value);
    this.accessOrder.push(key);
  }

  get(key: K): V | undefined {
    if (this.cache.has(key)) {
      this.accessOrder.splice(this.accessOrder.indexOf(key), 1);
      this.accessOrder.push(key);
    }
    return this.cache.get(key);
  }
}
```

### 4. WeakMap/WeakSet 사용
```typescript
// ❌ 강한 참조로 메모리 누수
const objectRefs = new Map<object, any>();
const obj = { data: 'test' };
objectRefs.set(obj, 'metadata');
// obj가 삭제되어도 메모리 유지

// ✅ 약한 참조
const weakRefs = new WeakMap<object, any>();
const obj2 = { data: 'test' };
weakRefs.set(obj2, 'metadata');
// obj2가 삭제되면 GC에 의해 정리됨
```

### 5. 메모리 프로파일링
```bash
# Node.js 메모리 모니터링
node --inspect app.js

# 힙 스냅샷 생성
node --heap-prof app.js
# app.heapsnapshot 파일 생성

# 메모리 사용량 추적
node --trace-gc app.js

# 디버그 플래그
node --expose-gc app.js  # gc() 함수 노출
```

### 6. 메모리 모니터링 함수
```typescript
function monitorMemory() {
  if (global.gc) {
    global.gc();  // 강제 가비지 컬렉션
  }

  const used = process.memoryUsage();
  console.log({
    rss: `${Math.round(used.rss / 1024 / 1024)} MB`,
    heapTotal: `${Math.round(used.heapTotal / 1024 / 1024)} MB`,
    heapUsed: `${Math.round(used.heapUsed / 1024 / 1024)} MB`,
    external: `${Math.round(used.external / 1024 / 1024)} MB`
  });
}

setInterval(monitorMemory, 5000);
```

### 7. 동적 import로 메모리 절약
```typescript
// ❌ 모든 모듈 로드
import * as heavyModule from './heavy';

// ✅ 필요할 때만 로드
async function useHeavyModule() {
  const heavyModule = await import('./heavy');
  return heavyModule.process();
}
```

### 8. 스트림으로 큰 데이터 처리
```typescript
// ❌ 전체 로드
const data = fs.readFileSync('large-file.json', 'utf-8');
const parsed = JSON.parse(data);  // 메모리 초과

// ✅ 스트림 처리
const stream = fs.createReadStream('large-file.json');
stream.on('data', (chunk) => {
  processChunk(chunk);
});
```

### 9. 객체 풀 패턴
```typescript
class ObjectPool<T> {
  private available: T[] = [];
  private inUse = new Set<T>();

  constructor(factory: () => T, initialSize = 10) {
    for (let i = 0; i < initialSize; i++) {
      this.available.push(factory());
    }
  }

  acquire(): T {
    const obj = this.available.pop() || new Object() as T;
    this.inUse.add(obj);
    return obj;
  }

  release(obj: T) {
    this.inUse.delete(obj);
    this.available.push(obj);
  }
}
```

### 10. 정리 체크리스트
```typescript
class ResourceManager {
  private timers: number[] = [];
  private listeners: [EventTarget, string, EventListener][] = [];

  addTimer(timerId: number) {
    this.timers.push(timerId);
  }

  addListener(target: EventTarget, event: string, handler: EventListener) {
    target.addEventListener(event, handler);
    this.listeners.push([target, event, handler]);
  }

  cleanup() {
    // 모든 타이머 제거
    this.timers.forEach(id => clearTimeout(id));
    this.timers = [];

    // 모든 리스너 제거
    this.listeners.forEach(([target, event, handler]) => {
      target.removeEventListener(event, handler);
    });
    this.listeners = [];
  }
}
```

## 연결된 패턴
- E-RT-09-worker-crash
- E-PF-02-heavy-derived-state

## 연결된 플로우
- 메모리 최적화 플로우
- 성능 모니터링 플로우

## 재발 방지
1. 이벤트 리스너는 항상 제거
2. setInterval/setTimeout은 cleanup에서 해제
3. 캐시에 크기 제한 설정
4. WeakMap/WeakSet으로 약한 참조 사용
5. 정기적으로 메모리 프로파일링
6. 큰 데이터는 스트림으로 처리
7. 메모리 모니터링 도구 사용 (clinic.js, node-inspect)
