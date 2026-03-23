/**
 * Vue.js 完整教程 - 第13章
 * 
 * 涵盖内容：
 * - Vue 3 如念
 * - 组合式 API
 * - 响应式系统
 * - 组件
 * - 指令
 * - 路由
 * - 状态管理
 */

import { createApp, ref, reactive, computed, watch, onMounted, onUnmounted } from 'vue';
import { useRouter, useRoute, useLink } from 'vue-router';
import { createStore } from 'vuex';
import { useStore } from 'vuex';
import axios from 'axios';

// ============================================
// 第1节：Vue 3 概念
// ============================================

// 组合式 API
<template>
    <div>
        <h1>{{ message }}</h1>
        <p>Count: {{ count }}</p>
        <button @click="increment">Increment</button>
    </div>
</template>

<script>
import { ref } from 'vue';

export default {
    setup() {
        const message = ref('Hello Vue 3!');
        const count = ref(0);
        
        const increment = () => {
            count.value++;
        };
        
        return {
            message,
            count,
            increment
        };
    }
}
</script>

// 响应式 API
<template>
    <div>
        <h1>{{ state.message }}</h1>
        <p>Count: {{ state.count }}</p>
        <button @click="increment">Increment</button>
    </div>
</template>

<script>
import { reactive } from 'vue';

export default {
    setup() {
                const state = reactive({
                    message: 'Hello Vue 3!',
                    count: 0
                });
                
                const increment = () => {
                    state.count++;
                };
                
                return {
                    state,
                    increment
                };
    }
}
</script>

// ============================================
// 第2节：组件
// ============================================

// 选项式 API
<template>
    <div>
        <h1>{{ title }}</h1>
        <p>{{ content }}</p>
        <button @click="handleClick">Click me</button>
    </div>
</template>

<script>
export default {
    props: {
        title: {
            type: String,
            required: true
        },
        content: {
            type: String,
            default: ''
        }
    },
    emits: ['click'],
    
    setup(props, { emit }) {
        const handleClick = () => {
            emit('click', 'Button clicked');
        };
        
        return {
            handleClick
        };
    }
}
</script>

// 插槽
<template>
    <div>
        <slot name="header">Default Header</slot>
        <slot name="content">
            <p>Default content</p>
        </slot>
        <slot name="footer" />
    </div>
</template>

<script>
export default {
    // 组件逻辑
}
</script>

// ============================================
// 第3节：指令
// ============================================

// v-model
<template>
    <input v-model="message" placeholder="Type something">
    <p>You typed: {{ message }}</p>
</template>

<script>
import { ref } from 'vue';

export default {
    setup() {
        const message = ref('');
        
        return {
            message
        };
    }
}
</script>

// v-show / v-if
<template>
    <div>
        <p v-if="isVisible">This is visible</p>
        <p v-show="isVisible">This is conditionally displayed</p>
        <button @click="isVisible = !isVisible">Toggle</button>
    </div>
</template>

<script>
import { ref } from 'vue';

export default {
    setup() {
        const isVisible = ref(true);
        
        return {
            isVisible
        };
    }
}
</script>

// v-for
<template>
    <ul>
        <li v-for="item in items" :key="item.id">
            {{ item.text }}
        </li>
    </ul>
</template>

<script>
export default {
    setup() {
        const items = ref([
            { id: 1, text: 'Item 1' },
            { id: 2, text: 'Item 2' },
            { id: 3, text: 'Item 3' }
        ]);
        
        return {
            items
        };
    }
}
</script>

// ============================================
// 第4节：路由
// ============================================

// Vue Router 设置
import { createRouter, createWebHistory } from 'vue-router';
import Home from './views/Home.vue';
import About from './views/About.vue';
import Contact from './views/Contact.vue';

const routes = [
    { path: '/', component: Home },
    { path: '/about', component: About },
    { path: '/contact', component: Contact }
];

const router = createRouter({
    history: createWebHistory(),
    routes
});

export default router;

// 路由使用
<template>
    <div>
        <nav>
            <router-link to="/">Home</router-link>
            <router-link to="/about">About</router-link>
            <router-link to="/contact">Contact</router-link>
        </nav>
        <router-view></router-view>
    </div>
</template>

<script>
export default {
    // 组件逻辑
}
</script>

// 路由参数
<template>
    <div>
        <h1>User ID: {{ userId }}</h1>
        <router-link to="/users/1">User 1</router-link>
        <router-link to="/users/2">User 2</router-link>
    </div>
</template>

<script>
import { useRoute } from 'vue-router';

export default {
    setup() {
        const route = useRoute();
        
        return {
            userId: route.params.id
        };
    }
}
</script>

// 编程式导航
<template>
    <div>
        <button @click="goToHome">Go to Home</button>
        <button @click="goBack">Go Back</button>
    </div>
</template>

<script>
import { useRouter } from 'vue-router';

export default {
    setup() {
        const router = useRouter();
        
        const goToHome = () => {
            router.push('/');
        };
        
        const goBack = () => {
            router.go(-1);
        };
        
        return {
            goToHome,
            goBack
        };
    }
}
</script>

// ============================================
// 第5节：状态管理
// ============================================

// Vuex Store
import { createStore } from 'vuex';

const store = createStore({
    state: {
        count: 0,
        user: null
    },
    mutations: {
        increment(state) {
            state.count++;
        },
        setUser(state, user) {
            state.user = user;
        }
    },
    actions: {
        increment({ commit }) {
            commit('increment');
        },
        async fetchUser({ commit }, id) {
            const response = await fetch(`/api/users/${id}`);
            const user = await response.json();
            commit('setUser', user);
        }
    },
    getters: {
        doubleCount(state) {
            return state.count * 2;
        }
    }
});

