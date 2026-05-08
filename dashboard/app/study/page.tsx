'use client'

import { useEffect, useMemo, useState } from 'react'
import useSWR from 'swr'
import {
  BookOpen,
  CalendarDays,
  Check,
  ClipboardList,
  FileDown,
  Gamepad2,
  History,
  Inbox,
  Layers,
  NotebookPen,
  PlayCircle,
  RefreshCw,
  Search,
  Sparkles,
  Star,
  UploadCloud,
} from 'lucide-react'
import Navigation from '@/components/Navigation'

const fetcher = (url: string) => fetch(url).then((res) => res.json())

type SourceStatus = {
  source_kind: string
  status: string
  configured: boolean
  item_count: number
  detail: string
}

type StudyItem = {
  item_id: string
  source_kind: string
  title: string
  summary: string
  why_it_matters: string
  technologies: string[]
  source_url: string
  reading_depth: 'skim' | 'read' | 'deep'
  suggested_action: string
  status: string
  score: number
}

type Brief = {
  brief_id: string
  title: string
  brief_date: string
  item_ids: string[]
  artifact_pdf_path?: string | null
  exports: Array<Record<string, unknown>>
}

type StudyState = {
  status: 'ok' | 'degraded'
  today: string
  sources: SourceStatus[]
  items: StudyItem[]
  briefs: Brief[]
  daily_schedule: {
    local_time?: string
    next_run_at?: string
  }
}

type ActionState = {
  busy: string
  message: string
}

type PersonalRecommendation = {
  recommendation_id: string
  kind: string
  title: string
  summary: string
  reason: string
  source_app: string
  score: number
  estimated_minutes: number
  actions: string[]
}

type PersonalRow = {
  row_id: string
  title: string
  reason: string
  items: PersonalRecommendation[]
}

type PersonalPlan = {
  plan_id: string
  plan_date: string
  title: string
  status: string
  blocks: Array<{
    block_id: string
    kind: string
    title: string
    minutes: number
    status: string
  }>
  export_job_ids: string[]
}

type PersonalCard = {
  card_id: string
  front: string
  back: string
  due_at: string
  review_count: number
  tags: string[]
}

type PersonalExport = {
  export_id: string
  target: string
  status: string
  title: string
  artifact_paths: string[]
  copied_paths: string[]
}

type PersonalState = {
  status: 'ok' | 'degraded' | 'disabled' | 'missing_dependency'
  enabled: boolean
  rows: PersonalRow[]
  active_plan?: PersonalPlan | null
  due_cards: PersonalCard[]
  exports: PersonalExport[]
  metadata: Record<string, unknown>
}

const sourceLabels: Record<string, string> = {
  x_bookmarks: 'X 书签',
  youtube_playlist: 'YouTube 深读',
  rss: '技术源',
  local: '项目主题',
}

const statusLabels: Record<string, string> = {
  new: '新',
  unread: '待读',
  read: '已读',
  annotated: '已批注',
  synthesized: '已沉淀',
  archived: '已归档',
}

const personalTabs = [
  { id: 'inbox', label: 'Inbox', icon: Inbox },
  { id: 'today', label: 'Today', icon: CalendarDays },
  { id: 'for-you', label: 'For You', icon: Star },
  { id: 'deep', label: 'Deep Study', icon: BookOpen },
  { id: 'review', label: 'Review', icon: ClipboardList },
  { id: 'cards', label: 'Cards', icon: Layers },
  { id: 'entertainment', label: 'Entertainment', icon: Gamepad2 },
  { id: 'exports', label: 'Exports', icon: UploadCloud },
  { id: 'history', label: 'History', icon: History },
] as const

type PersonalTab = (typeof personalTabs)[number]['id']

