import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
    Zap, DollarSign, Filter, ArrowUpDown, RefreshCw,
    Server, HardDrive, Database, Network, Shield, TrendingDown,
    Download, FileText, FileJson
} from 'lucide-react'
import apiClient from '../services/apiClient'

// ── Helpers ──────────────────────────────────────────────────────────────────
const fmtNum = (n) => (n == null ? '—' : Number(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }))

const CATEGORY_COLORS = {
    Compute: '#3b82f6',
    Storage: '#8b5cf6',
    Database: '#10b981',
    Network: '#0ea5e9',
    Governance: '#6b7280',
}

const CATEGORY_ICONS = {
    Compute: Server,
    Storage: HardDrive,
    Database: Database,
    Network: Network,
    Governance: Shield,
}

const CONFIDENCE_COLOR = {
    HIGH: '#10b981',
    MEDIUM: '#f59e0b',
    LOW: '#6b7280',
}

const SEV_COLOR = {
    CRITICAL: '#ef4444',
    HIGH: '#f97316',
    MEDIUM: '#f59e0b',
    LOW: '#6b7280',
}

function badge(text, color) {
    return (
        <span style={{
            background: `${color}22`, color, border: `1px solid ${color}44`,
            borderRadius: 4, padding: '2px 7px', fontSize: 11, fontWeight: 700,
            whiteSpace: 'nowrap', display: 'inline-block',
        }}>{text}</span>
    )
}

// ── Total Savings Hero Card ───────────────────────────────────────────────────
function SavingsHero({ recs }) {
    const total = recs.reduce((s, r) => s + (r.estimated_monthly_savings || 0), 0)
    const totalAnnual = total * 12
    const withSavings = recs.filter(r => r.estimated_monthly_savings > 0)
    const categories = [...new Set(recs.map(r => r.category))]

    return (
        <div style={{
            background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)',
            border: '1px solid #334155', borderRadius: 12, padding: '24px 28px',
            marginBottom: 24, display: 'flex', flexWrap: 'wrap', gap: 32, alignItems: 'center',
        }}>
            <div>
                <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 4, textTransform: 'uppercase', letterSpacing: 1 }}>
                    Estimated Monthly Savings
                </div>
                <div style={{ fontSize: 36, fontWeight: 900, color: '#10b981' }}>
                    ${fmtNum(total)}
                    <span style={{ fontSize: 14, color: '#94a3b8', fontWeight: 500, marginLeft: 8 }}>/ mo</span>
                </div>
                <div style={{ fontSize: 13, color: '#64748b', marginTop: 4 }}>
                    ~${fmtNum(totalAnnual)} / year if all actioned
                </div>
            </div>
            <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
                <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 24, fontWeight: 700, color: '#f8fafc' }}>{recs.length}</div>
                    <div style={{ fontSize: 11, color: '#64748b' }}>Total recommendations</div>
                </div>
                <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 24, fontWeight: 700, color: '#f97316' }}>{withSavings.length}</div>
                    <div style={{ fontSize: 11, color: '#64748b' }}>With savings estimate</div>
                </div>
                <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 24, fontWeight: 700, color: '#3b82f6' }}>{categories.length}</div>
                    <div style={{ fontSize: 11, color: '#64748b' }}>Categories affected</div>
                </div>
            </div>
        </div>
    )
}

// ── Category Filter Tabs ──────────────────────────────────────────────────────
const CATEGORIES = ['All', 'Compute', 'Storage', 'Database', 'Network', 'Governance']

function CategoryTabs({ active, onChange, recs }) {
    const counts = Object.fromEntries(CATEGORIES.map(c => [
        c, c === 'All' ? recs.length : recs.filter(r => r.category === c).length
    ]))
    return (
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 16 }}>
            {CATEGORIES.map(cat => {
                const color = cat === 'All' ? '#3b82f6' : (CATEGORY_COLORS[cat] || '#6b7280')
                const isActive = active === cat
                const Icon = CATEGORY_ICONS[cat]
                return (
                    <button key={cat} onClick={() => onChange(cat)} style={{
                        display: 'flex', alignItems: 'center', gap: 5,
                        padding: '6px 14px', borderRadius: 6, fontSize: 12, fontWeight: 600, cursor: 'pointer',
                        border: `1px solid ${isActive ? color : 'var(--border)'}`,
                        background: isActive ? `${color}18` : 'transparent',
                        color: isActive ? color : 'var(--text-secondary)',
                        transition: 'all 0.15s',
                    }}>
                        {Icon && <Icon size={13} />}
                        {cat}
                        <span style={{ opacity: 0.7 }}>({counts[cat] || 0})</span>
                    </button>
                )
            })}
        </div>
    )
}

