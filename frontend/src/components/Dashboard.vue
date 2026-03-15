<template>
  <div class="dashboard">
    <header class="header">
      <h1>Oban</h1>
      <span class="status" :class="{ online: connected }">
        {{ connected ? 'Live' : 'Reconnecting…' }}
      </span>
    </header>

    <form class="quick-add" @submit.prevent="addTask">
      <select v-model="selectedBoard" class="board-select">
        <option value="" disabled>Board…</option>
        <option v-for="name in boardNames" :key="name" :value="name">{{ name }}</option>
      </select>
      <input
        v-model="newTaskText"
        class="task-input"
        type="text"
        placeholder="Add a task…"
        :disabled="!selectedBoard"
      />
      <button type="submit" class="add-btn" :disabled="!selectedBoard || !newTaskText.trim()">Add</button>
    </form>

    <div class="board-grid">
      <BoardCard
        v-for="board in boards"
        :key="board.name"
        :board="board"
        @navigate="$router.push(`/board/${encodeURIComponent(board.name)}`)"
        @delete-task="deleteTask"
        @move-task="moveTask"
        @complete-task="completeTask"
        @add-task="addTaskToBoard"
      />
    </div>
    <p v-if="boards.length === 0" class="no-boards">No boards with active tasks found.</p>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import BoardCard from './BoardCard.vue'
import { useWebSocket } from '../composables/useWebSocket.js'
import { getPinnedBoard } from '../composables/useObsidian.js'

const API_BASE = import.meta.env.VITE_API_URL || ''
const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
const WS_URL = import.meta.env.VITE_WS_URL || `${wsProtocol}//${window.location.host}/ws`

const boards = ref([])
const boardNames = ref([])
const selectedBoard = ref('')
const newTaskText = ref('')
const { data: wsData, connected } = useWebSocket(WS_URL)

function sortBoards(list) {
  const pinned = getPinnedBoard()
  return list.slice().sort((a, b) => {
    if (pinned) {
      if (a.name === pinned) return -1
      if (b.name === pinned) return 1
    }
    return a.name.localeCompare(b.name)
  })
}

watch(wsData, (payload) => {
  if (payload && payload.boards) {
    boards.value = sortBoards(payload.boards)
  }
})

onMounted(async () => {
  try {
    const [boardsRes, namesRes] = await Promise.all([
      fetch(`${API_BASE}/api/boards`),
      fetch(`${API_BASE}/api/board-names`),
    ])
    const boardsData = await boardsRes.json()
    const namesData = await namesRes.json()

    if (boardsData.boards && boards.value.length === 0) {
      boards.value = sortBoards(boardsData.boards)
    }
    boardNames.value = namesData.names
    if (!selectedBoard.value) {
      const pinned = getPinnedBoard()
      selectedBoard.value = pinned && namesData.names.includes(pinned) ? pinned : (namesData.names[0] || '')
    }
  } catch (e) {
    console.error('Failed to fetch initial data:', e)
  }
})

async function addTaskToBoard(boardName, columnIndex, text) {
  try {
    await fetch(`${API_BASE}/api/tasks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ board: boardName, text, column_index: columnIndex }),
    })
  } catch (e) {
    console.error('Failed to add task:', e)
  }
}

async function completeTask(boardName, columnIndex, taskIndex) {
  // Move to next column (e.g. Working -> Done, Inbox -> Triaged)
  try {
    await fetch(`${API_BASE}/api/tasks/move`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        from_board: boardName,
        from_column: columnIndex,
        from_index: taskIndex,
        to_board: boardName,
        to_column: columnIndex + 1,
        to_index: 0,
      }),
    })
  } catch (e) {
    console.error('Failed to complete task:', e)
  }
}

async function moveTask(move) {
  try {
    await fetch(`${API_BASE}/api/tasks/move`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(move),
    })
  } catch (e) {
    console.error('Failed to move task:', e)
  }
}

async function deleteTask(boardName, columnIndex, taskIndex) {
  try {
    await fetch(`${API_BASE}/api/tasks`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ board: boardName, column_index: columnIndex, task_index: taskIndex }),
    })
  } catch (e) {
    console.error('Failed to delete task:', e)
  }
}

async function addTask() {
  const text = newTaskText.value.trim()
  if (!text || !selectedBoard.value) return

  try {
    const res = await fetch(`${API_BASE}/api/tasks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ board: selectedBoard.value, text }),
    })
    if (res.ok) {
      newTaskText.value = ''
    }
  } catch (e) {
    console.error('Failed to add task:', e)
  }
}
</script>

<style scoped>
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.5rem;
}

.header h1 {
  margin: 0;
  font-size: 1.5rem;
  color: var(--text-primary);
}

.status {
  font-size: 0.8rem;
  padding: 0.25rem 0.6rem;
  border-radius: 999px;
  background: var(--border);
  color: var(--text-muted);
}

.status.online {
  background: #22c55e22;
  color: #22c55e;
}

.quick-add {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
}

.board-select {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--card-bg);
  color: var(--text-primary);
  font-size: 0.9rem;
  min-width: 150px;
}

.task-input {
  flex: 1;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--card-bg);
  color: var(--text-primary);
  font-size: 0.9rem;
}

.task-input::placeholder {
  color: var(--text-muted);
}

.add-btn {
  padding: 0.5rem 1.25rem;
  border: none;
  border-radius: 8px;
  background: var(--accent);
  color: white;
  font-size: 0.9rem;
  cursor: pointer;
}

.add-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.board-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;
}

.no-boards {
  text-align: center;
  color: var(--text-muted);
  margin-top: 3rem;
}
</style>
