<template>
  <div class="board-card" :data-board-name="board.name">
    <div class="board-header" @click="$emit('navigate')">
      <h2 class="board-name">{{ board.name }}</h2>
      <p class="column-label">{{ board.column_name }}</p>
    </div>
    <VueDraggable
      v-model="localTasks"
      tag="ul"
      class="task-list"
      group="dashboard-tasks"
      ghost-class="ghost"
      drag-class="dragging"
      :disabled="!props.dragEnabled"
      @start="onDragStart"
      @end="onDragEnd"
    >
      <li
        v-for="(task, i) in localTasks"
        :key="task.text"
        class="task-item"
        :class="{ completed: task.completed }"
      >
        <span class="checkbox" @click.stop="onComplete(i)">☐</span>
        <span class="task-text" v-html="renderTask(task.text)"></span>
        <button class="delete-btn" @click.stop="$emit('delete-task', board.name, columnIndex, i)" title="Remove task">&times;</button>
      </li>
    </VueDraggable>
    <p v-if="!localTasks || localTasks.length === 0" class="empty">No active tasks</p>
    <form class="inline-add" @submit.prevent="onAdd" @click.stop>
      <input
        v-model="newText"
        class="inline-input"
        type="text"
        placeholder="+ Add task…"
        @focus="inputFocused = true"
        @blur="inputFocused = false"
      />
    </form>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { VueDraggable } from 'vue-draggable-plus'
import { useObsidian, columnIndexFor } from '../composables/useObsidian.js'

const props = defineProps({
  board: { type: Object, required: true },
  dragEnabled: { type: Boolean, default: false },
})

const emit = defineEmits(['delete-task', 'move-task', 'complete-task', 'add-task', 'navigate'])

const { renderTask } = useObsidian()
const localTasks = ref([...(props.board.tasks || [])])

// Use column_index from API if available, fall back to config
const columnIndex = props.board.column_index ?? columnIndexFor(props.board.name)
const newText = ref('')
const inputFocused = ref(false)

function onComplete(index) {
  localTasks.value.splice(index, 1)
  emit('complete-task', props.board.name, columnIndex, index)
}

function onAdd() {
  const text = newText.value.trim()
  if (!text) return
  emit('add-task', props.board.name, columnIndex, text)
  newText.value = ''
}

// Sync when parent data updates (WS push), but not during a drag
let dragging = false

watch(() => props.board.tasks, (newTasks) => {
  if (!dragging) {
    localTasks.value = [...(newTasks || [])]
  }
}, { deep: true })

function onDragStart(evt) {
  dragging = true
  window.__obanDragSource = {
    board: props.board.name,
    column: columnIndex,
    index: evt.oldIndex,
  }
}

function onDragEnd(evt) {
  const source = window.__obanDragSource
  window.__obanDragSource = null
  dragging = false

  // Figure out which board the item landed in
  const toEl = evt.to
  const toBoardName = toEl?.closest('.board-card')?.dataset?.boardName
  const fromBoardName = source?.board

  if (!fromBoardName || !toBoardName) return

  // If dropped in the same board at the same index, ignore
  if (fromBoardName === toBoardName && evt.oldIndex === evt.newIndex) return

  const toColumnIndex = columnIndexFor(toBoardName)

  emit('move-task', {
    from_board: fromBoardName,
    from_column: source.column,
    from_index: evt.oldIndex,
    to_board: toBoardName,
    to_column: toColumnIndex,
    to_index: evt.newIndex,
  })
}
</script>

<style scoped>
.board-card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  transition: border-color 0.15s;
}

.board-header {
  cursor: pointer;
}

.board-header:hover .board-name {
  color: var(--accent);
}

.board-name {
  margin: 0 0 0.25rem;
  font-size: 1.1rem;
  color: var(--text-primary);
  transition: color 0.15s;
}

.column-label {
  margin: 0 0 0.75rem;
  font-size: 0.8rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.task-list {
  list-style: none;
  margin: 0;
  padding: 0;
  min-height: 2rem;
}

.task-item {
  padding: 0.4rem 0.25rem;
  border-bottom: 1px solid var(--border-light);
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  font-size: 0.9rem;
  color: var(--text-primary);
  border-radius: 4px;
}

.task-item:last-child {
  border-bottom: none;
}

.task-item.completed {
  opacity: 0.5;
  text-decoration: line-through;
}

.ghost {
  opacity: 0.4;
  background: var(--accent);
  border-radius: 4px;
}

.dragging {
  background: var(--card-bg);
  border: 1px dashed var(--accent);
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.checkbox {
  flex-shrink: 0;
  cursor: pointer;
}

.checkbox:hover {
  color: var(--accent);
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

.inline-add {
  margin-top: 0.5rem;
  opacity: 0;
  max-height: 0;
  overflow: hidden;
  transition: opacity 0.15s, max-height 0.15s;
}

.board-card:hover .inline-add,
.inline-add:focus-within {
  opacity: 1;
  max-height: 3rem;
}

.inline-input {
  width: 100%;
  padding: 0.35rem 0.5rem;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: transparent;
  color: var(--text-primary);
  font-size: 0.85rem;
  outline: none;
}

.inline-input::placeholder {
  color: var(--text-muted);
}

@media (max-width: 640px) {
  .board-card {
    padding: 1rem;
    border-radius: 8px;
  }

  .board-name {
    font-size: 1rem;
  }

  .column-label {
    margin-bottom: 0.5rem;
  }

  .task-item {
    padding: 0.3rem 0;
    font-size: 0.85rem;
  }

  .delete-btn {
    opacity: 0.5;
  }

  .inline-add {
    opacity: 1;
    max-height: 3rem;
  }
}

.inline-input:focus {
  border-color: var(--accent);
}
</style>
