---
id: P-FS-03
title: 파생 상태 패턴
stage: Implement
layer: UI
pattern_family: State
tech_tags: [React, 계산된 상태, 메모이제이션, 성능 최적화]
linked_errors: [E-FS-06, E-FS-07, E-FS-08]
linked_flows: [F-FS-05]
linked_prompts: [PR-FS-03]
---

# 파생 상태 패턴

## 목표
State에 저장할 수 있는 값을 계산으로 도출하여 데이터 중복을 제거하고, 동기화 오류를 방지합니다.

## 언제 사용하는가
- 다른 상태에서 파생되는 값 (필터링된 목록, 합계, 유효성 상태)
- 계산 비용이 낮은 경우
- 실시간 계산이 필요한 경우

## 언제 사용하지 않는가
- 매우 비싼 계산 (대규모 배열 정렬/필터링) - useMemo 사용
- 비동기 작업 (서버에서 데이터 로드) - 상태로 저장 필요
- 이전 상태 값을 추적해야 하는 경우

## 핵심 구조

필터링된 목록의 좋은 예제:

```typescript
export function ProductList() {
  const [products] = useState<Product[]>([
    { id: 1, name: '노트북', price: 1000 },
    { id: 2, name: '마우스', price: 50 },
    { id: 3, name: '키보드', price: 100 },
  ]);

  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState<'name' | 'price'>('name');

  // ❌ 안 좋은 예제: 파생 상태를 state로 관리
  // const [filteredProducts, setFilteredProducts] = useState<Product[]>([]);
  // useEffect(() => {
  //   setFilteredProducts(products.filter(...));
  // }, [products, searchTerm]);

  // ✅ 좋은 예제: 파생 값을 계산으로 도출
  const filteredProducts = useMemo(() => {
    return products
      .filter(p =>
        p.name.toLowerCase().includes(searchTerm.toLowerCase())
      )
      .sort((a, b) => {
        if (sortBy === 'name') {
          return a.name.localeCompare(b.name);
        }
        return a.price - b.price;
      });
  }, [products, searchTerm, sortBy]);

  return (
    <div>
      <input
        value={searchTerm}
        onChange={e => setSearchTerm(e.target.value)}
        placeholder="검색..."
      />
      <select value={sortBy} onChange={e => setSortBy(e.target.value as any)}>
        <option value="name">이름순</option>
        <option value="price">가격순</option>
      </select>
      <ul>
        {filteredProducts.map(product => (
          <li key={product.id}>
            {product.name} - ${product.price}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

## 최소 예제

```typescript
// ❌ 안 좋은 패턴
const [items] = useState([1, 2, 3, 4, 5]);
const [sum, setSum] = useState(0);

useEffect(() => {
  setSum(items.reduce((a, b) => a + b)); // state 동기화 필요
}, [items]);

// ✅ 좋은 패턴
const [items] = useState([1, 2, 3, 4, 5]);
const sum = items.reduce((a, b) => a + b); // 직접 계산
```

## 폼 유효성 예제

```typescript
interface FormData {
  email: string;
  password: string;
  confirmPassword: string;
}

export function SignUpForm() {
  const [form, setForm] = useState<FormData>({
    email: '',
    password: '',
    confirmPassword: '',
  });

  // 파생 상태: 유효성 검사 결과
  const validation = useMemo(() => {
    const errors: Record<string, string> = {};

    if (!form.email) {
      errors.email = '이메일은 필수입니다';
    } else if (!form.email.includes('@')) {
      errors.email = '유효한 이메일을 입력하세요';
    }

    if (!form.password) {
      errors.password = '비밀번호는 필수입니다';
    } else if (form.password.length < 8) {
      errors.password = '비밀번호는 8자 이상이어야 합니다';
    }

    if (form.password !== form.confirmPassword) {
      errors.confirmPassword = '비밀번호가 일치하지 않습니다';
    }

    return {
      errors,
      isValid: Object.keys(errors).length === 0,
    };
  }, [form]);

  return (
    <form>
      <div>
        <input
          type="email"
          value={form.email}
          onChange={e => setForm(p => ({ ...p, email: e.target.value }))}
        />
        {validation.errors.email && (
          <span className="error">{validation.errors.email}</span>
        )}
      </div>
      <div>
        <input
          type="password"
          value={form.password}
          onChange={e => setForm(p => ({ ...p, password: e.target.value }))}
        />
        {validation.errors.password && (
          <span className="error">{validation.errors.password}</span>
        )}
      </div>
      <div>
        <input
          type="password"
          value={form.confirmPassword}
          onChange={e =>
            setForm(p => ({ ...p, confirmPassword: e.target.value }))
          }
        />
        {validation.errors.confirmPassword && (
          <span className="error">
            {validation.errors.confirmPassword}
          </span>
        )}
      </div>
      <button disabled={!validation.isValid}>회원가입</button>
    </form>
  );
}
```

## 전자상거래 장바구니 예제

```typescript
interface CartItem {
  id: string;
  productId: string;
  quantity: number;
  price: number;
}

