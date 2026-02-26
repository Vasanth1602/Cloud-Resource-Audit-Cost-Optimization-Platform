import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
    Server, HardDrive, Database, Globe2, RefreshCw, WifiOff,
    Search, AlertTriangle, DollarSign, Zap, Network, Camera,
    LoaderCircle, GitBranch
} from 'lucide-react'
import { getSettings } from '../services/settingsService'
import apiClient from '../services/apiClient'

// ── helpers ─────────────────────────────────────────────────────────────────
const fmtDate = iso => iso ? new Date(iso).toLocaleString() : '—'
const fmtNum = n => n != null ? Number(n).toLocaleString() : '—'

const badge = (text, color) => (
    <span style={{
        display: 'inline-block', padding: '2px 10px', borderRadius: 12,
        fontSize: 11, fontWeight: 600, background: `${color}22`, color,
        whiteSpace: 'nowrap',
    }}>{text}</span>
)

const stateColor = s => {
    const m = { running: '#10b981', stopped: '#ef4444', available: '#10b981', 'in-use': '#3b82f6', active: '#10b981', unassociated: '#ef4444', associated: '#10b981', completed: '#6b7280' }
    return m[s?.toLowerCase()] || '#6b7280'
}

const SEV_COLOR = { CRITICAL: '#ef4444', HIGH: '#f97316', MEDIUM: '#f59e0b', LOW: '#3b82f6' }
const SEV_EMOJI = { CRITICAL: '🔴', HIGH: '🟠', MEDIUM: '🟡', LOW: '🔵' }

function riskBadge(score) {
    if (!score && score !== 0) return null
    const color = score >= 76 ? '#ef4444' : score >= 51 ? '#f97316' : score >= 26 ? '#f59e0b' : score > 0 ? '#3b82f6' : '#10b981'
    const label = score >= 76 ? 'CRITICAL' : score >= 51 ? 'HIGH' : score >= 26 ? 'MEDIUM' : score > 0 ? 'LOW' : 'CLEAN'
    return badge(label, color)
}

// ── Empty state ──────────────────────────────────────────────────────────────
function Empty({ msg }) {
    return (
        <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--text-secondary)' }}>
            <Search size={28} style={{ marginBottom: 8, opacity: 0.5 }} />
            <p>{msg}</p>
        </div>
    )
}

// ── Resource tables ──────────────────────────────────────────────────────────
function EC2Table({ items }) {
    if (!items.length) return <Empty msg="No EC2 instances found." />
    return (
        <div className="table-wrapper">
            <table>
                <thead><tr>
                    <th>Instance ID</th><th>Name</th><th>State</th><th>Type</th>
                    <th>Region</th><th>Public IP</th><th>Avg CPU</th>
                    <th>In ASG</th><th>Spot Eligible</th><th>RI Candidate</th>
                    <th>Net In</th><th>Net Out</th><th>Risk</th><th>Launched</th>
                </tr></thead>
                <tbody>{items.map(r => (
                    <tr key={r.resource_id}>
                        <td style={{ fontFamily: 'monospace', fontSize: 12 }}>{r.resource_id}</td>
                        <td>{r.name || '—'}</td>
                        <td>{badge(r.state, stateColor(r.state))}</td>
                        <td>{r.raw_data?.instance_type || '—'}</td>
                        <td>{r.region}</td>
                        <td>{r.raw_data?.public_ip || '—'}</td>
                        <td>{r.raw_data?.avg_cpu_percent != null ? `${r.raw_data.avg_cpu_percent.toFixed(1)}%` : '—'}</td>
                        <td>
                            {r.raw_data?.in_asg
                                ? badge('Yes ✓', '#10b981')
                                : badge('No', '#f59e0b')}
                        </td>
                        <td>
                            {r.raw_data?.spot_eligible
                                ? badge('Yes', '#3b82f6')
                                : <span style={{ color: 'var(--text-secondary)', fontSize: 12 }}>—</span>}
                        </td>
                        <td>
                            {r.raw_data?.ri_candidate
                                ? badge('Candidate', '#8b5cf6')
                                : <span style={{ color: 'var(--text-secondary)', fontSize: 12 }}>—</span>}
                        </td>
                        <td style={{ fontSize: 12 }}>
                            {r.raw_data?.network_in_gb != null ? `${r.raw_data.network_in_gb.toFixed(2)} GB` : '—'}
                        </td>
                        <td style={{ fontSize: 12 }}>
                            {r.raw_data?.network_out_gb != null ? `${r.raw_data.network_out_gb.toFixed(2)} GB` : '—'}
                        </td>
                        <td>{riskBadge(r.risk_score)}</td>
                        <td style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{fmtDate(r.raw_data?.launch_time)}</td>
                    </tr>
                ))}</tbody>
            </table>
        </div>
    )
}

