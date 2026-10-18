import React from 'react';

export default function StatCard({ title, value, subtitle, icon: Icon, trend, colorScheme = 'indigo' }) {
  return (
    <div className={`stat-card glass-panel theme-${colorScheme}`}>
      <div className="stat-card-header">
        <span className="stat-title">{title}</span>
        {Icon && (
          <div className="stat-icon-wrapper">
            <Icon size={20} />
          </div>
        )}
      </div>
      <div className="stat-card-body">
        <div className="stat-value">{value}</div>
        {subtitle && <div className="stat-subtitle">{subtitle}</div>}
      </div>
      {trend && (
        <div className="stat-trend">
          <span className="trend-badge">{trend}</span>
          <span className="trend-text">from last week</span>
        </div>
      )}
    </div>
  );
}
