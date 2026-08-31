// @ts-nocheck
import React from 'react'

export default function TestButton() {
	return (
		<div className="p-4">
			<button
				type="button"
				className="px-4 py-2 bg-black text-white rounded-md"
				onClick={() => {
					// quick visual + console signal for click
					// eslint-disable-next-line no-console
					console.log('TestButton clicked')
					alert('TestButton clicked')
				}}
			>
				Test Button
			</button>
		</div>
	)
}
