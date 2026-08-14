// @ts-nocheck
import React from 'react'

export default function Card({ title, children }) {
  return (
    <section className="bg-white rounded shadow-sm p-4">
      {title && <h3 className="font-semibold mb-2">{title}</h3>}
      <div>{children}</div>
    </section>
  )
}
