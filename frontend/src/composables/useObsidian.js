import { ref } from 'vue'

const vault = ref('')
const defaultColumn = ref(1)
const boardColumns = ref({})
const pinnedBoard = ref('')
const wipLimit = ref(15)

export async function loadObsidianConfig() {
  if (vault.value) return
  try {
    const API_BASE = import.meta.env.VITE_API_URL || ''
    const res = await fetch(`${API_BASE}/api/config`)
    const data = await res.json()
    vault.value = data.obsidian_vault
    defaultColumn.value = data.default_column ?? 1
    boardColumns.value = data.board_columns ?? {}
    pinnedBoard.value = data.pinned_board ?? ''
    wipLimit.value = data.wip_limit ?? 15
  } catch (e) {
    console.error('Failed to load obsidian config:', e)
  }
}

export function getPinnedBoard() {
  return pinnedBoard.value
}

export function getWipLimit() {
  return wipLimit.value
}

export function columnIndexFor(boardName) {
  return boardColumns.value[boardName] ?? defaultColumn.value
}

export function useObsidian() {
  function renderTask(text) {
    // Convert [[wiki links]] to obsidian:// URIs
    let rendered = text.replace(/\[\[([^\]]+)\]\]/g, (_, note) => {
      if (vault.value) {
        const uri = `obsidian://open?vault=${encodeURIComponent(vault.value)}&file=${encodeURIComponent(note)}`
        return `<a href="${uri}" class="obsidian-link">${note}</a>`
      }
      return `<em>${note}</em>`
    })
    // Convert [text](url) markdown links to anchor tags
    rendered = rendered.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
    return rendered
  }

  return { renderTask }
}
