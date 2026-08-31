import React from 'react'
import TestButton from '../debug/TestButton'

export default function Home() {
	return (
		<div>
			<div className="max-w-4xl mx-auto">
				<h1 className="text-2xl font-bold mb-4">Dashboard</h1>
				<p className="mb-4">Welcome to EmergencyIQ — this is a minimal dashboard placeholder.</p>

				<section className="mb-6">
					<TestButton />
				</section>

				<section>
					<div className="p-4 bg-white rounded shadow-sm">
						<h3 className="font-semibold">Recent Calls</h3>
						<p className="text-sm text-muted-foreground">No calls yet (placeholder)</p>
					</div>
				</section>
			</div>
		</div>
	)
}