function EBSTable({ items }) {
    if (!items.length) return <Empty msg="No EBS volumes found." />
    return (
        <div className="table-wrapper">
            <table>
                <thead><tr>
                    <th>Volume ID</th><th>State</th><th>Size</th><th>Type</th>
                    <th>Encrypted</th><th>Attached To</th><th>Risk</th><th>Region</th>
                </tr></thead>
                <tbody>{items.map(r => (
                    <tr key={r.resource_id}>
                        <td style={{ fontFamily: 'monospace', fontSize: 12 }}>{r.resource_id}</td>
                        <td>{badge(r.state, stateColor(r.state))}</td>
                        <td>{r.raw_data?.size_gb ? `${r.raw_data.size_gb} GB` : '—'}</td>
                        <td>
                            {r.raw_data?.volume_type === 'gp2'
                                ? <>{r.raw_data.volume_type} {badge('→ gp3', '#f59e0b')}</>
                                : (r.raw_data?.volume_type || '—')}
                        </td>
                        <td>{r.raw_data?.encrypted ? badge('Yes', '#10b981') : badge('No', '#ef4444')}</td>
                        <td style={{ fontFamily: 'monospace', fontSize: 12 }}>{r.raw_data?.attached_instance || '—'}</td>
                        <td>{riskBadge(r.risk_score)}</td>
                        <td>{r.region}</td>
                    </tr>
                ))}</tbody>
            </table>
        </div>
    )
}

function S3Table({ items }) {
    if (!items.length) return <Empty msg="No S3 buckets found." />
    return (
        <div className="table-wrapper">
            <table>
                <thead><tr>
                    <th>Bucket Name</th><th>Region</th><th>Size</th><th>Objects</th>
                    <th>Lifecycle Policy</th><th>Last Accessed</th>
                    <th>Versioning</th><th>Encryption</th><th>Public Access Blocked</th><th>Risk</th>
                </tr></thead>
                <tbody>{items.map(r => (
                    <tr key={r.resource_id}>
                        <td>{r.resource_id}</td>
                        <td>{r.region}</td>
                        <td>{r.raw_data?.size_gb != null ? `${r.raw_data.size_gb} GB` : '—'}</td>
                        <td>{r.raw_data?.object_count != null ? fmtNum(r.raw_data.object_count) : '—'}</td>
                        <td>{r.raw_data?.has_lifecycle_policy
                            ? badge('Yes ✓', '#10b981')
                            : badge('None ✗', '#ef4444')}</td>
                        <td>
                            {r.raw_data?.last_accessed_days != null
                                ? r.raw_data.last_accessed_days > 90
                                    ? badge(`${r.raw_data.last_accessed_days}d ago ⚠`, '#ef4444')
                                    : `${r.raw_data.last_accessed_days}d ago`
                                : '—'}
                        </td>
                        <td>{r.raw_data?.versioning_enabled ? badge('On', '#10b981') : badge('Off', '#f59e0b')}</td>
                        <td>{r.raw_data?.encryption_enabled ? badge('Yes', '#10b981') : badge('No', '#ef4444')}</td>
                        <td>{r.raw_data?.public_access_blocked ? badge('Yes ✓', '#10b981') : badge('No ✗', '#ef4444')}</td>
                        <td>{riskBadge(r.risk_score)}</td>
                    </tr>
                ))}</tbody>
            </table>
        </div>
    )
}

function RDSTable({ items }) {
    if (!items.length) return <Empty msg="No RDS instances found." />
    return (
        <div className="table-wrapper">
            <table>
                <thead><tr>
                    <th>DB Identifier</th><th>Engine</th><th>Class</th><th>Status</th>
                    <th>Multi-AZ</th><th>Encrypted</th><th>Publicly Accessible</th>
                    <th>CPU %</th><th>Avg Connections</th><th>Storage Autoscale</th>
                    <th>Risk</th><th>Region</th>
                </tr></thead>
                <tbody>{items.map(r => (
                    <tr key={r.resource_id}>
                        <td style={{ fontFamily: 'monospace', fontSize: 12 }}>{r.resource_id}</td>
                        <td>{r.raw_data?.engine || '—'}</td>
                        <td>{r.raw_data?.instance_class || '—'}</td>
                        <td>{badge(r.state || '—', stateColor(r.state))}</td>
                        <td>{r.raw_data?.multi_az ? badge('Yes', '#10b981') : badge('No', '#f59e0b')}</td>
                        <td>{r.raw_data?.storage_encrypted
                            ? badge('Yes', '#10b981')
                            : badge('No', '#ef4444')}
                        </td>
                        <td>{r.raw_data?.publicly_accessible
                            ? badge('Yes ⚠', '#ef4444')
                            : badge('No ✓', '#10b981')}
                        </td>
                        <td>
                            {r.raw_data?.avg_cpu_percent != null
                                ? r.raw_data.avg_cpu_percent < 20
                                    ? badge(`${r.raw_data.avg_cpu_percent.toFixed(1)}% ⚠`, '#f97316')
                                    : `${r.raw_data.avg_cpu_percent.toFixed(1)}%`
                                : '—'}
                        </td>
                        <td>
                            {r.raw_data?.avg_connections != null
                                ? r.raw_data.avg_connections < 5
                                    ? badge(`${r.raw_data.avg_connections.toFixed(1)} ⚠`, '#ef4444')
                                    : r.raw_data.avg_connections.toFixed(1)
                                : '—'}
                        </td>
                        <td>
                            {r.raw_data?.storage_autoscaling_enabled
                                ? badge('On ✓', '#10b981')
                                : badge('Off', '#f59e0b')}
                        </td>
                        <td>{riskBadge(r.risk_score)}</td>
                        <td>{r.region}</td>
                    </tr>
                ))}</tbody>
            </table>
        </div>
    )
}