export function ShoppingCart() {
  const [cartItems, setCartItems] = useState<CartItem[]>([]);
  const [taxRate] = useState(0.1); // 10% 세금

  // 파생 상태들: 순수 계산으로 도출
  const cartSummary = useMemo(() => {
    const subtotal = cartItems.reduce(
      (sum, item) => sum + item.price * item.quantity,
      0
    );
    const tax = subtotal * taxRate;
    const total = subtotal + tax;

    return {
      itemCount: cartItems.reduce((sum, item) => sum + item.quantity, 0),
      subtotal,
      tax,
      total,
      isEmpty: cartItems.length === 0,
    };
  }, [cartItems, taxRate]);

  return (
    <div>
      <h2>장바구니</h2>
      <p>항목 수: {cartSummary.itemCount}</p>
      <p>소계: ${cartSummary.subtotal.toFixed(2)}</p>
      <p>세금: ${cartSummary.tax.toFixed(2)}</p>
      <p>합계: ${cartSummary.total.toFixed(2)}</p>
      {cartSummary.isEmpty && <p>장바구니가 비어있습니다</p>}
      <button disabled={cartSummary.isEmpty}>결제하기</button>
    </div>
  );
}
```

## 안티패턴

### 1. 파생 상태를 state로 관리

```typescript
// ❌ 나쁜 예제
const [items, setItems] = useState<Item[]>([...]);
const [filteredItems, setFilteredItems] = useState<Item[]>([]); // 중복!
const [total, setTotal] = useState(0); // 중복!

useEffect(() => {
  setFilteredItems(items.filter(...)); // 동기화 필요
}, [items]);

useEffect(() => {
  setTotal(items.reduce(...)); // 동기화 필요
}, [items]);

// ✅ 좋은 예제
const [items, setItems] = useState<Item[]>([...]);
const filteredItems = items.filter(...); // 계산으로 도출
const total = items.reduce(...); // 계산으로 도출
```

### 2. useMemo 없이 성능 저하

```typescript
// ❌ 나쁜 예제 - 매 렌더마다 계산
export function List({ items, filter }) {
  const filtered = items.filter(i => i.category === filter); // 계산 비용이 높음
  return <div>{filtered.map(...)}</div>;
}

// ✅ 좋은 예제 - 의존성이 변경될 때만 계산
export function List({ items, filter }) {
  const filtered = useMemo(
    () => items.filter(i => i.category === filter),
    [items, filter]
  );
  return <div>{filtered.map(...)}</div>;
}
```

### 3. 복잡한 계산을 동기화

```typescript
// ❌ 나쁜 예제
const [data, setData] = useState([...]);
const [aggregated, setAggregated] = useState({});

useEffect(() => {
  // 복잡한 집계 로직
  const result = expensiveAggregation(data);
  setAggregated(result);
}, [data]);

// ✅ 좋은 예제
const [data, setData] = useState([...]);
const aggregated = useMemo(
  () => expensiveAggregation(data),
  [data]
);
```

## 연결된 오류

- **E-FS-06**: Props를 state로 복사하여 동기화 불일치
- **E-FS-07**: useMemo의 의존성 배열 누락으로 인한 버그
- **E-FS-08**: 파생 상태와 원본 상태의 불일치

## 연결된 플로우

- **F-FS-05**: 검색/필터링 기능 구현

## 참고 자료

- React 공식: https://react.dev/learn/choosing-the-state-structure#avoid-redundant-state
- useMemo 가이드: https://react.dev/reference/react/useMemo
