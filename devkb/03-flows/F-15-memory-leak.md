---
id: F-15
title: 메모리 누수 해결
pattern_id: P-15
error_ids: [E-43, E-44, E-45]
tech_scope: 메모리 관리, 가비지 컬렉션, DevTools
---

# 메모리 누수 해결

JavaScript 애플리케이션에서 메모리 누수를 진단하고 해결합니다.

## 1단계: 증상 고정

증상:
- 시간이 지날수록 메모리 사용량 증가
- 페이지 성능 저하
- 브라우저 크래시
- "Chrome ran out of memory"
- 장시간 사용 후 속도 저하

## 2단계: 재현

```javascript
// ❌ 메모리 누수 예제 1: 전역 변수
const cache = {}; // 영구적인 메모리

function addToCache(key, value) {
  cache[key] = value; // 언제 삭제되는가? → 절대 삭제 안 됨
}

// ❌ 메모리 누수 예제 2: 리스너 미제거
function setupListener() {
  const largeObject = new Array(1000000).fill('x');

  window.addEventListener('message', () => {
    console.log(largeObject); // 클로저로 largeObject 캡처
  });

  // removeEventListener() 호출 안 함
}

// ❌ 메모리 누수 예제 3: 순환 참조
class Node {
  constructor(value) {
    this.value = value;
    this.parent = null;
    this.children = [];
  }
}

const parent = new Node('parent');
const child = new Node('child');
parent.children.push(child);
child.parent = parent; // 순환 참조 → GC 불가능 (일부 엔진)
```

## 3단계: 범위 축소

메모리 누수 유형:

1. **전역 변수**: 정리되지 않는 전역 변수
2. **리스너 미제거**: 이벤트 리스너, 타이머
3. **클로저**: 불필요한 변수 캡처
4. **순환 참조**: A → B → A
5. **DOM 참조**: 제거된 DOM 노드 참조 유지
6. **캐시**: 크기 제한 없는 캐시
7. **타이머**: clearInterval/clearTimeout 미호출

## 4단계: 증거 수집

```javascript
// Chrome DevTools Performance 탭
// 1. Recording 시작
// 2. 애플리케이션 사용
// 3. Recording 중지
// 4. Memory 탭 확인 → Heap 증가 여부 확인

// Memory Profiler 사용
// 1. DevTools → Memory 탭
// 2. Heap snapshot 촬영
// 3. 작업 수행
// 4. 다시 Heap snapshot 촬영
// 5. 두 snapshot 비교 → 증가한 메모리 확인
```

```javascript
// 프로그래밍으로 메모리 모니터링
if (performance.memory) {
  setInterval(() => {
    const memUsage = performance.memory;
    console.log(`Used: ${(memUsage.usedJSHeapSize / 1048576).toFixed(2)} MB`);
    console.log(`Limit: ${(memUsage.jsHeapSizeLimit / 1048576).toFixed(2)} MB`);

    if (memUsage.usedJSHeapSize > memUsage.jsHeapSizeLimit * 0.9) {
      console.warn('Memory usage critical');
    }
  }, 5000);
}
```

## 5단계: 원인 후보 정렬

| 원인 | 확률 | 복잡도 |
|------|------|--------|
| 리스너 미제거 | 매우높음 | 낮음 |
| 클로저 문제 | 높음 | 중간 |
| 캐시 무제한 증가 | 높음 | 낮음 |
| DOM 참조 | 높음 | 중간 |
| 타이머 미정리 | 중간 | 낮음 |

## 6단계: 수정안 선택

### 수정안 1: 이벤트 리스너 정리