// ── Recommendations Table ─────────────────────────────────────────────────────
function RecTable({ recs, sortKey, sortDir, onSort }) {
    const cols = [
        { key: 'category', label: 'Category' },
        { key: 'title', label: 'Recommendation' },
        { key: 'resource_id', label: 'Resource' },
        { key: 'region', label: 'Region' },
        { key: 'severity', label: 'Severity' },
        { key: 'confidence', label: 'Confidence' },
        { key: 'estimated_monthly_savings', label: 'Est. Savings / Mo' },
    ]

    if (!recs.length) return (
        <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-secondary)', fontSize: 14 }}>
            <Zap size={32} style={{ marginBottom: 12, opacity: 0.3 }} />
            <div>No recommendations for this category.</div>
        </div>
    )

    return (
        <div className="table-wrapper">
            <table>
                <thead>
                    <tr>
                        {cols.map(c => (
                            <th key={c.key} onClick={() => onSort(c.key)} style={{ cursor: 'pointer', userSelect: 'none' }}>
                                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                                    {c.label}
                                    <ArrowUpDown size={11} style={{ opacity: sortKey === c.key ? 1 : 0.3 }} />
                                </span>
                            </th>
                        ))}
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {recs.map(r => {
                        const catColor = CATEGORY_COLORS[r.category] || '#6b7280'
                        const CatIcon = CATEGORY_ICONS[r.category]
                        return (
                            <tr key={r.id}>
                                {/* Category */}
                                <td>
                                    <span style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 600, color: catColor }}>
                                        {CatIcon && <CatIcon size={13} />}
                                        {r.category}
                                    </span>
                                </td>
                                {/* Title + description */}
                                <td style={{ maxWidth: 280 }}>
                                    <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 2 }}>{r.title}</div>
                                    <div style={{ fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                                        {r.description}
                                    </div>
                                    <code style={{ fontSize: 10, background: 'var(--bg-tertiary)', padding: '1px 5px', borderRadius: 3, marginTop: 3, display: 'inline-block' }}>
                                        {r.rule_id}
                                    </code>
                                </td>
                                {/* Resource */}
                                <td>
                                    <code style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                                        {r.resource_id?.length > 22 ? r.resource_id.slice(0, 10) + '…' + r.resource_id.slice(-10) : r.resource_id}
                                    </code>
                                </td>
                                {/* Region */}
                                <td style={{ fontSize: 12 }}>{r.region}</td>
                                {/* Severity */}
                                <td>{badge(r.severity, SEV_COLOR[r.severity?.toUpperCase()] || '#6b7280')}</td>
                                {/* Confidence */}
                                <td>{badge(r.confidence, CONFIDENCE_COLOR[r.confidence?.toUpperCase()] || '#6b7280')}</td>
                                {/* Savings */}
                                <td>
                                    {r.estimated_monthly_savings > 0
                                        ? <span style={{ fontWeight: 700, color: '#10b981', fontSize: 13 }}>
                                            ${fmtNum(r.estimated_monthly_savings)}
                                        </span>
                                        : <span style={{ color: 'var(--text-secondary)', fontSize: 12 }}>—</span>
                                    }
                                </td>
                                {/* Action */}
                                <td style={{ maxWidth: 220, fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                                    {r.action}
                                </td>
                            </tr>
                        )
                    })}
                </tbody>
            </table>
        </div>
    )
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function Recommendations() {
    const navigate = useNavigate()
    const [recs, setRecs] = useState([])
    const [scanId, setScanId] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [category, setCategory] = useState('All')
    const [sortKey, setSortKey] = useState('estimated_monthly_savings')
    const [sortDir, setSortDir] = useState('desc')

    const loadLatestRecs = useCallback(async () => {
        setLoading(true)
        setError(null)
        try {
            // Get the latest completed scan
            const scansResp = await apiClient.get('/scans')
            const scans = scansResp.data?.scans || []
            const completed = scans.filter(s => s.status === 'completed')
            if (!completed.length) {
                setError('No completed scans found. Trigger a scan from the Resources page first.')
                setLoading(false)
                return
            }
            const latestId = completed[0].id
            setScanId(latestId)
            const resp = await apiClient.get(`/scans/${latestId}/recommendations`)
            setRecs(resp.data?.recommendations || [])
        } catch (e) {
            setError('Failed to load recommendations. Check that the backend is running.')
            console.error(e)
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => { loadLatestRecs() }, [loadLatestRecs])

    // Sort
    const handleSort = (key) => {
        if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
        else { setSortKey(key); setSortDir('desc') }
    }

    const filtered = recs
        .filter(r => category === 'All' || r.category === category)
        .sort((a, b) => {
            const av = a[sortKey] ?? ''
            const bv = b[sortKey] ?? ''
            const cmp = typeof av === 'number' ? av - bv : String(av).localeCompare(String(bv))
            return sortDir === 'asc' ? cmp : -cmp
        })

    // Export helpers — open backend URLs directly (browser handles download)
    const baseUrl = (apiClient.defaults?.baseURL || 'http://localhost:8000/api/v1')
    const handleExport = (path) => {
        if (!scanId) return
        window.open(`${baseUrl}/scans/${scanId}${path}`, '_blank')
    }

    const btnStyle = {
        display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px',
        borderRadius: 6, border: '1px solid var(--border)', background: 'transparent',
        color: 'var(--text-secondary)', fontSize: 12, cursor: 'pointer',
    }

    return (
        <div style={{ padding: '24px 28px', maxWidth: 1400, margin: '0 auto' }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24, flexWrap: 'wrap', gap: 12 }}>
                <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <div style={{ background: '#3b82f618', borderRadius: 8, padding: 8 }}>
                            <Zap size={20} color="#3b82f6" />
                        </div>
                        <div>
                            <h1 style={{ fontSize: 20, fontWeight: 800, margin: 0 }}>Recommendations</h1>
                            <p style={{ fontSize: 13, color: 'var(--text-secondary)', margin: 0 }}>
                                Ranked savings actions from latest audit
                                {scanId && <code style={{ marginLeft: 6, fontSize: 11, background: 'var(--bg-tertiary)', padding: '1px 6px', borderRadius: 3 }}>{scanId.slice(0, 8)}…</code>}
                            </p>
                        </div>
                    </div>
                </div>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    {scanId && (
                        <>
                            <button onClick={() => handleExport('/export/recommendations.csv')} style={btnStyle} title="Download CSV">
                                <Download size={14} /> Rec. CSV
                            </button>
                            <button onClick={() => handleExport('/export/violations.csv')} style={btnStyle} title="Download violations CSV">
                                <Download size={14} /> Viol. CSV
                            </button>
                            <button onClick={() => handleExport('/export/report.json')} style={btnStyle} title="Download full JSON">
                                <FileJson size={14} /> JSON
                            </button>
                            <button onClick={() => handleExport('/export/report.html')} style={{ ...btnStyle, color: '#3b82f6', borderColor: '#3b82f640' }} title="Open printable HTML report (Ctrl+P to save as PDF)">
                                <FileText size={14} /> PDF Report
                            </button>
                        </>
                    )}
                    <button onClick={() => navigate('/')} style={btnStyle}>
                        <TrendingDown size={14} /> Dashboard
                    </button>
                    <button onClick={loadLatestRecs} style={btnStyle}>
                        <RefreshCw size={14} /> Refresh
                    </button>
                </div>
            </div>

            {loading && (
                <div style={{ textAlign: 'center', padding: '80px 0', color: 'var(--text-secondary)' }}>
                    <RefreshCw size={28} style={{ animation: 'spin 1s linear infinite', marginBottom: 12 }} />
                    <div>Loading recommendations…</div>
                </div>
            )}

            {error && !loading && (
                <div style={{
                    background: '#ef444418', border: '1px solid #ef444440', borderRadius: 8,
                    padding: '16px 20px', color: '#ef4444', fontSize: 13,
                }}>
                    {error}
                </div>
            )}

            {!loading && !error && recs.length > 0 && (
                <>
                    <SavingsHero recs={recs} />
                    <div className="card">
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, flexWrap: 'wrap', gap: 8 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                <Filter size={14} color="var(--text-secondary)" />
                                <span style={{ fontSize: 13, fontWeight: 600 }}>Filter by Category</span>
                            </div>
                            <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                                Showing {filtered.length} of {recs.length} · sorted by {sortKey.replace(/_/g, ' ')} ({sortDir})
                            </div>
                        </div>
                        <CategoryTabs active={category} onChange={setCategory} recs={recs} />
                        <RecTable recs={filtered} sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
                    </div>
                </>
            )}

            {!loading && !error && recs.length === 0 && (
                <div style={{ textAlign: 'center', padding: '80px 0', color: 'var(--text-secondary)' }}>
                    <Zap size={36} style={{ marginBottom: 12, opacity: 0.3 }} />
                    <div style={{ fontSize: 15, fontWeight: 600 }}>No recommendations yet</div>
                    <div style={{ fontSize: 13, marginTop: 4 }}>Trigger a scan to generate recommendations.</div>
                </div>
            )}
        </div>
    )
}
