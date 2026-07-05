---
id: P-FS-02
title: 낙관적 UI 업데이트 패턴
stage: Implement
layer: UI
pattern_family: State
tech_tags: [React, 낙관적 업데이트, 상태 롤백, 사용자 경험]
linked_errors: [E-FS-04, E-FS-05]
linked_flows: [F-FS-03, F-FS-04]
linked_prompts: [PR-FS-02]
---

# 낙관적 UI 업데이트 패턴

## 목표
서버 응답 대기 시간 동안 UI를 먼저 업데이트하여 사용자에게 빠른 피드백을 제공하고, 실패 시 자동으로 롤백합니다.

## 언제 사용하는가
- 네트워크 지연이 눈에 띄는 작업 (좋아요, 팔로우, 삭제 등)
- 사용자 경험이 중요한 상황
- 작업 실패율이 낮은 경우

## 언제 사용하지 않는가
- 높은 실패율의 작업 (사용자가 자주 실패 경험)
- 변경이 되돌릴 수 없는 작업
- 재정 거래 등 정합성이 중요한 작업

## 핵심 구조

낙관적 업데이트는 3 단계입니다:
1. 즉시 UI 업데이트
2. 서버에 요청 전송
3. 실패 시 롤백

```typescript
// 좋아요 버튼 예제
interface Post {
  id: string;
  liked: boolean;
  likeCount: number;
}

export function LikeButton({ post: initialPost }: { post: Post }) {
  const [post, setPost] = useState(initialPost);
  const [isLoading, setIsLoading] = useState(false);

  const toggleLike = async () => {
    // Step 1: 즉시 UI 업데이트 (낙관적)
    const previousPost = post;
    const newPost = {
      ...post,
      liked: !post.liked,
      likeCount: post.liked ? post.likeCount - 1 : post.likeCount + 1,
    };
    setPost(newPost);
    setIsLoading(true);

    try {
      // Step 2: 서버 요청
      await toggleLikeApi(post.id, !post.liked);
      // 성공 - UI는 이미 업데이트됨
    } catch (error) {
      // Step 3: 실패 시 롤백
      console.error('좋아요 업데이트 실패:', error);
      setPost(previousPost);
      showNotification('좋아요 업데이트에 실패했습니다', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <button
      onClick={toggleLike}
      disabled={isLoading}
      aria-pressed={post.liked}
    >
      {post.liked ? '❤️' : '🤍'} {post.likeCount}
    </button>
  );
}
```

## 최소 예제

```typescript
function DeleteItem({ item, onDelete }) {
  const [items, setItems] = useState([item]);

  const handleDelete = async (id) => {
    // 낙관적으로 삭제
    const removed = items.find(i => i.id === id);
    setItems(items.filter(i => i.id !== id));

    try {
      await deleteApi(id);
    } catch {
      // 실패 시 복구
      setItems(prev => [...prev, removed]);
    }
  };

  return items.map(i => (
    <div key={i.id}>
      {i.name}
      <button onClick={() => handleDelete(i.id)}>삭제</button>
    </div>
  ));
}
```

## 고급 사용법 - 낙관적 업데이트 관리자

복잡한 목록에서 여러 항목을 동시에 수정할 때:

```typescript
type OptimisticUpdate<T> = {
  id: string;
  previousValue: T;
  newValue: T;
  status: 'pending' | 'success' | 'error';
};

export function useOptimisticUpdate<T extends { id: string }>(
  initialItems: T[],
  updateApi: (id: string, value: T) => Promise<void>
) {
  const [items, setItems] = useState(initialItems);
  const [updates, setUpdates] = useState<Map<string, OptimisticUpdate<T>>>(
    new Map()
  );

  const applyOptimistic = async (id: string, newValue: T) => {
    const previousValue = items.find(i => i.id === id);
    if (!previousValue) return;

    // 낙관적 업데이트 기록
    setUpdates(prev => new Map(prev).set(id, {
      id,
      previousValue,
      newValue,
      status: 'pending',
    }));

    // UI 즉시 업데이트
    setItems(prev =>
      prev.map(i => (i.id === id ? newValue : i))
    );

    try {
      await updateApi(id, newValue);
      // 성공
      setUpdates(prev => {
        const updated = new Map(prev);
        const record = updated.get(id);
        if (record) {
          record.status = 'success';
        }
        return updated;
      });
    } catch (error) {
      // 실패 시 롤백
      setItems(prev =>
        prev.map(i => (i.id === id ? previousValue : i))
      );
      setUpdates(prev => {
        const updated = new Map(prev);
        const record = updated.get(id);
        if (record) {
          record.status = 'error';
        }
        return updated;
      });
    }
  };

  return { items, updates, applyOptimistic };
}
```

