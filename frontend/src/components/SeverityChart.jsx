import React from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

export default function SeverityChart({ data = [] }) {
  return (
    <div className="card p-4 rounded-md">
      <h3 className="font-semibold mb-2">Severity Distribution</h3>
      <div style={{ width: '100%', height: 180 }}>
        <ResponsiveContainer>
          <BarChart data={data}>
            <XAxis dataKey="name" stroke="#A1A1AA" />
            <YAxis stroke="#A1A1AA" />
            <Tooltip />
            <Bar dataKey="value" fill="#FFFFFF" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
