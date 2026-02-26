import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Settings, Zap } from 'lucide-react'

const NAV = [
    { to: '/', label: 'Resources', icon: LayoutDashboard },
    { to: '/recommendations', label: 'Recommendations', icon: Zap },
    { to: '/settings', label: 'Settings', icon: Settings },
]

export default function Sidebar() {
    return (
        <aside className="sidebar">
            <div className="sidebar-logo">
                <div className="sidebar-logo-icon">☁</div>
                <div>
                    <div className="sidebar-logo-text">CloudAudit</div>
                    <div className="sidebar-logo-sub">Resource Inventory</div>
                </div>
            </div>

            <nav className="sidebar-nav">
                {NAV.map(({ to, label, icon: Icon }) => (
                    <NavLink
                        key={to}
                        to={to}
                        end
                        className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
                    >
                        <Icon size={17} />
                        {label}
                    </NavLink>
                ))}
            </nav>
        </aside>
    )
}