function EIPTable({ items }) {
    if (!items.length) return <Empty msg="No Elastic IPs found." />
    return (
        <div className="table-wrapper">
            <table>
                <thead><tr>
                    <th>Public IP</th><th>Allocation ID</th><th>Status</th>
                    <th>Associated Instance</th><th>Estimated Waste</th><th>Risk</th><th>Region</th>
                </tr></thead>
                <tbody>{items.map(r => (
                    <tr key={r.resource_id}>
                        <td style={{ fontFamily: 'monospace' }}>{r.resource_id}</td>
                        <td style={{ fontFamily: 'monospace', fontSize: 12 }}>{r.raw_data?.allocation_id || '—'}</td>
                        <td>{badge(r.state, stateColor(r.state))}</td>
                        <td style={{ fontFamily: 'monospace', fontSize: 12 }}>{r.raw_data?.instance_id || '—'}</td>
                        <td>
                            {!r.raw_data?.associated
                                ? <span style={{ color: '#ef4444', fontWeight: 600 }}>~$3.60/mo</span>
                                : <span style={{ color: 'var(--text-secondary)' }}>$0</span>}
                        </td>
                        <td>{riskBadge(r.risk_score)}</td>
                        <td>{r.region}</td>
                    </tr>
                ))}</tbody>
            </table>
        </div>
    )
}

function SnapshotTable({ items }) {
    if (!items.length) return <Empty msg="No EBS snapshots found." />
    return (
        <div className="table-wrapper">
            <table>
                <thead><tr>
                    <th>Snapshot ID</th><th>Name / Description</th><th>Size</th>
                    <th>Age</th><th>AMI Linked</th><th>Estimated Waste</th><th>Risk</th><th>Region</th>
                </tr></thead>
                <tbody>{items.map(r => (
                    <tr key={r.resource_id}>
                        <td style={{ fontFamily: 'monospace', fontSize: 12 }}>{r.resource_id}</td>
                        <td>{r.name || '—'}</td>
                        <td>{r.raw_data?.size_gb ? `${r.raw_data.size_gb} GB` : '—'}</td>
                        <td>
                            {r.raw_data?.age_days != null
                                ? r.raw_data.age_days > 30
                                    ? badge(`${r.raw_data.age_days}d ⚠`, '#f59e0b')
                                    : `${r.raw_data.age_days}d`
                                : '—'}
                        </td>
                        <td>{r.raw_data?.ami_id ? badge('Yes ✓', '#10b981') : badge('Orphaned', '#ef4444')}</td>
                        <td>
                            {!r.raw_data?.ami_id && r.raw_data?.size_gb
                                ? <span style={{ color: '#f59e0b', fontWeight: 600 }}>
                                    ~${(r.raw_data.size_gb * 0.05).toFixed(2)}/mo
                                </span>
                                : <span style={{ color: 'var(--text-secondary)' }}>—</span>}
                        </td>
                        <td>{riskBadge(r.risk_score)}</td>
                        <td>{r.region}</td>
                    </tr>
                ))}</tbody>
            </table>
        </div>
    )
}

function LBTable({ items }) {
    if (!items.length) return <Empty msg="No Load Balancers found." />
    return (
        <div className="table-wrapper">
            <table>
                <thead><tr>
                    <th>Name</th><th>Type</th><th>State</th><th>Scheme</th>
                    <th>Listeners</th><th>Avg Req/Day</th><th>Risk</th><th>Region</th>
                </tr></thead>
                <tbody>{items.map(r => (
                    <tr key={r.resource_id}>
                        <td>{r.name || '—'}</td>
                        <td>
                            {r.raw_data?.lb_type === 'ALB'
                                ? badge('ALB', '#3b82f6')
                                : badge('NLB', '#8b5cf6')}
                        </td>
                        <td>{badge(r.state, stateColor(r.state))}</td>
                        <td style={{ fontSize: 12 }}>{r.raw_data?.scheme || '—'}</td>
                        <td>
                            {r.raw_data?.listener_count === 0
                                ? badge('None ✗', '#ef4444')
                                : r.raw_data?.listener_count ?? '—'}
                        </td>
                        <td>
                            {r.raw_data?.avg_request_count_per_day != null
                                ? r.raw_data.avg_request_count_per_day < 10
                                    ? badge(`${r.raw_data.avg_request_count_per_day.toFixed(1)} ⚠`, '#f97316')
                                    : r.raw_data.avg_request_count_per_day.toFixed(1)
                                : '—'}
                        </td>
                        <td>{riskBadge(r.risk_score)}</td>
                        <td>{r.region}</td>
                    </tr>
                ))}</tbody>
            </table>
        </div>
    )
}