```javascript
// ❌ 메모리 누수
class Component {
  constructor() {
    this.data = new Array(1000000);
    window.addEventListener('message', () => {
      this.handleMessage();
    });
  }

  handleMessage() {
    console.log(this.data);
  }
}

// ✅ cleanup 구현
class Component {
  constructor() {
    this.data = new Array(1000000);
    this.handleMessage = this.handleMessage.bind(this);
    window.addEventListener('message', this.handleMessage);
  }

  handleMessage() {
    console.log(this.data);
  }

  destroy() {
    window.removeEventListener('message', this.handleMessage);
    this.data = null; // 명시적으로 null 할당
  }
}

const component = new Component();
// 사용 후
component.destroy();
```

```javascript
// React에서
useEffect(() => {
  const handleMessage = (event) => {
    console.log(event);
  };

  window.addEventListener('message', handleMessage);

  return () => {
    window.removeEventListener('message', handleMessage); // cleanup
  };
}, []);
```

### 수정안 2: 타이머 정리

```javascript
// ❌ 타이머 미정리
setInterval(() => {
  console.log('Tick');
}, 1000); // 종료될 때까지 계속 실행

// ✅ 타이머 정리
const timerId = setInterval(() => {
  console.log('Tick');
}, 1000);

// 필요할 때 정리
clearInterval(timerId);

// React에서
useEffect(() => {
  const timerId = setInterval(() => {
    console.log('Tick');
  }, 1000);

  return () => clearInterval(timerId); // cleanup
}, []);
```

### 수정안 3: 크기 제한이 있는 캐시

```javascript
// ❌ 무제한 캐시
const cache = {};

function memoize(fn) {
  return function(...args) {
    const key = JSON.stringify(args);
    if (!(key in cache)) {
      cache[key] = fn(...args); // 언제까지 메모리 사용?
    }
    return cache[key];
  };
}

// ✅ LRU(Least Recently Used) 캐시
class LRUCache {
  constructor(maxSize = 100) {
    this.maxSize = maxSize;
    this.cache = new Map();
  }

  get(key) {
    if (!this.cache.has(key)) {
      return undefined;
    }

    // 최근 사용으로 표시
    const value = this.cache.get(key);
    this.cache.delete(key);
    this.cache.set(key, value);
    return value;
  }

  set(key, value) {
    if (this.cache.has(key)) {
      this.cache.delete(key);
    } else if (this.cache.size >= this.maxSize) {
      // 가장 오래된 항목 제거
      const oldestKey = this.cache.keys().next().value;
      this.cache.delete(oldestKey);
    }

    this.cache.set(key, value);
  }
}

// 사용
const cache = new LRUCache(100);
```

### 수정안 4: 클로저 최적화

```javascript
// ❌ 큰 객체 클로저
function createHandler() {
  const largeData = new Array(10000000); // 거대한 배열

  return () => {
    console.log('Handler called');
    // largeData는 클로저에 캡처되어 메모리 누수
  };
}

// ✅ 필요한 데이터만 저장
function createHandler() {
  const requiredValue = '필요한 것만';

  return () => {
    console.log('Handler called:', requiredValue);
  };
}

// 또는 WeakMap 사용
const handlers = new WeakMap();

function attachHandler(obj) {
  handlers.set(obj, () => {
    console.log('Handler');
  });
}

// obj가 GC되면 핸들러도 자동 제거
```

### 수정안 5: DOM 참조 정리

```javascript
// ❌ DOM 참조 누수
const elements = [];

document.querySelectorAll('.item').forEach(el => {
  elements.push(el);

  el.addEventListener('click', () => {
    console.log(el.textContent);
  });
});

// 나중에 DOM 제거
document.querySelectorAll('.item').forEach(el => el.remove());
// 하지만 elements 배열이 여전히 참조 중

// ✅ 명시적 정리
const elements = [];

document.querySelectorAll('.item').forEach(el => {
  elements.push(el);

  el.addEventListener('click', () => {
    console.log(el.textContent);
  });
});

// 정리 함수
function cleanup() {
  elements.forEach(el => {
    el.removeEventListener('click', null); // 모든 리스너 제거
  });
  elements.length = 0; // 배열 비우기
}

cleanup();
```

### 수정안 6: Proxy로 자동 정리

