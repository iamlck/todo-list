// Every request to the backend goes through here, so the token, the JSON
// headers and 401 handling are written once.

const BASE = '/api' // Vite proxies this to FastAPI (see vite.config.js)

const TOKEN_KEY = 'learning-tracker-token'

export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    // Private windows and blocked site data: behave as signed out.
    return null
  }
}

export function setToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    /* not fatal: the session just will not survive a reload */
  }
}

// Set by AuthContext so an expired token drops the user back to the login
// screen no matter which call discovered it.
let onUnauthorized = () => {}
export function setUnauthorizedHandler(fn) {
  onUnauthorized = fn
}

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

async function request(method, path, body, options = {}) {
  const token = getToken()
  const response = await fetch(BASE + path, {
    method,
    headers: {
      ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  // A 401 from signing in means "wrong credentials" and must keep the
  // server's own message. A 401 from anywhere else means the token is no
  // longer good, which signs the user out.
  if (response.status === 401 && !options.isAuthAttempt) {
    onUnauthorized()
    throw new ApiError('Your session has expired. Please sign in again.', 401)
  }

  if (!response.ok) {
    let detail = `Request failed (${response.status})`
    try {
      const data = await response.json()
      if (typeof data.detail === 'string') detail = data.detail
    } catch {
      /* keep the generic message */
    }
    throw new ApiError(detail, response.status)
  }

  if (response.status === 204) return null
  return response.json()
}

export const api = {
  // --- auth
  signup: (email, password) =>
    request('POST', '/auth/signup', { email, password }, { isAuthAttempt: true }),
  login: (email, password) =>
    request('POST', '/auth/login', { email, password }, { isAuthAttempt: true }),
  me: () => request('GET', '/auth/me'),
  forgotPassword: (email) =>
    request('POST', '/auth/forgot-password', { email }, { isAuthAttempt: true }),
  resetPassword: (token, password) =>
    request('POST', '/auth/reset-password', { token, password }, { isAuthAttempt: true }),
  changePassword: (currentPassword, newPassword) =>
    request('POST', '/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    }),
  accountSummary: () => request('GET', '/auth/account-summary'),
  deleteAccount: (password, confirmEmail) =>
    request('DELETE', '/auth/account', { password, confirm_email: confirmEmail }),

  // --- the plan
  getPlan: () => request('GET', '/me/plan'),
  setupPlan: (body) => request('POST', '/me/plan/setup', body),
  setStartDate: (startDate) => request('PUT', '/me/settings', { start_date: startDate }),

  addDay: (title) => request('POST', '/me/days', { title }),
  renameDay: (dayId, title) => request('PATCH', `/me/days/${dayId}`, { title }),
  deleteDay: (dayId) => request('DELETE', `/me/days/${dayId}`),
  dayDeleteImpact: (dayId) => request('GET', `/me/days/${dayId}/delete-impact`),
  reorderDays: (ids) => request('PUT', '/me/days/reorder', { ids }),

  addTask: (dayId, title, parentId = null) =>
    request('POST', '/me/tasks', { day_id: dayId, parent_id: parentId, title }),
  renameTask: (taskId, title) => request('PATCH', `/me/tasks/${taskId}`, { title }),
  deleteTask: (taskId) => request('DELETE', `/me/tasks/${taskId}`),
  reorderTasks: (dayId, parentId, ids) =>
    request('PUT', '/me/tasks/reorder', { day_id: dayId, parent_id: parentId, ids }),

  // --- progress and time
  setCompleted: (taskId, completed) => request('PUT', `/me/progress/${taskId}`, { completed }),
  setStarted: (taskId, started) => request('PUT', `/me/progress/${taskId}/start`, { started }),
  setNotes: (taskId, notes) => request('PUT', `/me/progress/${taskId}/notes`, { notes }),
  setTime: (taskId, body) => request('PUT', `/me/progress/${taskId}/time`, body),
  startTimer: (taskId) => request('POST', `/me/progress/${taskId}/timer/start`),
  stopTimer: (taskId) => request('POST', `/me/progress/${taskId}/timer/stop`),

  // --- carry forward and undo
  carryForward: (dayId, { taskIds = null, targetDayId = null, direction = 'next' } = {}) =>
    request('POST', `/me/days/${dayId}/carry-forward`, {
      task_ids: taskIds,
      target_day_id: targetDayId,
      direction,
    }),
  moveTasks: (taskIds, targetDayId) =>
    request('POST', '/me/tasks/move', { task_ids: taskIds, target_day_id: targetDayId }),
  restoreDay: (snapshot) => request('POST', '/me/days/restore', snapshot),
  restoreTask: (snapshot) => request('POST', '/me/tasks/restore', snapshot),

  // --- history
  deletedTasks: () => request('GET', '/me/deleted-tasks'),

  // --- administration
  adminUsers: (q = '') =>
    request('GET', `/admin/users${q ? `?q=${encodeURIComponent(q)}` : ''}`),
  adminSetAdmin: (userId, isAdmin) =>
    request('PATCH', `/admin/users/${userId}`, { is_admin: isAdmin }),
  adminDeleteUser: (userId, password, confirmEmail) =>
    request('DELETE', `/admin/users/${userId}`, {
      password,
      confirm_email: confirmEmail,
    }),
}