function NATTable({ items }) {
    if (!items.length) return <Empty msg="No NAT Gateways found." />
    return (
        <div className="table-wrapper">
            <table>
                <thead><tr>
                    <th>NAT Gateway ID</th><th>Name</th><th>State</th>
                    <th>VPC</th><th>Type</th><th>Data Transfer (7d)</th><th>Risk</th><th>Region</th>
                </tr></thead>
                <tbody>{items.map(r => (
                    <tr key={r.resource_id}>
                        <td style={{ fontFamily: 'monospace', fontSize: 12 }}>{r.resource_id}</td>
                        <td>{r.name || '—'}</td>
                        <td>{badge(r.state, stateColor(r.state))}</td>
                        <td style={{ fontFamily: 'monospace', fontSize: 12 }}>{r.raw_data?.vpc_id || '—'}</td>
                        <td>{r.raw_data?.connectivity_type === 'private'
                            ? badge('Private', '#6b7280')
                            : badge('Public', '#3b82f6')}
                        </td>
                        <td>
                            {r.raw_data?.data_transfer_gb != null
                                ? r.raw_data.data_transfer_gb < 1
                                    ? badge(`${r.raw_data.data_transfer_gb.toFixed(3)} GB ⚠`, '#ef4444')
                                    : `${r.raw_data.data_transfer_gb.toFixed(2)} GB`
                                : '—'}
                        </td>
                        <td>{riskBadge(r.risk_score)}</td>
                        <td>{r.region}</td>
                    </tr>
                ))}</tbody>
            </table>
        </div>
    )
}

// ── Violations Panel ─────────────────────────────────────────────────────────
function ViolationsPanel({ violations, sevSummary }) {
    const [filter, setFilter] = useState('ALL')

    const filtered = filter === 'ALL' ? violations : violations.filter(v => v.severity?.toUpperCase() === filter)

    return (
        <div>
            {/* Severity summary row */}
            <div style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
                {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(s => {
                    const count = s === 'ALL' ? violations.length : (sevSummary[s] || 0)
                    const color = s === 'ALL' ? '#6b7280' : SEV_COLOR[s]
                    const active = filter === s
                    return (
                        <button key={s} onClick={() => setFilter(s)} style={{
                            display: 'flex', alignItems: 'center', gap: 6,
                            padding: '6px 14px', borderRadius: 8, border: `1px solid ${active ? color : 'var(--border)'}`,
                            background: active ? `${color}18` : 'transparent',
                            color: active ? color : 'var(--text-secondary)',
                            cursor: 'pointer', fontSize: 12, fontWeight: 600,
                        }}>
                            {s !== 'ALL' && SEV_EMOJI[s]} {s} <span style={{ opacity: 0.7 }}>({count})</span>
                        </button>
                    )
                })}
            </div>

            {filtered.length === 0
                ? <Empty msg="No violations found 🎉" />
                : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                        {filtered.map((v, i) => {
                            const color = SEV_COLOR[v.severity?.toUpperCase()] || '#6b7280'
                            return (
                                <div key={v.id || i} style={{
                                    border: `1px solid ${color}40`, borderLeft: `3px solid ${color}`,
                                    borderRadius: 8, padding: '12px 16px', background: `${color}08`,
                                }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8, marginBottom: 6 }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                            {badge(v.severity, color)}
                                            <code style={{ fontSize: 12, background: 'var(--bg-tertiary)', padding: '2px 6px', borderRadius: 4 }}>{v.rule_id}</code>
                                            <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{v.resource_type} · {v.region}</span>
                                        </div>
                                        <code style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{v.resource_id}</code>
                                    </div>
                                    <div style={{ fontSize: 13, marginBottom: 4 }}>{v.message}</div>
                                    {v.remediation && (
                                        <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                                            💡 {v.remediation}
                                        </div>
                                    )}
                                </div>
                            )
                        })}
                    </div>
                )
            }
        </div>
    )
}

// ── Daily Trend Sparkline (SVG) ───────────────────────────────────────────────
function DailySparkline({ trend }) {
    if (!trend?.length) return null
    const W = 560, H = 100, PAD = 24
    const amounts = trend.map(d => d.amount)
    const minA = Math.min(...amounts)
    const maxA = Math.max(...amounts)
    const range = maxA - minA || 1

    const px = (i) => PAD + (i / (trend.length - 1)) * (W - PAD * 2)
    const py = (a) => H - PAD - ((a - minA) / range) * (H - PAD * 2)

    const points = trend.map((d, i) => `${px(i)},${py(d.amount)}`).join(' ')
    const areaPoints = [
        `${PAD},${H - PAD}`,
        ...trend.map((d, i) => `${px(i)},${py(d.amount)}`),
        `${W - PAD},${H - PAD}`,
    ].join(' ')

    return (
        <div style={{ marginBottom: 24 }}>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', fontWeight: 600, marginBottom: 10 }}>
                DAILY SPEND — LAST 14 DAYS
            </div>
            <div style={{ overflowX: 'auto' }}>
                <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', maxWidth: W, height: H, display: 'block' }}>
                    <defs>
                        <linearGradient id="sparkGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.3" />
                            <stop offset="100%" stopColor="#3b82f6" stopOpacity="0.02" />
                        </linearGradient>
                    </defs>
                    {/* Area fill */}
                    <polygon points={areaPoints} fill="url(#sparkGrad)" />
                    {/* Line */}
                    <polyline points={points} fill="none" stroke="#3b82f6" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
                    {/* Data points */}
                    {trend.map((d, i) => (
                        <g key={i}>
                            <circle cx={px(i)} cy={py(d.amount)} r={3} fill="#3b82f6" />
                            <title>{d.date}: ${d.amount.toLocaleString()}</title>
                        </g>
                    ))}
                    {/* Min / Max labels */}
                    <text x={PAD} y={H - 6} fontSize={9} fill="var(--text-secondary)" textAnchor="middle">
                        {trend[0]?.date?.slice(5)}
                    </text>
                    <text x={W - PAD} y={H - 6} fontSize={9} fill="var(--text-secondary)" textAnchor="middle">
                        {trend[trend.length - 1]?.date?.slice(5)}
                    </text>
                    <text x={W - PAD + 2} y={py(maxA) + 4} fontSize={9} fill="#3b82f6" textAnchor="start">
                        ${maxA.toLocaleString()}
                    </text>
                </svg>
            </div>
        </div>
    )
}