export default store;

// 使用 Vuex
<template>
    <div>
        <p>Count: {{ count }}</p>
        <p>Double: {{ doubleCount }}</p>
        <button @click="increment">Increment</button>
    </div>
</template>

<script>
import { useStore } from 'vuex';
import { computed } from 'vue';

export default {
    setup() {
        const store = useStore();
        
        const count = computed(() => store.state.count);
        const doubleCount = computed(() => store.getters.doubleCount);
        
        const increment = () => {
            store.dispatch('increment');
        };
        
        return {
            count,
            doubleCount,
            increment
        };
    }
}
</script>

// ============================================
// 第6节：生命周期钩子
// ============================================

<template>
    <div>
        <p>{{ message }}</p>
    </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue';

export default {
    setup() {
        const message = ref('Loading...');
        
        onMounted(() => {
            console.log('Component mounted');
            // 执行初始化操作
            fetch('/api/data')
                .then(response => response.json())
                .then(data => {
                    message.value = data.message;
                });
        });
        
        onUnmounted(() => {
            console.log('Component unmounted');
            // 清理操作
        });
        
        return {
            message
        };
    }
}
</script>

// watch
<template>
    <div>
        <input v-model="query" placeholder="Search">
        <p>Results: {{ results.length }}</p>
    </div>
</template>

<script>
import { ref, watch } from 'vue';

export default {
    setup() {
        const query = ref('');
        const results = ref([]);
        
        watch(query, async (newQuery) => {
            if (newQuery) {
                const response = await fetch(`/api/search?q=${newQuery}`);
                results.value = await response.json();
            } else {
                results.value = [];
            }
        });
        
        return {
            query,
            results
        };
    }
}
</script>

// computed
<template>
    <div>
        <input v-model="firstName" placeholder="First Name">
        <input v-model="lastName" placeholder="Last Name">
        <p>Full Name: {{ fullName }}</p>
    </div>
</template>

<script>
import { ref, computed } from 'vue';

export default {
    setup() {
        const firstName = ref('');
        const lastName = ref('');
        
        const fullName = computed(() => {
            return `${firstName.value} ${lastName.value}`.trim();
        });
        
        return {
            firstName,
            lastName,
            fullName
        };
    }
}
</script>

// ============================================
// 第7节：组合式函数
// ============================================

// 自定义组合式函数
function useCounter(initialValue = 0) {
    const count = ref(initialValue);
    
    const increment = () => {
        count.value++;
    };
    
    const decrement = () => {
        count.value--;
    };
    
    const reset = () => {
        count.value = initialValue;
    };
    
    return {
        count,
        increment,
        decrement,
        reset
    };
}

// 使用组合式函数
<template>
    <div>
        <p>Count: {{ count }}</p>
        <button @click="increment">+</button>
        <button @click="decrement">-</button>
        <button @click="reset">Reset</button>
    </div>
</template>

<script>
import { useCounter } from './composables/useCounter';

export default {
    setup() {
        const { count, increment, decrement, reset } = useCounter(10);
        
        return {
            count,
            increment,
            decrement,
            reset
        };
    }
}
</script>

// 数据获取组合式函数
function useFetch(url) {
    const data = ref(null);
    const error = ref(null);
    const loading = ref(true);
    
    const fetchData = async () => {
        loading.value = true;
        try {
            const response = await fetch(url);
            data.value = await response.json();
            error.value = null;
        } catch (e) {
            error.value = e.message;
        } finally {
            loading.value = false;
        }
    };
    
    onMounted(fetchData);
    
    return {
        data,
        error,
        loading,
        refetch: fetchData
    };
}

// ============================================
// 第8节：Teleport 和 Suspense
// ============================================

// Teleport
<template>
    <div>
        <button @click="showModal = true">Show Modal</button>
        
        <teleport to="body">
            <div v-if="showModal" class="modal">
                <p>This is a modal</p>
                <button @click="showModal = false">Close</button>
            </div>
        </teleport>
    </div>
</template>

<script>
import { ref } from 'vue';

export default {
    setup() {
        const showModal = ref(false);
        
        return {
            showModal
        };
    }
}
</script>

// Suspense
<template>
    <suspense>
        <template #default>
            <div>Loading...</div>
        </template>
        <template #fallback>
            <div>Loading component...</div>
        </template>
        
        <async-component></async-component>
    </suspense>
</template>

// ============================================
// 第9节：Provide/Inject
// ============================================

// 父组件
<template>
    <div>
        <child-component></child-component>
    </div>
</template>

<script>
import { provide, ref } from 'vue';
import ChildComponent from './ChildComponent.vue';

export default {
    setup() {
        const theme = ref('light');
        
        provide('theme', theme);
        
        return {
            theme
        };
    }
}
</script>

// 子组件
<template>
    <div>
        <p>Current theme: {{ theme }}</p>
        <button @click="toggleTheme">Toggle Theme</button>
    </div>
</template>

<script>
import { inject } from 'vue';

export default {
    setup() {
        const theme = inject('theme');
        
        const toggleTheme = () => {
            theme.value = theme.value === 'light' ? 'dark' : 'light';
        };
        
        return {
            theme,
            toggleTheme
        };
    }
}
</script>

console.log('=== Vue.js 完整教程完成 ===');
