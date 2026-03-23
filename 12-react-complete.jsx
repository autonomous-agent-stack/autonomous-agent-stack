/**
 * React 完整教程 - 第12章
 * 
 * 涵盖内容：
 * - JSX 语法
 * - 组件
 * - Props 和 State
 * - 生命周期
 * - Hooks
 * - Context
 * - Redux 集成
 * - 性能优化
 */

import React, { useState, useEffect, useContext, useReducer, useRef, useMemo, useCallback } from 'react';
import ReactDOM from 'react-dom/client';
import React Router from 'react-router-dom';
import axios from 'axios';

// ============================================
// 第1节：JSX 语法
// ============================================

// JSX 基本语法
const element = <h1>Hello, JSX!</h1>;
const element2 = <div className="container">
    <h2>Title</h2>
    <p>Paragraph</p>
</div>;

// 表达式嵌入
const name = "Alice";
const element3 = <h1>Hello, {name}!</h1>;

// 属性
const element4 = <div id="myId" className="myClass">
    <input type="text" placeholder="Enter text" />
    <button onClick={() => alert('Clicked!')}>Click me</button>
</div>;

// 条件渲染
const isLoggedIn = true;
const element5 = (
    <div>
        {isLoggedIn ? <h1>Welcome back!</h1> : <h1>Please log in</h1>}
    </ </div>
);

// 列表渲染
const items = ['Apple', 'Banana', 'Cherry'];
const element6 = (
    <ul>
        {items.map((item, index) => (
            <li key={index}>{item}</li>
        ))}
    </ul>
);

// 表单处理
function Form() {
    const [value, setValue] = useState('');
    
    const handleChange = (event) => {
        setValue(event.target.value);
    };
    
    const handleSubmit = (event) => {
        event.preventDefault();
        alert(`Submitted: ${value}`);
    };
    
    return (
        <form onSubmit={handleSubmit}>
            <label>
                Name:
                <input type="text" value={value} onChange={handleChange} />
            </label>
            <button type="submit">Submit</button>
        </form>
    );
}

// ============================================
// 第2节：组件
// ============================================

// 函数组件
function Welcome(props) {
    return <h1>Hello, {props.name}!</h1>;
}

// 类组件
class Counter extends React.Component {
    constructor(props) {
        super(props);
        this.state = { count: 0 };
    }
    
    increment = () => {
        this.setState({ count: this.state.count + 1 });
    };
    
    render() {
        return (
            <div>
                <p>Count: {this.state.count}</p>
                <button onClick={this.increment}>Increment</button>
            </div>
        );
    }
}

// 组件组合
function App() {
    return (
        <div>
            <Welcome name="Alice" />
            <Welcome name="Bob" />
            <Counter />
        </div>
    );
}

// ============================================
// 第3节：Props 和 State
// ============================================

// Props
function UserCard(props) {
    return (
        <div>
            <h2>{props.name}</h2>
            <p>Email: {props.email}</p>
            <p>Age: {props.age}</p>
        </div>
    );
}

// 默认 Props
function Button(props) {
    return (
        <button onClick={props.onClick}>
            {props.children || 'Click me'}
        </button>
    );
}

// State
function Timer() {
    const [seconds, setSeconds] = useState(0);
    
    useEffect(() => {
        const interval = setInterval(() => {
            setSeconds(s => s + 1);
        }, 1000);
        
        return () => clearInterval(interval);
    }, []);
    
    return <div>Seconds: {seconds}</div>;
}

// ============================================
// 第4节：生命周期
// ============================================

// 挂载阶段
function Example() {
    const [data, setData] = useState(null);
    
    useEffect(() => {
        // 组件挂载后执行
        console.log('Component mounted');
        
        // 数据获取
        fetch('https://api.example.com/data')
            .then(response => response.json())
            .then(data => setData(data));
        
        // 清理函数
        return () => {
            console.log('Component will unmount');
        };
    }, []);
    
    return <div>{data ? 'Data loaded' : 'Loading...'}</div>;
}

// 更新阶段
function CounterWithUpdate() {
    const [count, setCount] = useState(0);
    
    useEffect(() => {
        console.log(`Count updated to: ${count}`);
    }, [count]); // 依赖数组
    
    return (
        <div>
            <p>Count: {count}</p>
            <button onClick={() => setCount(count + 1)}>Increment</button>
        </div>
    );
}

// ============================================
// 第5节：Hooks
// ============================================

// useState
function Counter() {
    const [count, setCount] = useState(0);
    
    return (
        <div>
            <p>You clicked {count} times</p>
            <button onClick={() => setCount(count + 1)}>
                Click me
            </button>
        </div>
    );
}

// useEffect
function DataFetcher() {
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(true);
    
    useEffect(() => {
        fetch('https://api.example.com/data')
            .then(response => response.json())
            .then(data => {
                setData(data);
                setLoading(false);
            });
    }, []);
    
    if (loading) return <div>Loading...</div>;
    
    return (
        <ul>
            {data.map(item => (
                <li key={item.id}>{item.name}</li>
            ))}
        </ul>
    );
}

// useContext
const ThemeContext = React.createContext();

function ThemeProvider({ children }) {
    const [theme, setTheme] = useState('light');
    
    return (
        <ThemeContext.Provider value={{ theme, setTheme }}>
            {children}
        </ThemeContext.Provider>
    );
}

function ThemedButton() {
    const { theme, setTheme } = useContext(ThemeContext);
    
    return (
        <button
            onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
            style={{ background: theme === 'light' ? '#fff' : '#333' }}
        >
            Toggle Theme
        </button>
    );
}

