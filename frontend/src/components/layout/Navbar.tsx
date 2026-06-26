import { NavLink } from 'react-router-dom';
import styles from './Navbar.module.css';

const navItems = [
  { to: '/', label: 'Dashboard', icon: '📊' },
  { to: '/new', label: 'New Application', icon: '➕' },
  { to: '/profile', label: 'Profile', icon: '👤' },
  { to: '/history', label: 'History', icon: '📋' },
  { to: '/config', label: 'Settings', icon: '⚙️' },
];

export default function Navbar() {
  return (
    <nav className={styles.nav}>
      <div className={styles.brand}>
        <span className={styles.logo}>RP</span>
        <span className={styles.title}>Resume Pipeline</span>
      </div>
      <ul className={styles.links}>
        {navItems.map((item) => (
          <li key={item.to}>
            <NavLink
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `${styles.link} ${isActive ? styles.active : ''}`
              }
            >
              <span className={styles.icon}>{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