// ── Cost Summary Card ─────────────────────────────────────────────────────────
function CostSummaryCard({ costData }) {
    if (!costData?.summary) return null
    const {
        total_monthly_cost, estimated_monthly_waste, waste_percentage,
        top_services, period, daily_trend, waste_by_service, cost_by_tag,
    } = costData.summary

    return (
        <div className="card" style={{ marginBottom: 24 }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20, flexWrap: 'wrap', gap: 8 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <DollarSign size={18} color="#10b981" />
                    <span style={{ fontWeight: 700, fontSize: 15 }}>Cost Intelligence</span>
                    {period && <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>({period} MTD)</span>}
                </div>
            </div>

            {/* Summary figures */}
            <div style={{ display: 'flex', gap: 32, flexWrap: 'wrap', marginBottom: 24 }}>
                <div>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 2 }}>Total Monthly Cost</div>
                    <div style={{ fontSize: 28, fontWeight: 800, color: '#10b981' }}>${fmtNum(total_monthly_cost)}</div>
                </div>
                <div>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 2 }}>Estimated Waste</div>
                    <div style={{ fontSize: 28, fontWeight: 800, color: '#ef4444' }}>
                        ${fmtNum(estimated_monthly_waste)}
                        <span style={{ fontSize: 13, fontWeight: 500, color: '#f97316', marginLeft: 6 }}>
                            ({waste_percentage}%)
                        </span>
                    </div>
                </div>
            </div>

            {/* ── Daily Trend Sparkline ── */}
            {daily_trend?.length > 0 && <DailySparkline trend={daily_trend} />}

            {/* ── Two-column breakdown ── */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 24 }}>

                {/* Top services spend */}
                {top_services?.length > 0 && (
                    <div>
                        <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 10, fontWeight: 600 }}>
                            TOP SERVICES BY SPEND
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                            {top_services.map((s, i) => {
                                const pct = total_monthly_cost > 0 ? (s.amount / total_monthly_cost) * 100 : 0
                                return (
                                    <div key={i}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 3 }}>
                                            <span>{s.service}</span>
                                            <span style={{ fontWeight: 700 }}>${s.amount.toLocaleString()}</span>
                                        </div>
                                        <div style={{ height: 5, borderRadius: 3, background: 'var(--bg-tertiary)', overflow: 'hidden' }}>
                                            <div style={{
                                                height: '100%', borderRadius: 3, width: `${pct}%`,
                                                background: 'linear-gradient(90deg, #3b82f6, #8b5cf6)',
                                            }} />
                                        </div>
                                    </div>
                                )
                            })}
                        </div>
                    </div>
                )}

                {/* Waste by service */}
                {waste_by_service?.length > 0 && (
                    <div>
                        <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 10, fontWeight: 600 }}>
                            ESTIMATED WASTE BY SERVICE
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                            {waste_by_service.map((w, i) => (
                                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12 }}>
                                    <span style={{ color: 'var(--text-secondary)' }}>{w.service}</span>
                                    <span style={{ fontWeight: 700, color: '#ef4444' }}>
                                        ~${w.estimated_waste.toLocaleString()}
                                    </span>
                                </div>
                            ))}
                            <div style={{ borderTop: '1px solid var(--border)', paddingTop: 6, marginTop: 4, display: 'flex', justifyContent: 'space-between', fontSize: 12, fontWeight: 700 }}>
                                <span>Total Est. Waste</span>
                                <span style={{ color: '#ef4444' }}>${fmtNum(estimated_monthly_waste)}</span>
                            </div>
                        </div>
                    </div>
                )}

                {/* Cost by tag */}
                {cost_by_tag?.length > 0 && (
                    <div>
                        <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 10, fontWeight: 600 }}>
                            COST BY ENVIRONMENT TAG
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                            {cost_by_tag.map((t, i) => {
                                const tagTotal = cost_by_tag.reduce((s, x) => s + x.amount, 0)
                                const pct = tagTotal > 0 ? (t.amount / tagTotal) * 100 : 0
                                const tagColors = {
                                    production: '#ef4444', staging: '#f59e0b',
                                    development: '#3b82f6', untagged: '#6b7280',
                                }
                                const color = tagColors[t.tag] || '#8b5cf6'
                                return (
                                    <div key={i}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 3 }}>
                                            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                                <span style={{ width: 8, height: 8, borderRadius: '50%', background: color, display: 'inline-block' }} />
                                                {t.tag || 'untagged'}
                                            </span>
                                            <span style={{ fontWeight: 700 }}>${t.amount.toLocaleString()}</span>
                                        </div>
                                        <div style={{ height: 4, borderRadius: 3, background: 'var(--bg-tertiary)', overflow: 'hidden' }}>
                                            <div style={{ height: '100%', borderRadius: 3, width: `${pct}%`, background: color }} />
                                        </div>
                                    </div>
                                )
                            })}
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}