// useReducer
function reducer(state, action) {
    switch (action.type) {
        case 'increment':
            return { count: state.count + 1 };
        case 'decrement':
            return { count: state.count - 1 };
        default:
            return state;
    }
}

function CounterWithReducer() {
    const [state, dispatch] = useReducer(reducer, { count: 0 });
    
    return (
        <div>
            <p>Count: {state.count}</p>
            <button onClick={() => dispatch({ type: 'increment' })}>+</button>
            <button onClick={() => dispatch({ type: 'decrement' })}>-</button>
        </div>
    );
}

// useRef
function TextInputWithFocus() {
    const inputRef = useRef(null);
    
    const focusInput = () => {
        inputRef.current.focus();
    };
    
    return (
        <div>
            <input ref={inputRef} type="text" />
            <button onClick={focusInput}>Focus Input</button>
        </div>
    );
}

// useMemo
function ExpensiveComponent({ items }) {
    const sortedItems = useMemo(() => {
        console.log('Sorting items...');
        return [...items].sort((a, b) => a - b);
    }, [items]);
    
    return (
        <ul>
            {sortedItems.map(item => (
                <li key={item}>{item}</li>
            ))}
        </ul>
    );
}

// useCallback
function ParentComponent() {
    const [count, setCount] = useState(0);
    
    const handleClick = useCallback(() => {
        console.log('Button clicked');
    }, []);
    
    return <ChildComponent onClick={handleClick} />;
}

function ChildComponent({ onClick }) {
    return <button onClick={onClick}>Click me</button>;
}

// ============================================
// 第6节：Context
// ============================================

// 创建 Context
const UserContext = React.createContext();

// Provider 组件
function UserProvider({ children }) {
    const [user, setUser] = useState(null);
    
    const login = (userData) => {
        setUser(userData);
    };
    
    const logout = () => {
        setUser(null);
    };
    
    return (
        <UserContext.Provider value={{ user, login, logout }}>
            {children}
        </UserContext.Provider>
    );
}

// Consumer 组件
function UserProfile() {
    const { user, logout } = useContext(UserContext);
    
    if (!user) {
        return <div>Please log in</div>;
    }
    
    return (
        <div>
            <h2>{user.name}</h2>
            <p>{user.email}</p>
            <button onClick={logout}>Logout</button>
        </div>
    );
}

// 使用 Context 的组件
function App() {
    return (
        <UserProvider>
            <div>
                <UserProfile />
                <LoginButton />
            </div>
        </UserProvider>
    );
}

function LoginButton() {
    const { login } = useContext(UserContext);
    
    return (
        <button onClick={() => login({ name: 'Alice', email: 'alice@example.com' })}>
            Login
        </button>
    );
}

// ============================================
// 第7节：Redux 集成
// ============================================

// Redux store
import { createStore } from 'redux';

const initialState = {
    count: 0,
    user: null
};

function reduxReducer(state = initialState, action) {
    switch (action.type) {
        case 'INCREMENT':
            return { ...state, count: state.count + 1 };
        case 'DECREMENT':
            return { ...state, count: state.count - 1 };
        case 'SET_USER':
            return { ...state, user: action.payload };
        case 'LOGOUT':
            return { ...state, user: null };
        default:
            return state;
    }
}

const store = createStore(reducer);

// Redux hooks
import { Provider, useDispatch, useSelector } from 'react-redux';

function ReduxCounter() {
    const count = useSelector(state => state.count);
    const dispatch = useDispatch();
    
    return (
        <div>
            <p>Count: {count}</p>
            <button onClick={() => dispatch({ type: 'INCREMENT' })}>+</button>
            <button onClick={() => dispatch({ type: 'DECREMENT' })}>-</button>
        </div>
    );
}

function ReduxApp() {
    return (
        <Provider store={store}>
            <ReduxCounter />
        </Provider>
    );
}

// ============================================
// 第8节：性能优化
// ============================================

// React.memo
const ExpensiveComponent = React.memo(function ExpensiveComponent({ data }) {
    console.log('ExpensiveComponent rendered');
    
    return <div>{/* complex rendering */}</div>;
});

// 代码分割
const LazyComponent = React.lazy(() => import('./HeavyComponent'));

function App() {
    return (
        <div>
            <Suspense fallback={<div>Loading...</div>}>
                <LazyComponent />
            </Suspense>
        </div>
    );
}

// 虚拟列表
function VirtualList({ items }) {
    return (
        <div style={{ height: '400px', overflow: 'auto' }}>
            {items.map(item => (
                <div key={item.id} style={{ height: '50px' }}>
                    {item.name}
                </div>
            ))}
        </div>
    );
}

// 防抖
function SearchInput() {
    const [query, setQuery] = useState('');
    
    const debouncedSearch = useMemo(
        () => debounce(() => {
        console.log('Searching for:', query);
    }, 300),
        [query]
    );
    
    useEffect(() => {
        debouncedSearch();
    }, [debouncedSearch]);
    
    return (
        <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search..."
        />
    );
}

// 节流
function ResizeHandler() {
    const [size, setSize] = useState({ width: 0, height: 0 });
    
    const throttledHandleResize = useMemo(
        () => throttle(() => {
        setSize({
            width: window.innerWidth,
            height: window.innerHeight
        });
    }, 100),
        []
    );
    
    useEffect(() => {
        window.addEventListener('resize', throttledHandleResize);
        return () => {
            window.removeEventListener('resize', throttledHandleResize);
        };
    }, [throttledHandleResize]);
    
    return <div>Window size: {size.width} x {size.height}</div>;
}