## 사용 사례 - 목록 필터링

```typescript
export function TodoList() {
  const [todos, setTodos] = useState<Todo[]>([]);

  const toggleTodo = async (id: string) => {
    // 1. 낙관적으로 상태 변경
    const previousTodos = todos;
    setTodos(todos =>
      todos.map(t =>
        t.id === id ? { ...t, completed: !t.completed } : t
      )
    );

    try {
      // 2. 서버에 요청
      await updateTodoApi(id, { completed: !previousTodos.find(t => t.id === id)?.completed });
    } catch {
      // 3. 실패 시 이전 상태로 복구
      setTodos(previousTodos);
    }
  };

  return (
    <ul>
      {todos.map(todo => (
        <li key={todo.id}>
          <input
            type="checkbox"
            checked={todo.completed}
            onChange={() => toggleTodo(todo.id)}
          />
          {todo.title}
        </li>
      ))}
    </ul>
  );
}
```

## 안티패턴

### 1. 롤백 데이터 보존 실패

```typescript
// ❌ 나쁜 예제 - 롤백할 데이터를 저장하지 않음
const handleLike = async (id) => {
  setPost(prev => ({ ...prev, liked: !prev.liked })); // 원본 데이터 손실!
  await likeApi(id);
};

// ✅ 좋은 예제 - 이전 상태 보존
const handleLike = async (id) => {
  const previousPost = post;
  setPost(prev => ({ ...prev, liked: !prev.liked }));
  try {
    await likeApi(id);
  } catch {
    setPost(previousPost); // 명확한 롤백
  }
};
```

### 2. 중복 요청 방지 부족

```typescript
// ❌ 나쁜 예제 - 연속 클릭 시 중복 요청
const handleLike = async () => {
  setPost(prev => ({ ...prev, liked: !prev.liked }));
  await likeApi(post.id); // 로딩 중 다시 클릭 가능
};

// ✅ 좋은 예제 - 로딩 상태로 중복 요청 방지
const handleLike = async () => {
  if (isLoading) return; // 로딩 중엔 실행하지 않음
  setPost(prev => ({ ...prev, liked: !prev.liked }));
  setIsLoading(true);
  try {
    await likeApi(post.id);
  } finally {
    setIsLoading(false);
  }
};
```

### 3. 동시 낙관적 업데이트 충돌

```typescript
// ❌ 나쁜 예제 - A 업데이트 실패 시 B의 낙관적 업데이트도 영향
const updateA = async () => {
  setItems(prev => updateItemA(prev)); // 낙관적
  try {
    await updateApiA();
  } catch {
    setItems(prev => revertA(prev)); // A만 되돌림
  }
};

// ✅ 좋은 예제 - 업데이트별 추적
const updateA = async () => {
  const previous = items;
  setItems(prev => updateItemA(prev));
  try {
    await updateApiA();
  } catch {
    setItems(previous); // 전체 이전 상태로 복구
  }
};
```

## 연결된 오류

- **E-FS-04**: 낙관적 업데이트 후 서버 데이터와 불일치
- **E-FS-05**: 동시 낙관적 업데이트로 인한 데이터 손실

## 연결된 플로우

- **F-FS-03**: 좋아요/팔로우 기능 구현
- **F-FS-04**: 항목 삭제 및 복구 플로우

## 참고 자료

- React 공식: https://react.dev/learn/you-might-not-need-an-effect
- SWR 낙관적 업데이트: https://swr.vercel.app/docs/mutation#optimistic-updates