```javascript
// 자동 정리되는 리스너 관리자
class ListenerManager {
  constructor(target) {
    this.target = target;
    this.listeners = new Map();

    return new Proxy(target, {
      set: (obj, prop, value) => {
        // 새 리스너 등록 추적
        if (prop === 'addEventListener') {
          this.listeners.set(value, true);
        }
        return Reflect.set(obj, prop, value);
      }
    });
  }

  cleanup() {
    this.listeners.forEach((_, listener) => {
      this.target.removeEventListener('message', listener);
    });
    this.listeners.clear();
  }
}
```

### 수정안 7: 메모리 모니터링

```javascript
// 메모리 사용량 모니터링
class MemoryMonitor {
  constructor(threshold = 0.8) {
    this.threshold = threshold;
    this.previousHeap = 0;
    this.startMonitoring();
  }

  startMonitoring() {
    setInterval(() => {
      if (!performance.memory) return;

      const used = performance.memory.usedJSHeapSize;
      const limit = performance.memory.jsHeapSizeLimit;
      const ratio = used / limit;

      if (ratio > this.threshold) {
        console.warn(`Memory usage: ${(ratio * 100).toFixed(1)}%`);
        this.triggerGC();
      }

      const delta = used - this.previousHeap;
      if (delta > 10 * 1024 * 1024) { // 10MB 증가
        console.warn(`Heap increased by ${(delta / 1024 / 1024).toFixed(2)}MB`);
      }

      this.previousHeap = used;
    }, 5000);
  }

  triggerGC() {
    // V8 엔진에서만 작동 (--expose-gc 플래그 필요)
    if (global.gc) {
      global.gc();
      console.log('Garbage collection triggered');
    }
  }
}

const monitor = new MemoryMonitor();
```

## 7단계: 검증

```javascript
describe('Memory Leak Prevention', () => {
  it('should clean up listeners on unmount', () => {
    const removeEventListenerSpy = jest.spyOn(window, 'removeEventListener');

    const { unmount } = render(<Component />);

    unmount();

    expect(removeEventListenerSpy).toHaveBeenCalled();
  });

  it('should not grow memory indefinitely', async () => {
    const initialMemory = performance.memory?.usedJSHeapSize || 0;

    for (let i = 0; i < 1000; i++) {
      const component = new Component();
      component.destroy();
    }

    const finalMemory = performance.memory?.usedJSHeapSize || 0;
    const delta = finalMemory - initialMemory;

    // 증가가 5MB 이하로 제한되어야 함
    expect(delta).toBeLessThan(5 * 1024 * 1024);
  });
});
```

## 8단계: 재발 방지

1. **코드 리뷰 체크리스트**
   - [ ] 모든 addEventListener에 removeEventListener 있는가?
   - [ ] 모든 setInterval/setTimeout에 clear 함수 있는가?
   - [ ] 캐시 크기가 제한되어 있는가?
   - [ ] cleanup 함수가 호출되는가?

2. **자동화 테스트**

```javascript
// 메모리 테스트 추가
it('should not leak memory during component lifecycle', async () => {
  const memoryBefore = performance.memory?.usedJSHeapSize;

  for (let i = 0; i < 100; i++) {
    const { unmount } = render(<Component />);
    unmount();
  }

  global.gc?.();

  const memoryAfter = performance.memory?.usedJSHeapSize;
  const delta = memoryAfter - memoryBefore;

  expect(delta).toBeLessThan(2 * 1024 * 1024); // 2MB 이하
});
```

## 연결된 프롬프트 블록

- **PB-CL-16-memory-management**: 메모리 관리 개념
- **PB-RP-15-memory-profiling**: 메모리 프로파일링
- **PB-DG-16-heap-snapshot**: Heap 스냅샷 분석
- **PB-PA-16-cleanup**: cleanup 함수 구현
- **PB-VF-15-memory-test**: 메모리 누수 검증