// ── Summary stat card ────────────────────────────────────────────────────────
function StatCard({ icon: Icon, label, count, color, sublabel }) {
    return (
        <div className="stat-card">
            <div className="stat-icon" style={{ background: `${color}22` }}>
                <Icon size={20} color={color} />
            </div>
            <div className="stat-info">
                <div className="stat-value">{count}</div>
                <div className="stat-label">{label}</div>
                {sublabel && <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>{sublabel}</div>}
            </div>
        </div>
    )
}

// ── Tab definitions ──────────────────────────────────────────────────────────
const RESOURCE_TABS = [
    { key: 'EC2', label: 'EC2', icon: Server, color: '#3b82f6' },
    { key: 'EBS', label: 'EBS', icon: HardDrive, color: '#8b5cf6' },
    { key: 'S3', label: 'S3', icon: Globe2, color: '#f59e0b' },
    { key: 'RDS', label: 'RDS', icon: Database, color: '#10b981' },
    { key: 'EIP', label: 'Elastic IPs', icon: Network, color: '#ec4899' },
    { key: 'SNAPSHOT', label: 'Snapshots', icon: Camera, color: '#6b7280' },
    { key: 'LB', label: 'Load Balancers', icon: GitBranch, color: '#0ea5e9' },
    { key: 'NAT', label: 'NAT Gateways', icon: LoaderCircle, color: '#f59e0b' },
]

const VIEW_TABS = [
    { key: 'resources', label: 'Resources', icon: Server },
    { key: 'violations', label: 'Violations', icon: AlertTriangle },
    { key: 'costs', label: 'Costs', icon: DollarSign },
]

