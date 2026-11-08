/**
 * Sidebar insights for the OpenCode TUI.
 *
 * Adds session timestamps and a git working-tree panel to the session sidebar.
 * The git panel refreshes on filesystem, branch, and turn-completion events,
 * with a slow poll as a fallback for changes the watcher misses.
 */
import { Plugin } from "@opencode/plugin/tui"
import { createEffect, createMemo, createSignal, For, onCleanup, Show } from "solid-js"

type FileStatus = {
  readonly file: string
  readonly additions: number
  readonly deletions: number
  readonly status: "added" | "deleted" | "modified"
}

type VcsInfo = {
  readonly provider?: string
  readonly branch: {
    readonly current?: string
    readonly default?: string
  }
}

const clock = new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" })
const monthDay = new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" })
const monthDayYear = new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", year: "numeric" })

function clockTime(value: number) {
  return clock.format(new Date(value))
}

function dateLabel(value: number) {
  const date = new Date(value)
  return date.getFullYear() === new Date().getFullYear() ? monthDay.format(date) : monthDayYear.format(date)
}

function relative(value: number, now: number) {
  const minutes = Math.floor((now - value) / 60_000)
  if (minutes < 1) return "now"
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days < 30) return `${days}d ago`
  const months = Math.floor(days / 30)
  if (months < 12) return `${months}mo ago`
  return `${Math.floor(days / 365)}y ago`
}

function lastMessageLabel(value: number, now: number) {
  const date = new Date(value)
  const today = new Date(now)
  if (date.toDateString() === today.toDateString()) return `${clockTime(value)} · ${relative(value, now)}`
  return `${dateLabel(value)} · ${clockTime(value)}`
}

function compact(value: number) {
  if (value >= 10_000) return `${Math.floor(value / 1000)}k`
  if (value >= 1000) return `${(value / 1000).toFixed(1)}k`
  return String(value)
}

function middleTruncate(value: string, max: number) {
  if (value.length <= max) return value
  const keepStart = Math.ceil((max - 1) / 2)
  const keepEnd = Math.floor((max - 1) / 2)
  return value.slice(0, keepStart) + "…" + value.slice(-keepEnd)
}

function statusMark(status: FileStatus["status"]) {
  if (status === "added") return "A"
  if (status === "deleted") return "D"
  return "M"
}

function SessionTimes(props: { context: Plugin.Context; sessionID: string }) {
  const theme = props.context.theme
  const session = createMemo(() => props.context.data.session.get(props.sessionID))
  const messages = createMemo(() => props.context.data.session.message.list(props.sessionID) ?? [])
  const created = createMemo(() => session()?.time.created)
  // Latest timestamp across the transcript, including the user prompt and the assistant reply.
  const last = createMemo(() => {
    let value = 0
    for (const message of messages()) value = Math.max(value, message.time?.created ?? 0)
    return value || undefined
  })
  const [now, setNow] = createSignal(Date.now())
  const ticker = setInterval(() => setNow(Date.now()), 30_000)
  onCleanup(() => clearInterval(ticker))

  return (
    <box>
      <text fg={theme.text.base}>
        <b>Session</b>
      </text>
      <box flexDirection="row" justifyContent="space-between" gap={1}>
        <text fg={theme.text.muted} flexShrink={0}>
          Created
        </text>
        <text fg={theme.text.base} wrapMode="none" truncate>
          <Show when={created()} fallback="—">
            {(value) => `${clockTime(value())} · ${dateLabel(value())}`}
          </Show>
        </text>
      </box>
      <box flexDirection="row" justifyContent="space-between" gap={1}>
        <text fg={theme.text.muted} flexShrink={0}>
          Last message
        </text>
        <text fg={last() ? theme.text.base : theme.text.muted} wrapMode="none" truncate>
          <Show when={last()} fallback="None yet">
            {(value) => lastMessageLabel(value(), now())}
          </Show>
        </text>
      </box>
    </box>
  )
}

