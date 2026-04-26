<template>
  <div class="counter">
    <h2>计数器示例</h2>
    <p>当前计数：{{ count }}</p>
    <button @click="increment">+1</button>
    <button @click="decrement">-1</button>
    <button @click="reset">重置</button>
  </div>
</template>

<script setup>
import { ref } from 'vue'

// 响应式数据
const count = ref(0)

// 方法
const increment = () => {
  count.value++
}

const decrement = () => {
  count.value--
}

const reset = () => {
  count.value = 0
}
</script>

<style scoped>
.counter {
  text-align: center;
  margin-top: 50px;
}
button {
  margin: 0 10px;
  padding: 5px 15px;
  font-size: 16px;
  cursor: pointer;
}
</style>