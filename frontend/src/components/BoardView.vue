<template>
  <div class="board-view">
    <header class="header">
      <router-link to="/" class="back-link">&larr; Dashboard</router-link>
      <h1>{{ name }}</h1>
    </header>

    <div v-if="board" class="columns">
      <div v-for="(col, ci) in board.columns" :key="ci" class="column">
        <div class="column-header">
          <h2>{{ col.name }}</h2>
          <span class="task-count">{{ col.tasks.length }}</span>
        </div>
        <ul class="task-list">
          <li v-for="(task, ti) in col.tasks" :key="ti" class="task-item" :class="{ completed: task.completed }">
            <span class="checkbox" @click="completeTask(ci, ti)">{{ task.completed ? '☑' : '☐' }}</span>
            <span class="task-text" v-html="renderTask(task.text)"></span>
            <button class="delete-btn" @click="deleteTask(ci, ti)" title="Remove task">&times;</button>
          </li>
        </ul>
        <p v-if="col.tasks.length === 0" class="empty">No tasks</p>
      </div>
    </div>

    <p v-else class="loading">Loading board…</p>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  name: { type: String, required: true }
})

const API_BASE = import.meta.env.VITE_API_URL || ''
import { useObsidian } from '../composables/useObsidian.js'

const { renderTask } = useObsidian()
const board = ref(null)
let pollTimer = null

async function completeTask(columnIndex, taskIndex) {
  try {
    const res = await fetch(`${API_BASE}/api/tasks/complete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ board: props.name, column_index: columnIndex, task_index: taskIndex }),
    })
    if (res.ok) fetchBoard()
  } catch (e) {
    console.error('Failed to complete task:', e)
  }
}

async function deleteTask(columnIndex, taskIndex) {
  try {
    const res = await fetch(`${API_BASE}/api/tasks`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ board: props.name, column_index: columnIndex, task_index: taskIndex }),
    })
    if (res.ok) fetchBoard()
  } catch (e) {
    console.error('Failed to delete task:', e)
  }
}

async function fetchBoard() {
  try {
    const res = await fetch(`${API_BASE}/api/boards/${encodeURIComponent(props.name)}`)
    if (res.ok) {
      board.value = await res.json()
    }
  } catch (e) {
    console.error('Failed to fetch board:', e)
  }
}

onMounted(() => {
  fetchBoard()
  // Poll for updates since we're not on the WS dashboard feed
  pollTimer = setInterval(fetchBoard, 3000)
})

onUnmounted(() => {
  clearInterval(pollTimer)
})
</script>

<style scoped>
.header {
  margin-bottom: 1.5rem;
}

.back-link {
  color: var(--accent);
  text-decoration: none;
  font-size: 0.85rem;
}

.back-link:hover {
  text-decoration: underline;
}

.header h1 {
  margin: 0.25rem 0 0;
  font-size: 1.5rem;
  color: var(--text-primary);
}

.columns {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1rem;
  align-items: start;
}

.column {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1rem;
}

.column-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}

.column-header h2 {
  margin: 0;
  font-size: 1rem;
  color: var(--text-primary);
}

.task-count {
  font-size: 0.75rem;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  background: var(--border);
  color: var(--text-muted);
}

.task-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.task-item {
  padding: 0.4rem 0;
  border-bottom: 1px solid var(--border-light);
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  font-size: 0.9rem;
  color: var(--text-primary);
}

.task-item:last-child {
  border-bottom: none;
}

.task-item.completed {
  opacity: 0.5;
  text-decoration: line-through;
}

.checkbox {
  flex-shrink: 0;
  cursor: pointer;
}

.delete-btn {
  margin-left: auto;
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 1rem;
  line-height: 1;
  padding: 0 0.25rem;
  opacity: 0;
  transition: opacity 0.15s;
}

.task-item:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  color: #ef4444;
}

.task-text :deep(a) {
  color: var(--accent);
  text-decoration: none;
}

.task-text :deep(a:hover) {
  text-decoration: underline;
}

.empty {
  color: var(--text-muted);
  font-style: italic;
  font-size: 0.85rem;
}

.loading {
  color: var(--text-muted);
  text-align: center;
  margin-top: 3rem;
}
</style>