function GitSection(props: { context: Plugin.Context; sessionID: string }) {
  const theme = props.context.theme
  const session = createMemo(() => props.context.data.session.get(props.sessionID))
  const directory = createMemo(() => session()?.location.directory)
  const [info, setInfo] = createSignal<VcsInfo>()
  const [files, setFiles] = createSignal<FileStatus[]>()
  let sequence = 0
  let throttle: ReturnType<typeof setTimeout> | undefined

  const refresh = async () => {
    const location = directory()
    if (!location) return
    const id = ++sequence
    const [vcs, status] = await Promise.all([
      props.context.client.vcs.get({ location: { directory: location } }).catch(() => undefined),
      props.context.client.vcs.status({ location: { directory: location } }).catch(() => undefined),
    ])
    if (id !== sequence) return
    if (vcs) setInfo(vcs.data)
    if (status) setFiles(status.data)
  }

  const schedule = () => {
    if (throttle) return
    throttle = setTimeout(() => {
      throttle = undefined
      void refresh()
    }, 1500)
  }

  const matches = (location?: { directory: string }) => !location || location.directory === directory()

  createEffect(() => {
    directory()
    setInfo(undefined)
    setFiles(undefined)
    void refresh()
  })

  const poller = setInterval(() => void refresh(), 30_000)
  const stops = [
    props.context.data.on("filesystem.changed", (event) => {
      if (matches(event.location)) schedule()
    }),
    props.context.data.on("vcs.branch.updated", (event) => {
      if (matches(event.location)) schedule()
    }),
    props.context.data.on("session.execution.succeeded", (event) => {
      if (event.data.sessionID === props.sessionID) schedule()
    }),
    props.context.data.on("session.execution.failed", (event) => {
      if (event.data.sessionID === props.sessionID) schedule()
    }),
  ]

  onCleanup(() => {
    sequence++
    clearInterval(poller)
    if (throttle) clearTimeout(throttle)
    for (const stop of stops) stop()
  })

  const available = createMemo(() => Boolean(info()?.provider) || (files()?.length ?? 0) > 0)
  const title = createMemo(() => {
    const provider = info()?.provider
    if (!provider || provider === "git") return "Git"
    if (provider === "hg") return "Hg"
    return provider.charAt(0).toUpperCase() + provider.slice(1)
  })
  const branch = createMemo(() => info()?.branch?.current)
  const additions = createMemo(() => (files() ?? []).reduce((total, file) => total + file.additions, 0))
  const deletions = createMemo(() => (files() ?? []).reduce((total, file) => total + file.deletions, 0))
  const shown = createMemo(() => (files() ?? []).slice(0, 8))
  const remaining = createMemo(() => Math.max(0, (files()?.length ?? 0) - shown().length))
  const count = createMemo(() => files()?.length ?? 0)

  const color = (status: FileStatus["status"]) => {
    if (status === "added") return theme.diff.text.added
    if (status === "deleted") return theme.diff.text.removed
    return theme.text.feedback.warning.base
  }

  const openDiff = () => props.context.keymap.dispatch("diff.open")

  return (
    <Show when={available()}>
      <box>
        <box flexDirection="row" justifyContent="space-between" gap={1} onMouseUp={openDiff}>
          <text fg={theme.text.base}>
            <b>{title()}</b>
          </text>
          <text fg={theme.text.muted}>diff</text>
        </box>
        <box flexDirection="row" justifyContent="space-between" gap={1}>
          <text fg={theme.text.base} wrapMode="none" truncate>
            {branch() ?? "detached HEAD"}
          </text>
          <Show when={count() > 0}>
            <box flexDirection="row" gap={1} flexShrink={0}>
              <Show when={additions() > 0}>
                <text fg={theme.diff.text.added}>+{compact(additions())}</text>
              </Show>
              <Show when={deletions() > 0}>
                <text fg={theme.diff.text.removed}>-{compact(deletions())}</text>
              </Show>
            </box>
          </Show>
        </box>
        <Show when={files()}>
          {(list) => (
            <Show when={list().length > 0} fallback={<text fg={theme.text.muted}>Working tree clean</text>}>
              <text fg={theme.text.muted}>
                {count()} file{count() === 1 ? "" : "s"} changed
              </text>
              <For each={shown()}>
                {(file) => (
                  <box flexDirection="row" gap={1} onMouseUp={openDiff}>
                    <text fg={color(file.status)} flexShrink={0}>
                      {statusMark(file.status)}
                    </text>
                    <text fg={theme.text.base} wrapMode="none" truncate flexGrow={1} flexShrink={1} minWidth={0}>
                      {middleTruncate(file.file, 26)}
                    </text>
                    <Show when={file.additions > 0}>
                      <text fg={theme.diff.text.added} flexShrink={0}>
                        +{compact(file.additions)}
                      </text>
                    </Show>
                    <Show when={file.deletions > 0}>
                      <text fg={theme.diff.text.removed} flexShrink={0}>
                        -{compact(file.deletions)}
                      </text>
                    </Show>
                  </box>
                )}
              </For>
              <Show when={remaining() > 0}>
                <text fg={theme.text.muted}>… {remaining()} more · open diff</text>
              </Show>
            </Show>
          )}
        </Show>
      </box>
    </Show>
  )
}

function SidebarInsights(props: { context: Plugin.Context; sessionID: string }) {
  return (
    <box gap={1}>
      <SessionTimes context={props.context} sessionID={props.sessionID} />
      <GitSection context={props.context} sessionID={props.sessionID} />
    </box>
  )
}

export default Plugin.define({
  id: "local.sidebar-insights",
  setup(context) {
    context.ui.slot({
      prepend: "sidebar.content",
      render: (props) => <SidebarInsights context={context} sessionID={props.sessionID} />,
    })
  },
})