export default function StudyDashboardPage() {
  const { data, error, mutate, isLoading } = useSWR<StudyState>('/api/study-dashboard/state', fetcher, {
    refreshInterval: 30000,
  })
  const { data: personal, mutate: mutatePersonal } = useSWR<PersonalState>('/api/personal/state', fetcher, {
    refreshInterval: 30000,
    shouldRetryOnError: false,
  })
  const [action, setAction] = useState<ActionState>({ busy: '', message: '' })
  const [activeTab, setActiveTab] = useState<PersonalTab>('today')

  const latestBrief = data?.briefs?.[0]
  const videoItems = useMemo(
    () => (data?.items || []).filter((item) => item.source_kind === 'youtube_playlist').slice(0, 5),
    [data?.items],
  )
  const deepItems = useMemo(
    () => (data?.items || []).filter((item) => item.reading_depth === 'deep').slice(0, 6),
    [data?.items],
  )
  const techQueue = useMemo(
    () => (data?.items || []).filter((item) => item.status !== 'synthesized').slice(0, 10),
    [data?.items],
  )

  useEffect(() => {
    if (!isLoading && data && data.items.length === 0 && action.busy !== '刷新') {
      let cancelled = false
      setAction({ busy: '刷新', message: '' })
      fetch('/api/study-dashboard/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ force: false }),
      })
        .then(() => mutate())
        .then(() => {
          if (!cancelled) {
            setAction({ busy: '', message: '刷新 完成' })
          }
        })
        .catch(() => {
          if (!cancelled) {
            setAction({ busy: '', message: '刷新 失败' })
          }
        })
      return () => {
        cancelled = true
      }
    }
    return undefined
  }, [action.busy, data, isLoading, mutate])

  async function runAction(label: string, task: () => Promise<void>) {
    setAction({ busy: label, message: '' })
    try {
      await task()
      await mutate()
      setAction({ busy: '', message: `${label} 完成` })
    } catch (err) {
      setAction({ busy: '', message: `${label} 失败` })
    }
  }

  async function refreshSources() {
    await fetch('/api/study-dashboard/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ force: true }),
    })
  }

  async function generateDailyBrief() {
    const briefResponse = await fetch('/api/study-dashboard/briefs/daily', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ targets: ['both'], auto_refresh: true }),
    })
    const brief = await briefResponse.json()
    await exportBrief(brief.brief_id, 'both')
  }

  async function exportBrief(briefId: string, target: 'goodnotes' | 'marginnote' | 'both') {
    await fetch(`/api/study-dashboard/briefs/${briefId}/export`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target }),
    })
  }

  async function itemAction(itemId: string, itemAction: string) {
    await fetch(`/api/study-dashboard/items/${itemId}/actions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: itemAction }),
    })
  }

  async function personalPost(path: string, body: Record<string, unknown>) {
    const response = await fetch(`/api/personal/${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!response.ok) {
      throw new Error(`personal action failed: ${path}`)
    }
    return response.json()
  }

  async function generatePersonalPlan() {
    await personalPost('plans/daily', {
      mood: 'mixed',
      focus: 'medium',
      available_minutes: 120,
      auto_export: true,
    })
    await mutatePersonal()
  }

  async function createPersonalCards() {
    await personalPost('cards', { limit: 12 })
    await mutatePersonal()
  }

  async function exportPersonalPack() {
    await personalPost('exports', { target: 'both', title: 'Personal study pack' })
    await mutatePersonal()
  }

  if (error) {
    return (
      <>
        <Navigation />
        <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <div className="rounded-lg border border-red-500/40 bg-red-950/40 p-6 text-red-100">
            学习手帐加载失败
          </div>
        </main>
      </>
    )
  }

  return (
    <>
      <Navigation />
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <section className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="mb-2 text-sm font-medium text-emerald-300">{data?.today || '...'}</p>
            <h1 className="text-3xl font-bold text-white sm:text-4xl">学习手帐</h1>
            <p className="mt-2 max-w-2xl text-sm text-slate-300">
              GoodNotes 日批注，MarginNote4 深读，技术雷达自动沉淀。
            </p>
          </div>
          <div className="grid grid-cols-3 gap-2 sm:flex sm:flex-wrap sm:justify-end">
            <CommandButton
              label="刷新"
              icon={<RefreshCw className="h-4 w-4" />}
              busy={action.busy === '刷新'}
              onClick={() => runAction('刷新', refreshSources)}
            />
            <CommandButton
              label="手帐"
              icon={<NotebookPen className="h-4 w-4" />}
              busy={action.busy === '手帐'}
              onClick={() => runAction('手帐', generateDailyBrief)}
            />
            <CommandButton
              label="GoodNotes"
              icon={<FileDown className="h-4 w-4" />}
              disabled={!latestBrief}
              busy={action.busy === 'GoodNotes'}
              onClick={() => latestBrief && runAction('GoodNotes', () => exportBrief(latestBrief.brief_id, 'goodnotes'))}
            />
            <CommandButton
              label="MarginNote"
              icon={<BookOpen className="h-4 w-4" />}
              disabled={!latestBrief}
              busy={action.busy === 'MarginNote'}
              onClick={() => latestBrief && runAction('MarginNote', () => exportBrief(latestBrief.brief_id, 'marginnote'))}
            />
            <CommandButton
              label="深挖"
              icon={<Search className="h-4 w-4" />}
              disabled={!deepItems[0]}
              busy={action.busy === '深挖'}
              onClick={() => deepItems[0] && runAction('深挖', () => itemAction(deepItems[0].item_id, 'deep_dive'))}
            />
            <CommandButton
              label="卡片"
              icon={<Layers className="h-4 w-4" />}
              disabled={!techQueue[0]}
              busy={action.busy === '卡片'}
              onClick={() => techQueue[0] && runAction('卡片', () => itemAction(techQueue[0].item_id, 'generate_cards'))}
            />
            <CommandButton
              label="计划"
              icon={<CalendarDays className="h-4 w-4" />}
              busy={action.busy === '计划'}
              onClick={() => runAction('计划', generatePersonalPlan)}
            />
          </div>
        </section>

        <section className="mb-6">
          <div className="mb-3 flex gap-2 overflow-x-auto pb-1">
            {personalTabs.map((tab) => {
              const Icon = tab.icon
              const active = activeTab === tab.id
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex h-10 shrink-0 items-center gap-2 rounded-lg border px-3 text-sm font-medium ${
                    active
                      ? 'border-emerald-400 bg-emerald-950/60 text-emerald-100'
                      : 'border-slate-700 bg-slate-900 text-slate-300 hover:border-slate-500'
                  }`}
                  title={tab.label}
                >
                  <Icon className="h-4 w-4" />
                  <span>{tab.label}</span>
                </button>
              )
            })}
          </div>
          <PersonalControlPanel
            activeTab={activeTab}
            personal={personal}
            studyItems={data?.items || []}
            onPlan={() => runAction('计划', generatePersonalPlan)}
            onCards={() => runAction('Personal Cards', createPersonalCards)}
            onExport={() => runAction('Personal Export', exportPersonalPack)}
          />
        </section>

        <section className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
          {(data?.sources || []).map((source) => (
            <div key={source.source_kind} className="rounded-lg border border-slate-700 bg-slate-900/70 p-4">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-semibold text-white">{sourceLabels[source.source_kind] || source.source_kind}</p>
                <span className={source.status === 'connected' ? 'text-emerald-300' : 'text-amber-300'}>
                  {source.item_count}
                </span>
              </div>
              <p className="mt-2 truncate text-xs text-slate-400">{source.configured ? source.status : '未连接'}</p>
            </div>
          ))}
        </section>

        <section className="mb-6 grid gap-4 lg:grid-cols-[1.4fr_0.9fr]">
          <div className="rounded-lg border border-slate-700 bg-slate-900/80 p-4">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-white">今日必读</h2>
              <span className="text-xs text-slate-400">
                {isLoading ? '加载中' : `${data?.items?.length || 0} 条`}
              </span>
            </div>
            <div className="grid gap-3">
              {(data?.items || []).slice(0, 6).map((item) => (
                <StudyItemRow key={item.item_id} item={item} onAction={(next) => runAction(next, () => itemAction(item.item_id, next))} />
              ))}
            </div>
          </div>

          <div className="grid gap-4">
            <div className="rounded-lg border border-slate-700 bg-slate-900/80 p-4">
              <div className="mb-3 flex items-center gap-2">
                <PlayCircle className="h-5 w-5 text-rose-300" />
                <h2 className="text-lg font-semibold text-white">视频深读</h2>
              </div>
              <div className="space-y-3">
                {videoItems.map((item) => (
                  <CompactItem key={item.item_id} item={item} />
                ))}
                {!videoItems.length && <p className="text-sm text-slate-400">专用播放列表未连接</p>}
              </div>
            </div>

            <div className="rounded-lg border border-slate-700 bg-slate-900/80 p-4">
              <div className="mb-3 flex items-center gap-2">
                <ClipboardList className="h-5 w-5 text-cyan-300" />
                <h2 className="text-lg font-semibold text-white">待补技术</h2>
              </div>
              <div className="flex flex-wrap gap-2">
                {Array.from(new Set(techQueue.flatMap((item) => item.technologies))).slice(0, 12).map((tech) => (
                  <span key={tech} className="rounded-md border border-cyan-500/30 bg-cyan-950/40 px-2 py-1 text-xs text-cyan-100">
                    {tech}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="grid gap-4 lg:grid-cols-3">
          <div className="rounded-lg border border-slate-700 bg-slate-900/80 p-4 lg:col-span-2">
            <h2 className="mb-3 text-lg font-semibold text-white">长期积累</h2>
            <div className="grid gap-3 sm:grid-cols-2">
              {deepItems.map((item) => (
                <CompactItem key={item.item_id} item={item} />
              ))}
            </div>
          </div>
          <div className="rounded-lg border border-slate-700 bg-slate-900/80 p-4">
            <h2 className="mb-3 text-lg font-semibold text-white">导出状态</h2>
            <div className="space-y-3 text-sm text-slate-300">
              <p>下一次：{data?.daily_schedule?.local_time || '08:00'}</p>
              <p>最近手帐：{latestBrief?.title || '暂无'}</p>
              <p>导出次数：{latestBrief?.exports?.length || 0}</p>
              {action.message && <p className="text-emerald-300">{action.message}</p>}
            </div>
          </div>
        </section>
      </main>
    </>
  )
}

function CommandButton({
  label,
  icon,
  busy,
  disabled,
  onClick,
}: {
  label: string
  icon: React.ReactNode
  busy?: boolean
  disabled?: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      disabled={disabled || busy}
      onClick={onClick}
      className="flex h-11 min-w-0 items-center justify-center gap-2 rounded-lg border border-slate-600 bg-slate-800 px-3 text-sm font-medium text-white hover:border-emerald-400 hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
      title={label}
    >
      {busy ? <RefreshCw className="h-4 w-4 animate-spin" /> : icon}
      <span className="truncate">{label}</span>
    </button>
  )
}

function StudyItemRow({ item, onAction }: { item: StudyItem; onAction: (action: string) => void }) {
  return (
    <article className="rounded-lg border border-slate-700 bg-slate-950/50 p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span className="rounded-md bg-emerald-950 px-2 py-1 text-xs text-emerald-200">{Math.round(item.score)}</span>
            <span className="rounded-md bg-slate-800 px-2 py-1 text-xs text-slate-200">{item.reading_depth}</span>
            <span className="rounded-md bg-amber-950 px-2 py-1 text-xs text-amber-200">{statusLabels[item.status] || item.status}</span>
          </div>
          <h3 className="line-clamp-2 text-base font-semibold text-white">{item.title}</h3>
          <p className="mt-2 line-clamp-2 text-sm text-slate-300">{item.summary || item.why_it_matters}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {item.technologies.slice(0, 5).map((tech) => (
              <span key={tech} className="rounded-md bg-slate-800 px-2 py-1 text-xs text-slate-300">
                {tech}
              </span>
            ))}
          </div>
        </div>
        <div className="flex shrink-0 gap-2">
          <IconButton label="deep_dive" icon={<Search className="h-4 w-4" />} onClick={() => onAction('deep_dive')} />
          <IconButton label="generate_cards" icon={<Sparkles className="h-4 w-4" />} onClick={() => onAction('generate_cards')} />
          <IconButton label="mark_read" icon={<Check className="h-4 w-4" />} onClick={() => onAction('mark_read')} />
        </div>
      </div>
    </article>
  )
}

function CompactItem({ item }: { item: StudyItem }) {
  return (
    <article className="rounded-lg border border-slate-700 bg-slate-950/50 p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="truncate text-xs text-slate-400">{sourceLabels[item.source_kind] || item.source_kind}</span>
        <span className="text-xs text-emerald-300">{Math.round(item.score)}</span>
      </div>
      <h3 className="line-clamp-2 text-sm font-semibold text-white">{item.title}</h3>
      <p className="mt-2 line-clamp-2 text-xs text-slate-400">{item.suggested_action}</p>
    </article>
  )
}

function PersonalControlPanel({
  activeTab,
  personal,
  studyItems,
  onPlan,
  onCards,
  onExport,
}: {
  activeTab: PersonalTab
  personal?: PersonalState
  studyItems: StudyItem[]
  onPlan: () => void
  onCards: () => void
  onExport: () => void
}) {
  if (!personal) {
    return (
      <div className="rounded-lg border border-slate-700 bg-slate-900/80 p-4 text-sm text-slate-300">
        个人操作系统未启用或正在加载。
      </div>
    )
  }

  if (personal.status === 'disabled' || personal.status === 'missing_dependency') {
    return (
      <div className="rounded-lg border border-amber-500/40 bg-amber-950/30 p-4 text-sm text-amber-100">
        personal.life_companion 当前不可用：{personal.status}
      </div>
    )
  }

  const rows = personal.rows || []
  const activeRows =
    activeTab === 'for-you'
      ? rows
      : activeTab === 'entertainment'
        ? rows.filter((row) => row.row_id.includes('entertainment'))
        : activeTab === 'review'
          ? rows.filter((row) => row.row_id.includes('review'))
          : activeTab === 'exports'
            ? rows.filter((row) => row.row_id.includes('export'))
            : rows.slice(0, 2)

  return (
    <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
      <div className="rounded-lg border border-slate-700 bg-slate-900/80 p-4">
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-white">{tabTitle(activeTab)}</h2>
            <p className="mt-1 text-sm text-slate-400">
              {activeTab === 'today'
                ? personal.active_plan?.title || '生成今日学习娱乐计划'
                : `${activeRows.reduce((sum, row) => sum + row.items.length, 0)} 条推荐`}
            </p>
          </div>
          <div className="flex gap-2">
            <IconButton label="plan" icon={<CalendarDays className="h-4 w-4" />} onClick={onPlan} />
            <IconButton label="cards" icon={<Layers className="h-4 w-4" />} onClick={onCards} />
            <IconButton label="export" icon={<UploadCloud className="h-4 w-4" />} onClick={onExport} />
          </div>
        </div>

        {activeTab === 'today' && personal.active_plan ? (
          <div className="grid gap-3">
            {personal.active_plan.blocks.map((block) => (
              <div key={block.block_id} className="rounded-lg border border-slate-700 bg-slate-950/50 p-3">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm font-semibold text-white">{block.title}</span>
                  <span className="text-xs text-emerald-300">{block.minutes}m</span>
                </div>
                <p className="mt-1 text-xs text-slate-400">{block.kind} · {block.status}</p>
              </div>
            ))}
          </div>
        ) : activeTab === 'cards' || activeTab === 'review' ? (
          <div className="grid gap-3 sm:grid-cols-2">
            {personal.due_cards.slice(0, 8).map((card) => (
              <div key={card.card_id} className="rounded-lg border border-slate-700 bg-slate-950/50 p-3">
                <p className="line-clamp-2 text-sm font-semibold text-white">{card.front}</p>
                <p className="mt-2 line-clamp-2 text-xs text-slate-400">{card.back}</p>
              </div>
            ))}
            {!personal.due_cards.length && <p className="text-sm text-slate-400">暂无到期卡片</p>}
          </div>
        ) : activeTab === 'exports' ? (
          <div className="grid gap-3">
            {personal.exports.slice(0, 8).map((item) => (
              <div key={item.export_id} className="rounded-lg border border-slate-700 bg-slate-950/50 p-3">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm font-semibold text-white">{item.title}</span>
                  <span className="text-xs text-cyan-300">{item.status}</span>
                </div>
                <p className="mt-1 text-xs text-slate-400">
                  files {item.artifact_paths.length} · copied {item.copied_paths.length}
                </p>
              </div>
            ))}
          </div>
        ) : activeTab === 'deep' ? (
          <div className="grid gap-3">
            {studyItems.filter((item) => item.reading_depth === 'deep').slice(0, 6).map((item) => (
              <CompactItem key={item.item_id} item={item} />
            ))}
          </div>
        ) : (
          <div className="grid gap-3">
            {activeRows.map((row) => (
              <div key={row.row_id}>
                <p className="mb-2 text-sm font-semibold text-slate-200">{row.title}</p>
                <div className="grid gap-3 sm:grid-cols-2">
                  {row.items.slice(0, 4).map((item) => (
                    <article key={item.recommendation_id} className="rounded-lg border border-slate-700 bg-slate-950/50 p-3">
                      <div className="mb-2 flex items-center justify-between gap-2">
                        <span className="text-xs text-slate-400">{item.kind}</span>
                        <span className="text-xs text-emerald-300">{Math.round(item.score)}</span>
                      </div>
                      <h3 className="line-clamp-2 text-sm font-semibold text-white">{item.title}</h3>
                      <p className="mt-2 line-clamp-2 text-xs text-slate-400">{item.reason || item.summary}</p>
                    </article>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="rounded-lg border border-slate-700 bg-slate-900/80 p-4">
        <h2 className="mb-3 text-lg font-semibold text-white">系统状态</h2>
        <div className="space-y-2 text-sm text-slate-300">
          <p>status: {personal.status}</p>
          <p>cards: {personal.due_cards.length}</p>
          <p>exports: {personal.exports.length}</p>
          <p>content: {String(personal.metadata?.content_count ?? 0)}</p>
        </div>
      </div>
    </div>
  )
}

function tabTitle(tab: PersonalTab): string {
  return personalTabs.find((item) => item.id === tab)?.label || 'Personal'
}

function IconButton({ label, icon, onClick }: { label: string; icon: React.ReactNode; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={label}
      className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-600 bg-slate-800 text-slate-100 hover:border-emerald-400 hover:text-white"
    >
      {icon}
    </button>
  )
}