// ── Main Dashboard ───────────────────────────────────────────────────────────
export default function Dashboard() {
    const navigate = useNavigate()
    const [connected, setConnected] = useState(null)
    const [scanRegions, setScanRegions] = useState(['ap-south-1'])
    const [scanning, setScanning] = useState(false)
    const [resources, setResources] = useState([])
    const [violations, setViolations] = useState([])
    const [sevSummary, setSevSummary] = useState({})
    const [costData, setCostData] = useState(null)
    const [recommendations, setRecommendations] = useState([])
    const [lastScan, setLastScan] = useState(null)
    const [activeTab, setActiveTab] = useState('EC2')
    const [viewTab, setViewTab] = useState('resources')
    const [toast, setToast] = useState(null)
    const [loading, setLoading] = useState(true)

    const showToast = (msg, type = 'info') => {
        setToast({ msg, type })
        setTimeout(() => setToast(null), 4000)
    }

    const loadScanData = useCallback(async (scanId) => {
        try {
            const [resResp, vioResp, costResp, recResp] = await Promise.all([
                apiClient.get(`/scans/${scanId}/resources`, { params: { page_size: 500 } }),
                apiClient.get(`/scans/${scanId}/violations`, { params: { page_size: 500 } }),
                apiClient.get(`/scans/${scanId}/costs`),
                apiClient.get(`/scans/${scanId}/recommendations`),
            ])
            setResources(resResp.data.resources ?? [])
            setViolations(vioResp.data.violations ?? [])
            setSevSummary(vioResp.data.severity_summary ?? {})
            setCostData(costResp.data ?? null)
            setRecommendations(recResp.data?.recommendations ?? [])
        } catch {
            showToast('Failed to load scan data', 'error')
        }
    }, [])

    const loadLatestScan = useCallback(async () => {
        try {
            const { data } = await apiClient.get('/scans')
            const completed = (data.scans ?? []).filter(s => s.status === 'completed')
            if (!completed.length) { setLoading(false); return }
            const latest = completed[0]
            setLastScan(latest)
            await loadScanData(latest.id)
        } catch {
            showToast('Failed to load scan results', 'error')
        } finally {
            setLoading(false)
        }
    }, [loadScanData])

    const pollScan = useCallback(async (scanId) => {
        for (let i = 0; i < 60; i++) {
            await new Promise(r => setTimeout(r, 3000))
            try {
                const { data } = await apiClient.get(`/scans/${scanId}`)
                if (data.status === 'completed' || data.status === 'failed') {
                    if (data.status === 'completed') {
                        setLastScan(data)
                        await loadScanData(scanId)
                        showToast(`Scan complete — ${data.resource_count} resources found`, 'success')
                    } else {
                        showToast('Scan failed', 'error')
                    }
                    setScanning(false)
                    return
                }
            } catch { break }
        }
        setScanning(false)
    }, [loadScanData])

    const handleScan = async () => {
        setScanning(true)
        try {
            const { data } = await apiClient.post('/scans', { regions: scanRegions })
            showToast(`Scanning ${scanRegions.join(', ')}…`, 'info')
            pollScan(data.scan_id)
        } catch {
            showToast('Failed to start scan', 'error')
            setScanning(false)
        }
    }

    useEffect(() => {
        getSettings().then(s => {
            setConnected(s.connected)
            if (s.scan_regions?.length) setScanRegions(s.scan_regions)
            if (s.connected) loadLatestScan()
            else setLoading(false)
        }).catch(() => { setConnected(false); setLoading(false) })
    }, [loadLatestScan])

    const byType = type => resources.filter(r => r.resource_type === type)

    const criticalCount = sevSummary['CRITICAL'] || 0
    const highCount = sevSummary['HIGH'] || 0

    return (
        <div>
            {toast && <div className={`toast ${toast.type}`}>{toast.msg}</div>}

            {connected === false && (
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '80px 20px', textAlign: 'center' }}>
                    <WifiOff size={48} color="#ef4444" style={{ marginBottom: 16 }} />
                    <div style={{ fontSize: 22, fontWeight: 700, marginBottom: 8 }}>AWS Account Not Connected</div>
                    <div style={{ color: 'var(--text-secondary)', fontSize: 14, maxWidth: 380, marginBottom: 24 }}>
                        Connect your AWS account in Settings to start viewing your cloud resources.
                    </div>
                    <button className="btn btn-primary" onClick={() => navigate('/settings')}>Go to Settings</button>
                </div>
            )}

            {connected && (
                <>
                    {/* Page header */}
                    <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12, marginBottom: 24 }}>
                        <div>
                            <div className="page-title">Cloud Resource Inventory</div>
                            <div className="page-subtitle">
                                {lastScan
                                    ? `Last scan: ${fmtDate(lastScan.started_at)} · Regions: ${lastScan.regions?.join(', ')}`
                                    : 'No scans run yet — click Scan Now to fetch your resources'}
                            </div>
                        </div>
                        <button className="btn btn-primary" onClick={handleScan} disabled={scanning}
                            style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <RefreshCw size={14} className={scanning ? 'spin' : ''} />
                            {scanning ? 'Scanning…' : 'Scan Now'}
                        </button>
                    </div>

                    {loading ? (
                        <div className="loading-wrapper"><div className="spinner" /><span>Loading resources…</span></div>
                    ) : (
                        <>
                            {/* Summary stat cards */}
                            <div className="stats-grid" style={{ marginBottom: 24 }}>
                                <StatCard icon={Server} label="EC2 Instances" count={byType('EC2').length} color="#3b82f6" />
                                <StatCard icon={HardDrive} label="EBS Volumes" count={byType('EBS').length} color="#8b5cf6" />
                                <StatCard icon={Globe2} label="S3 Buckets" count={byType('S3').length} color="#f59e0b" />
                                <StatCard icon={Database} label="RDS Databases" count={byType('RDS').length} color="#10b981" />
                                <StatCard icon={Network} label="Elastic IPs" count={byType('EIP').length} color="#ec4899" />
                                <StatCard icon={Camera} label="Snapshots" count={byType('SNAPSHOT').length} color="#6b7280" />
                                <StatCard icon={GitBranch} label="Load Balancers" count={byType('LB').length} color="#0ea5e9" />
                                <StatCard icon={LoaderCircle} label="NAT Gateways" count={byType('NAT').length} color="#f59e0b" />
                                <StatCard icon={AlertTriangle} label="Violations" count={violations.length}
                                    color="#ef4444"
                                    sublabel={criticalCount || highCount ? `${criticalCount} critical · ${highCount} high` : undefined} />
                                <StatCard icon={Zap} label="Estimated Waste"
                                    count={costData?.summary?.estimated_monthly_waste != null
                                        ? `$${costData.summary.estimated_monthly_waste.toLocaleString()}`
                                        : '—'}
                                    color="#f97316" />
                            </div>

                            {/* Cost summary */}
                            {costData?.summary?.total_monthly_cost > 0 && <CostSummaryCard costData={costData} />}

                            {/* View tabs (Resources / Violations / Costs) */}
                            <div style={{ display: 'flex', gap: 4, borderBottom: '1px solid var(--border)', marginBottom: 20 }}>
                                {VIEW_TABS.map(({ key, label, icon: Icon }) => {
                                    const isActive = viewTab === key
                                    const dot = key === 'violations' && (criticalCount + highCount) > 0
                                    return (
                                        <button key={key} onClick={() => setViewTab(key)} style={{
                                            display: 'flex', alignItems: 'center', gap: 6,
                                            padding: '8px 18px', border: 'none', cursor: 'pointer',
                                            background: 'transparent', fontSize: 13, fontWeight: isActive ? 700 : 400,
                                            color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                                            borderBottom: isActive ? '2px solid var(--accent)' : '2px solid transparent',
                                            marginBottom: -1, position: 'relative',
                                        }}>
                                            <Icon size={14} />
                                            {label}
                                            {dot && <span style={{
                                                width: 7, height: 7, borderRadius: '50%',
                                                background: '#ef4444', marginLeft: 2,
                                            }} />}
                                        </button>
                                    )
                                })}
                            </div>

                            {/* Resources view */}
                            {viewTab === 'resources' && (
                                resources.length === 0 && !scanning ? (
                                    <div className="card">
                                        <Empty msg={lastScan ? 'No resources found in the last scan.' : 'Run a scan to see your AWS resources.'} />
                                    </div>
                                ) : (
                                    <div className="card">
                                        {/* Resource type tabs */}
                                        <div style={{ display: 'flex', gap: 4, borderBottom: '1px solid var(--border)', marginBottom: 20, flexWrap: 'wrap' }}>
                                            {RESOURCE_TABS.map(({ key, label, icon: Icon, color }) => {
                                                const count = byType(key).length
                                                const isActive = activeTab === key
                                                return (
                                                    <button key={key} onClick={() => setActiveTab(key)} style={{
                                                        display: 'flex', alignItems: 'center', gap: 6,
                                                        padding: '8px 14px', border: 'none', cursor: 'pointer',
                                                        background: 'transparent', fontSize: 13, fontWeight: isActive ? 700 : 400,
                                                        color: isActive ? color : 'var(--text-secondary)',
                                                        borderBottom: isActive ? `2px solid ${color}` : '2px solid transparent',
                                                        marginBottom: -1,
                                                    }}>
                                                        <Icon size={13} />
                                                        {label}
                                                        <span style={{
                                                            background: isActive ? `${color}22` : 'var(--bg-tertiary)',
                                                            color: isActive ? color : 'var(--text-secondary)',
                                                            borderRadius: 10, padding: '1px 7px', fontSize: 11,
                                                        }}>{count}</span>
                                                    </button>
                                                )
                                            })}
                                        </div>
                                        {activeTab === 'EC2' && <EC2Table items={byType('EC2')} />}
                                        {activeTab === 'EBS' && <EBSTable items={byType('EBS')} />}
                                        {activeTab === 'S3' && <S3Table items={byType('S3')} />}
                                        {activeTab === 'RDS' && <RDSTable items={byType('RDS')} />}
                                        {activeTab === 'EIP' && <EIPTable items={byType('EIP')} />}
                                        {activeTab === 'SNAPSHOT' && <SnapshotTable items={byType('SNAPSHOT')} />}
                                        {activeTab === 'LB' && <LBTable items={byType('LB')} />}
                                        {activeTab === 'NAT' && <NATTable items={byType('NAT')} />}
                                    </div>
                                )
                            )}

                            {/* Violations view */}
                            {viewTab === 'violations' && (
                                <div className="card">
                                    <ViolationsPanel violations={violations} sevSummary={sevSummary} />
                                </div>
                            )}

                            {/* Recommendations preview — shown under violations when recs available */}
                            {viewTab === 'violations' && recommendations?.length > 0 && (
                                <div className="card" style={{ marginTop: 16 }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                            <Zap size={16} color="#3b82f6" />
                                            <span style={{ fontWeight: 700, fontSize: 14 }}>Top Savings Recommendations</span>
                                        </div>
                                        <a href="/recommendations" style={{ fontSize: 12, color: '#3b82f6', textDecoration: 'none', fontWeight: 600 }}>
                                            View all {recommendations.length} →
                                        </a>
                                    </div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
                                        <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Total estimated monthly savings:</span>
                                        <span style={{ fontWeight: 800, fontSize: 16, color: '#10b981' }}>
                                            ${recommendations.reduce((s, r) => s + (r.estimated_monthly_savings || 0), 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                        </span>
                                    </div>
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                                        {recommendations.filter(r => r.estimated_monthly_savings > 0).slice(0, 3).map((r, i) => {
                                            const catColors = { Compute: '#3b82f6', Storage: '#8b5cf6', Database: '#10b981', Network: '#0ea5e9', Governance: '#6b7280' }
                                            const color = catColors[r.category] || '#6b7280'
                                            return (
                                                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 12px', borderRadius: 6, background: `${color}0a`, border: `1px solid ${color}22` }}>
                                                    <div style={{ flex: 1 }}>
                                                        <div style={{ fontSize: 12, fontWeight: 600 }}>{r.title}</div>
                                                        <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>
                                                            <span style={{ color, fontWeight: 600 }}>{r.category}</span>
                                                            <span style={{ margin: '0 6px' }}>·</span>
                                                            <code style={{ fontSize: 10 }}>{r.rule_id}</code>
                                                        </div>
                                                    </div>
                                                    <div style={{ fontWeight: 800, fontSize: 14, color: '#10b981', marginLeft: 16 }}>
                                                        ${r.estimated_monthly_savings.toFixed(2)}/mo
                                                    </div>
                                                </div>
                                            )
                                        })}
                                    </div>
                                </div>
                            )}

                            {/* Costs view */}
                            {viewTab === 'costs' && (
                                <div className="card">
                                    {costData?.records?.length > 0 ? (
                                        <>
                                            <div style={{ fontWeight: 700, marginBottom: 16 }}>Cost Breakdown by Service & Region</div>
                                            <div className="table-wrapper">
                                                <table>
                                                    <thead><tr>
                                                        <th>Service</th><th>Region</th><th>Amount (USD)</th><th>Period</th>
                                                    </tr></thead>
                                                    <tbody>
                                                        {[...costData.records]
                                                            .sort((a, b) => b.amount - a.amount)
                                                            .map((r, i) => (
                                                                <tr key={i}>
                                                                    <td>{r.service}</td>
                                                                    <td>{r.region}</td>
                                                                    <td style={{ fontWeight: 600 }}>${r.amount.toLocaleString()}</td>
                                                                    <td style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{r.period_start} → {r.period_end}</td>
                                                                </tr>
                                                            ))}
                                                    </tbody>
                                                </table>
                                            </div>
                                        </>
                                    ) : (
                                        <Empty msg="No cost data available. Run a scan to fetch cost data." />
                                    )}
                                </div>
                            )}
                        </>
                    )}
                </>
            )}
        </div>
    )
}
